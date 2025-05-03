# utils.py
import pandas as pd
from sqlalchemy import text
from app.config import engine

'''
def fetch_tracking_data():
    query = """
    SELECT vehicle_reg_no, main_input_voltage, internal_battery_voltage, 
           main_power_status, ignition_status, gps_fix, tamper_alert, emergency_status, 
           created_on, vehicle_timestamp
    FROM tracking_data
    WHERE vehicle_timestamp >= NOW() - INTERVAL '7 days'
    """
    return pd.read_sql_query(query, engine, parse_dates=['created_on', 'vehicle_timestamp'])
'''

def fetch_tracking_data(vehicle_reg_no=None):
    base_query = """
    SELECT vehicle_reg_no, main_input_voltage, internal_battery_voltage, 
           main_power_status, ignition_status, gps_fix, tamper_alert, emergency_status, 
           created_on, vehicle_timestamp
    FROM tracking_data
    WHERE vehicle_timestamp >= (SELECT MAX(vehicle_timestamp) FROM tracking_data) - INTERVAL '7 days'
    """
    if vehicle_reg_no:
        base_query += " AND vehicle_reg_no = :vehicle_reg_no"

    params = {"vehicle_reg_no": vehicle_reg_no} if vehicle_reg_no else {}

    return pd.read_sql_query(text(base_query), engine, params=params, parse_dates=['created_on', 'vehicle_timestamp'])


def preprocess(df):
    df['low_main_voltage'] = (df['main_input_voltage'] < 11.5).astype(int)
    df['low_internal_battery'] = (df['internal_battery_voltage'] < 3.6).astype(int)
    df['power_fluctuations'] = df['main_power_status'].ne(df['main_power_status'].shift()).astype(int)
    df['ignition_cycles'] = df['ignition_status'].ne(df['ignition_status'].shift()).astype(int)
    df['gps_unreliable'] = (df['gps_fix'] == '0').astype(int)
    df['time_drift'] = (df['created_on'] - df['vehicle_timestamp']).dt.total_seconds().fillna(0)
    df['tamper_flag'] = (df['tamper_alert'].notnull()).astype(int)
    df['emergency_flag'] = (df['emergency_status'].notnull()).astype(int)
    df.fillna(0, inplace=True)
    df['date'] = df['vehicle_timestamp'].dt.date

    agg_df = df.groupby(['vehicle_reg_no', 'date']).agg({
        'low_main_voltage': 'sum',
        'low_internal_battery': 'sum',
        'power_fluctuations': 'sum',
        'ignition_cycles': 'sum',
        'gps_unreliable': 'sum',
        'time_drift': 'mean',
        'tamper_flag': 'sum',
        'emergency_flag': 'sum'
    }).reset_index()

    return agg_df
