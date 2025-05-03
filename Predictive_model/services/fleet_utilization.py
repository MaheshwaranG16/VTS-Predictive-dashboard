from sqlalchemy.sql import text
from app.config import SessionLocal
import math

def get_tracking_heatmap_data(vehicle_id=None, start_date=None, end_date=None):
    session = SessionLocal()
    try:
        # Base query for heatmap data
        base_query = """
            SELECT 
                ROUND(CAST(td.latitude AS numeric), 2) AS lat_bin,
                ROUND(CAST(td.longitude AS numeric), 2) AS long_bin,
                COUNT(DISTINCT td.id) AS point_count,
                DATE(vehicle_timestamp) tracking_date
            FROM tracking_data td
            WHERE td.latitude IS NOT NULL
              AND td.longitude IS NOT NULL
              AND td.latitude != '0'
              AND td.longitude != '0'
        """

        # Filter parameters
        filters = ""
        params = {}

        # If specific filters are provided, add them to the query
        if vehicle_id:
            filters += " AND td.vehicle_reg_no = :vehicle_id"
            params['vehicle_id'] = vehicle_id

        # If dates are not provided, fetch the min and max dates from the tracking_data table
        if not start_date or not end_date:
            date_query = """
                SELECT MIN(DATE(td.vehicle_timestamp)) AS min_date, MAX(DATE(td.vehicle_timestamp)) AS max_date
                FROM tracking_data td
            """
            date_result = session.execute(text(date_query)).fetchone()
            if date_result:
                if not start_date:
                    start_date = date_result.min_date
                if not end_date:
                    end_date = date_result.max_date

        # If dates are provided, add them to the query
        if start_date:
            filters += " AND DATE(td.vehicle_timestamp) >= :start_date"
            params['start_date'] = start_date
        if end_date:
            filters += " AND DATE(td.vehicle_timestamp) <= :end_date"
            params['end_date'] = end_date

        # Final query with filters
        final_query = text(base_query + filters + """
            GROUP BY lat_bin, long_bin, tracking_date
            ORDER BY point_count DESC        
            """)

        result = session.execute(final_query, params).fetchall()

        # Process the result to return heatmap data
        heatmap_data = []
        for row in result:
            lat, lng, count, date = row.lat_bin, row.long_bin, row.point_count, row.tracking_date
            if lat is not None and lng is not None:
                try:
                    # Convert Decimal to float
                    if not (math.isnan(float(lat)) or math.isnan(float(lng))):
                        heatmap_data.append([float(lat), float(lng), count, date])
                except TypeError:
                    continue

        return heatmap_data

    finally:
        session.close()


if __name__ == "__main__":
    heatmap_data = get_tracking_heatmap_data(vehicle_id='TN99Z8438')
    print(heatmap_data)
