import os
import pickle
from flask import Blueprint, jsonify, request
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, Session
from app.config import SessionLocal
from services.predictive_maintenance.failure_analysis import cluster_failure_reasons, get_association_rules, load_failure_data
from services.driver_behavior import get_driver_risk_profile_by_id
from services.fleet_utilization import get_tracking_heatmap_data
from services.predictive_maintenance.forecast_next_replacement import forecast_all_next_replacements
from services.vehicle_health_monitor.vehicle_health import get_vehicle_health_json


routes = Blueprint("routes", __name__)
db_session = scoped_session(SessionLocal)

@routes.route('/driver_behavior', methods=['GET'])
def get_driver_risk():
    try:
        db = db_session()

        # Read driver_id from query parameter
        driver_id = request.args.get("driver_id", default=None, type=int)

        if not driver_id:
            return jsonify({"error": "Please provide driver_id as a query parameter."}), 400

        # Call risk profile function
        risk_data = get_driver_risk_profile_by_id(db, driver_id=driver_id)

        if not risk_data or "error" in risk_data:
            return jsonify(risk_data), 404

        return jsonify(risk_data)

    except SQLAlchemyError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@routes.route('/predictive_maintenance', methods=['GET'])
def get_next_replacement():
    try:
        vehicle_reg_no = request.args.get('vehicle_reg_no')
        spare_name = request.args.get('spare_name')

        forecast_df = forecast_all_next_replacements()

        if vehicle_reg_no:
            forecast_df = forecast_df[forecast_df['vehicle_reg_no'] == vehicle_reg_no]
        if spare_name:
            forecast_df = forecast_df[forecast_df['spare_name'].str.lower() == spare_name.lower()]

        if forecast_df.empty:
            return jsonify({"message": "No data found for the given parameters."}), 404

        # Convert Timestamp to ISO string and replace NaN/NaT with None
        forecast_df['next_expected_replacement'] = forecast_df['next_expected_replacement'].apply(
            lambda x: x.isoformat() if pd.notnull(x) else None
        )

        # Convert any remaining NaNs to None
        forecast_df = forecast_df.where(pd.notnull(forecast_df), None)

        forecast_list = forecast_df.to_dict(orient='records')
        return jsonify(forecast_list), 200

    except SQLAlchemyError as e:
        return jsonify({"error": "Database error: " + str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500



@routes.route('/generate-fleet-heatmap', methods=['GET'])
def tracking_heatmap():
    vehicle_id = request.args.get('vehicle_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        heatmap_data = get_tracking_heatmap_data(vehicle_id, start_date, end_date)
        if not heatmap_data:
            return jsonify({"message": "No heatmap data found"}), 404
        return jsonify({"heatmap_data": heatmap_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API endpoint to get the list of vehicle IDs using raw SQL query
@routes.route('/get-vehicle-list', methods=['GET'])
def get_vehicle_list():
    try:
        db = db_session()
        query = text("SELECT vehicle_id, vehicle_number FROM vehicle ORDER BY vehicle_id")
        result = db.execute(query).mappings().all()

        vehicle_list = [
            {"vehicle_id": row["vehicle_id"], "vehicle_number": row["vehicle_number"]}
            for row in result
        ]
        return jsonify({"vehicles": vehicle_list}), 200
    except Exception as e:
        return jsonify({"message": "Error fetching vehicle list", "error": str(e)}), 500
    
    
@routes.route('/vehicle-health-status', methods=['GET'])
def get_vehicle_health_status():
    try:
        vehicle_reg_no = request.args.get('vehicle_reg_no', default=None, type=str)
        results = get_vehicle_health_json(vehicle_reg_no=vehicle_reg_no)

        if not results:
            return jsonify({"message": "No vehicle health data found"}), 404

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route('/failure-analysis', methods=['GET'])
def failure_analysis():
    try:
        # Get vehicle_number from query parameters
        vehicle_number = request.args.get('vehicle_number', default=None, type=str)

        if not vehicle_number:
            return jsonify({"error": "Please provide vehicle_number as a query parameter."}), 400

        # Start a session using the scoped session
        with db_session() as session:  # Using db_session here
            # Load the failure data using the session
            df_failure_data, replacement_dict = load_failure_data(session)

            # Filter data for the specified vehicle_number
            filtered_df = df_failure_data[df_failure_data["vehicle_number"] == vehicle_number]

            if filtered_df.empty:
                return jsonify({"message": f"No failure records found for vehicle: {vehicle_number}"}), 404

            if len(filtered_df) < 2:
                return jsonify({
                    "cluster_data": [],
                    "predictions": [],
                    "silhouette_score": 0,
                    "message": "Not enough data to perform clustering or rules"
                }), 200

            # Perform clustering and association rule generation
            cluster_data, silhouette_avg, filtered_df_with_clusters = cluster_failure_reasons(filtered_df)
            predictions = get_association_rules(filtered_df_with_clusters, replacement_dict, clusters=True)

            if not predictions and cluster_data:
                predictions = [{"cluster": 0, "rules": [cluster_data[0]["highlight"]]}]

            return jsonify({
                "cluster_data": cluster_data,
                "predictions": predictions,
                "silhouette_score": silhouette_avg
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500