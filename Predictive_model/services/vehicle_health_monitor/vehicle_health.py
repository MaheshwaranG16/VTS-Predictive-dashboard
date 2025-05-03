import pandas as pd
import numpy as np
from sqlalchemy import text
from app.config import engine
from datetime import datetime
import joblib
import os

from services.vehicle_health_monitor.utils import fetch_tracking_data, preprocess


MODEL_PATH = "models/vehicle_health_iforest.pkl"


def detect_anomalies(agg_df, model_path=MODEL_PATH):
    features = [
        'low_main_voltage', 'low_internal_battery', 'power_fluctuations',
        'ignition_cycles', 'gps_unreliable', 'time_drift',
        'tamper_flag', 'emergency_flag'
    ]

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}. Please train it first.")

    model = joblib.load(model_path)
    X = agg_df[features]
    agg_df['anomaly_score'] = model.predict(X)
    agg_df['health_status'] = agg_df['anomaly_score'].map({1: 'Healthy', -1: 'At Risk'})
    return agg_df

def get_vehicle_health_json(vehicle_reg_no=None):
    df = fetch_tracking_data(vehicle_reg_no=vehicle_reg_no)
    if df.empty:
        return []

    agg_df = preprocess(df)
    if agg_df.empty:
        return []

    result_df = detect_anomalies(agg_df)

    result_df['date'] = result_df['date'].astype(str)
    result_json = result_df[['vehicle_reg_no', 'date', 'health_status','anomaly_score']].to_dict(orient='records')
    return result_json