import pandas as pd
from prophet import Prophet
from sqlalchemy import text
from app.config import SessionLocal
import numpy as np
import os
import pickle
import json
from datetime import datetime

MODEL_DIR = "prophet_models"
os.makedirs(MODEL_DIR, exist_ok=True)

def is_model_stale(meta_path):
    if not os.path.exists(meta_path):
        return True
    with open(meta_path, "r") as f:
        meta = json.load(f)
    last_trained = datetime.strptime(meta["last_trained"], "%Y-%m-%d")
    now = datetime.now()
    return (last_trained.year < now.year) or (last_trained.month < now.month)

def update_model_metadata(meta_path):
    with open(meta_path, "w") as f:
        json.dump({"last_trained": datetime.now().strftime("%Y-%m-%d")}, f)


def fetch_replacement_history() -> pd.DataFrame:
    session = SessionLocal()
    try:
        query = text("""
            SELECT 
                s.replaced_on,
                s.vehicle_id,
                s.spares_inventory_depot_id AS spare_id
            FROM spare_replacement s
            WHERE s.replaced_on IS NOT NULL
            ORDER BY s.vehicle_id, s.spares_inventory_depot_id, s.replaced_on
        """)
        df = pd.read_sql(query, session.bind)
    finally:
        session.close()
    return df


def fetch_tracking_data() -> pd.DataFrame:
    session = SessionLocal()
    try:
        query = text("""
            SELECT
                vehicle_reg_no,
                vehicle_timestamp,
                speed
            FROM tracking_data
            WHERE speed > 0
            ORDER BY vehicle_reg_no, vehicle_timestamp
        """)
        df = pd.read_sql(query, session.bind)
    finally:
        session.close()

    df["vehicle_timestamp"] = pd.to_datetime(df["vehicle_timestamp"])
    df["time_diff"] = df.groupby("vehicle_reg_no")["vehicle_timestamp"].diff().dt.total_seconds() / 3600
    df["usage_hours"] = df["speed"] * df["time_diff"]
    return df


def compute_usage_before_replacement(replacement_df: pd.DataFrame, tracking_df: pd.DataFrame) -> pd.DataFrame:
    replacement_df["prev_replaced_on"] = replacement_df.groupby(
        ["vehicle_reg_no", "spare_id"]
    )["replaced_on"].shift(1)

    usage_list = []

    for idx, row in replacement_df.iterrows():
        vehicle_reg_no = row["vehicle_reg_no"]
        start = row["prev_replaced_on"]
        end = row["replaced_on"]

        if pd.isna(vehicle_reg_no) or pd.isna(start) or pd.isna(end):
            usage_list.append(None)
            continue

        usage_data = tracking_df[
            (tracking_df["vehicle_reg_no"] == vehicle_reg_no) &
            (tracking_df["vehicle_timestamp"] > start) &
            (tracking_df["vehicle_timestamp"] <= end)
        ]

        usage_hours_sum = usage_data["usage_hours"].sum()
        usage_list.append(usage_hours_sum if not np.isnan(usage_hours_sum) else None)

    replacement_df["usage_before_replacement"] = usage_list
    return replacement_df



def fetch_spare_inventory_data():
    session = SessionLocal()
    try:
        query = text("""
            SELECT
                spare_id,
                spare_name,
                unit_price,
                quantity_available
            FROM spares_inventory_depot
        """)
        return pd.read_sql(query, session.bind)
    finally:
        session.close()


def fetch_vehicle_status_data():
    session = SessionLocal()
    try:
        query = text("""
            SELECT
                vehicle_reg_no,
                AVG(emergency_status::int) AS emergency_condition,
                AVG(CASE WHEN tamper_alert = 'O' THEN 1 ELSE 0 END) AS tamper_condition
            FROM tracking_data
            GROUP BY vehicle_reg_no
        """)
        return pd.read_sql(query, session.bind)
    finally:
        session.close()


def fetch_vehicle_reg_no():
    session = SessionLocal()
    try:
        query = text("""
            SELECT
                vehicle_id,
                vehicle_number AS vehicle_reg_no
            FROM vehicle
        """)
        return pd.read_sql(query, session.bind)
    finally:
        session.close()


def generate_forecast_for_pair(df, spare_inventory, vehicle_status, periods=60):
    df = df.merge(spare_inventory, on="spare_id", how="left")
    df = df.merge(vehicle_status, on="vehicle_reg_no", how="left")

    df = df.sort_values("replaced_on")
    ts = df[["replaced_on", "usage_before_replacement"]].rename(columns={"replaced_on": "ds", "usage_before_replacement": "y"})

    ts["cost"] = df["unit_price"]
    ts["quantity_available"] = df["quantity_available"]
    ts["emergency_condition"] = df["emergency_condition"]
    ts["tamper_condition"] = df["tamper_condition"]

    if len(ts.dropna()) < 3:
        return None

    vehicle_id = df["vehicle_id"].iloc[0]
    spare_id = df["spare_id"].iloc[0]
    model_path = os.path.join(MODEL_DIR, f"prophet_model_{vehicle_id}_{spare_id}.pkl")
    meta_path = os.path.join(MODEL_DIR, f"prophet_model_{vehicle_id}_{spare_id}_meta.json")

    if os.path.exists(model_path) and not is_model_stale(meta_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    else:
        model = Prophet(daily_seasonality=False, yearly_seasonality=False, weekly_seasonality=False)
        model.add_regressor("cost")
        model.add_regressor("quantity_available")
        model.add_regressor("emergency_condition")
        model.add_regressor("tamper_condition")

        model.fit(ts)

        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        update_model_metadata(meta_path)

    future = model.make_future_dataframe(periods=periods)
    future["cost"] = df["unit_price"].iloc[-1]
    future["quantity_available"] = df["quantity_available"].iloc[-1]
    future["emergency_condition"] = df["emergency_condition"].iloc[-1]
    future["tamper_condition"] = df["tamper_condition"].iloc[-1]

    forecast = model.predict(future)
    forecasted = forecast[forecast['ds'] > ts['ds'].max()]
    next_date = forecasted.loc[forecasted['yhat'] > 0.5, 'ds']

    return next_date.min() if not next_date.empty else None


def forecast_all_next_replacements(periods: int = 60):
    history_df = fetch_replacement_history()
    vehicle_reg_no_df = fetch_vehicle_reg_no()
    tracking_df = fetch_tracking_data()

    # Merge vehicle_reg_no into history
    history_df = history_df.merge(vehicle_reg_no_df, on="vehicle_id", how="left")

    spare_inventory_df = fetch_spare_inventory_data()
    vehicle_status_df = fetch_vehicle_status_data()

    history_with_usage = compute_usage_before_replacement(history_df, tracking_df)
    results = []

    grouped = history_with_usage.groupby(["vehicle_id", "spare_id"])
    for (vehicle_id, spare_id), group_df in grouped:
        try:
            next_date = generate_forecast_for_pair(group_df, spare_inventory_df,
                                                   vehicle_status_df, periods)

            spare_row = spare_inventory_df[spare_inventory_df['spare_id'] == spare_id].iloc[0]
            vehicle_reg_no = group_df['vehicle_reg_no'].iloc[0]
            status_row = vehicle_status_df[vehicle_status_df['vehicle_reg_no'] == vehicle_reg_no]

            usage_before_last = group_df["usage_before_replacement"].dropna().iloc[-1] \
                                if not group_df["usage_before_replacement"].dropna().empty else None

            results.append({
                "vehicle_reg_no": vehicle_reg_no,
                "spare_name": spare_row["spare_name"],
                "next_expected_replacement": next_date,
                "unit_price": round(spare_row["unit_price"], 2),
                "quantity_available": round(spare_row["quantity_available"], 2),
                "usage_before_last_replacement": round(usage_before_last, 2) if usage_before_last is not None else None,
                "emergency_condition": round(status_row["emergency_condition"].values[0], 2) if not status_row.empty else None,
                "tamper_condition": round(status_row["tamper_condition"].values[0], 2) if not status_row.empty else None
            })
        except Exception as e:
            print(f"Skipping vehicle {vehicle_id}, spare {spare_id}: {e}")
            continue

    results_df = pd.DataFrame(results)
    results_df["usage_before_last_replacement"] = results_df["usage_before_last_replacement"].fillna(0)
    results_df["emergency_condition"] = results_df["emergency_condition"].fillna(0)
    results_df["tamper_condition"] = results_df["tamper_condition"].fillna(0)

    results_df = results_df.where(pd.notnull(results_df), None)

    return results_df

if __name__ == "__main__":
    forecast_df = forecast_all_next_replacements()
    print("Forecasted Next Expected Replacements:")
    print(forecast_df)
