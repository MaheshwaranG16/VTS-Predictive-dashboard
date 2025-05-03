from sqlalchemy import text
from sqlalchemy.orm import Session
import pandas as pd


def get_driver_behavior_metrics(db: Session) -> pd.DataFrame:
    query = text("""
        WITH tracking_metrics AS (
            SELECT
                td.vehicle_reg_no,
                d.driver_name,
                td.speed,
                td.heading,
                td.ignition_status,
                td.vehicle_timestamp,
                v.vehicle_type_id,
                v.company_id,
                mvt.speed_limit,
                (td.speed - LAG(td.speed) OVER (PARTITION BY td.vehicle_reg_no ORDER BY td.vehicle_timestamp)) /
                NULLIF(EXTRACT(EPOCH FROM (
                    td.vehicle_timestamp - LAG(td.vehicle_timestamp) OVER (PARTITION BY td.vehicle_reg_no ORDER BY td.vehicle_timestamp)
                )), 0) AS acceleration,
                ABS(td.heading - LAG(td.heading) OVER (PARTITION BY td.vehicle_reg_no ORDER BY td.vehicle_timestamp)) AS heading_diff
            FROM tracking_data td
            JOIN vehicle v ON td.vehicle_reg_no = v.vehicle_number
            JOIN map_vehicle_type mvt ON v.vehicle_type_id = mvt.vehicle_type_id AND v.company_id = mvt.company_id
            JOIN trip_details tp ON tp.vehicle_id = v.vehicle_id
            JOIN driver_details d ON d.driver_id = tp.driver_id
        )
        SELECT
            driver_name,
            vehicle_reg_no,
            SUM(CASE WHEN acceleration > 3 THEN 1 ELSE 0 END) AS harsh_accel_count,
            SUM(CASE WHEN acceleration < -3 THEN 1 ELSE 0 END) AS harsh_brake_count,
            SUM(CASE WHEN heading_diff > 45 AND speed > 30 THEN 1 ELSE 0 END) AS rash_turn_count,
            SUM(CASE WHEN speed < 2 AND ignition_status = 'ON' THEN 1 ELSE 0 END) AS idle_time_points,
            SUM(CASE WHEN speed > speed_limit THEN 1 ELSE 0 END) AS overspeed_count
        FROM tracking_metrics
        GROUP BY driver_name, vehicle_reg_no;
    """)
    return pd.read_sql(query, db.bind)


def get_route_deviation_count(db: Session, vehicle_id: int, trip_id: int) -> int:
    query = text("""
        SELECT COUNT(DISTINCT a.alert_id) AS deviation_count
        FROM alerts a
        JOIN trip_details td ON a.trip_id = td.trip_id
        WHERE a.alert_type = 'deviate'
          AND a.vehicle_id = :vehicle_id
          AND td.trip_id = :trip_id
    """)
    result = db.execute(query, {"vehicle_id": vehicle_id, "trip_id": trip_id}).mappings().fetchone()
    return result['deviation_count'] if result else 0


def get_time_deviation(db: Session, trip_id: int) -> float:
    query = text("""
        SELECT start_date, end_date,
               CAST(REPLACE(total_distance, 'km', '') AS FLOAT) AS total_distance
        FROM trip_details
        WHERE trip_id = :trip_id
    """)
    result = db.execute(query, {"trip_id": trip_id}).mappings().fetchone()
    if not result or not result['start_date'] or not result['end_date']:
        return 0

    expected_duration = result['total_distance'] / 60  # Assuming avg speed = 60 km/h
    actual_duration = (result['end_date'] - result['start_date']).total_seconds() / 3600
    deviation = actual_duration - expected_duration
    return deviation if deviation > 1 else 0

def get_driver_risk_profile_by_id(db: Session, driver_id: int):
    behavior_df = get_driver_behavior_metrics(db)

    # Fetch driver and vehicle info
    driver_query = text("""
        SELECT DISTINCT d.driver_id, d.driver_name, v.vehicle_number
        FROM driver_details d
        JOIN trip_details t ON d.driver_id = t.driver_id
        JOIN vehicle v ON t.vehicle_id = v.vehicle_id
        WHERE d.driver_id = :driver_id
        LIMIT 1
    """)
    driver = db.execute(driver_query, {"driver_id": driver_id}).mappings().fetchone()
    if not driver:
        return {"error": "Driver not found."}

    vehicle_number = driver["vehicle_number"]
    driver_name = driver["driver_name"]

    behavior_row = behavior_df[behavior_df['vehicle_reg_no'] == vehicle_number]
    if behavior_row.empty:
        return {"error": "No behavior data found for the vehicle."}

    row = behavior_row.iloc[0]

    # Route deviation count
    deviation_query = text("""
        SELECT COUNT(DISTINCT a.alert_id) FROM alerts a
        JOIN trip_details td ON a.trip_id = td.trip_id
        WHERE a.alert_type = 'deviate' AND td.driver_id = :driver_id
    """)
    route_deviation_count = db.execute(deviation_query, {"driver_id": driver_id}).scalar()

    # Time deviation across trips
    trips_query = text("SELECT trip_id FROM trip_details WHERE driver_id = :driver_id")
    trip_ids = [r[0] for r in db.execute(trips_query, {"driver_id": driver_id}).fetchall()]
    time_deviation = sum(get_time_deviation(db, tid) for tid in trip_ids) / len(trip_ids) if trip_ids else 0

    # Risk scoring logic
    risk_score = 0
    risk_factors = {}

    # Harsh Acceleration
    if row['harsh_accel_count'] > 10:
        risk_score += 1
        risk_factors["harsh_acceleration"] = {
            "count": int(row['harsh_accel_count']),
            "score_contribution": 1
        }

    # Harsh Braking
    if row['harsh_brake_count'] > 10:
        risk_score += 1
        risk_factors["harsh_braking"] = {
            "count": int(row['harsh_brake_count']),
            "score_contribution": 1
        }

    # Rash Turning
    if row['rash_turn_count'] > 5:
        risk_score += 2
        risk_factors["rash_turning"] = {
            "count": int(row['rash_turn_count']),
            "score_contribution": 2
        }

    # Overspeeding: Adjusting for scale and ratio
    overspeed_ratio = row['overspeed_count'] / (row['overspeed_count'] + 1 + row.get('idle_time_points', 1))
    if overspeed_ratio > 0.2 and row['overspeed_count'] > 500:
        risk_score += 3
        risk_factors["overspeeding"] = {
            "count": int(row['overspeed_count']),
            "score_contribution": 3
        }

    # Idling
    if row['idle_time_points'] > 20:
        risk_score += 1
        risk_factors["idling"] = {
            "count": int(row['idle_time_points']),
            "score_contribution": 1
        }

    # Route Deviation
    if route_deviation_count > 0:
        risk_score += 2
        risk_factors["route_deviation"] = {
            "count": route_deviation_count,
            "score_contribution": 2
        }

    # Time Deviation
    if time_deviation > 1:
        risk_score += 2
        risk_factors["time_deviation"] = {
            "count": round(time_deviation, 2),
            "score_contribution": 2
        }

    # Risk level
    if risk_score <= 6:
        risk_level = "Safe"
    elif risk_score <= 12:
        risk_level = "Caution"
    else:
        risk_level = "Risky"

    return {
        "driver_id": driver_id,
        "driver_name": driver_name,
        "predicted_risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors
    }
