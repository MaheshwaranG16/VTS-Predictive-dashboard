import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
from sqlalchemy import text
from app.config import engine
from services.vehicle_health_monitor.utils import fetch_tracking_data, preprocess


def train_and_save_model(model_path='models/vehicle_health_iforest.pkl'):
    df = fetch_tracking_data()
    agg_df = preprocess(df)

    features = [
        'low_main_voltage', 'low_internal_battery', 'power_fluctuations',
        'ignition_cycles', 'gps_unreliable', 'time_drift',
        'tamper_flag', 'emergency_flag'
    ]
    
    model = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
    model.fit(agg_df[features])
    
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_and_save_model()