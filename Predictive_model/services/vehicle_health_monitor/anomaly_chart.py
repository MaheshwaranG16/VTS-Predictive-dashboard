import pandas as pd
import plotly.graph_objects as go
import requests

def generate_anomaly_chart():
    # Fetch data from your Flask API
    response = requests.get("http://localhost:5000/vehicle-health-status")
    data = response.json()

    # Create DataFrame
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    # Health status to color mapping
    status_colors = {
        "Healthy": "#11502c",
        "At Risk": "#b90f28"
    }

    vehicles = df["vehicle_reg_no"].unique()
    fig = go.Figure()

    for i, vehicle in enumerate(vehicles):
        filtered = df[df["vehicle_reg_no"] == vehicle]
        colors = [status_colors[status] for status in filtered["health_status"]]
        
        fig.add_trace(go.Bar(
            x=filtered["date"],
            y=filtered["anomaly_score"],
            name=vehicle,
            visible=(i == 0),
            marker_color=colors,
            text=filtered["health_status"],
            hovertemplate="Date: %{x}<br>Score: %{y}<br>Status: %{text}<extra></extra>"
        ))

    dropdown_buttons = [
        {
            "label": v,
            "method": "update",
            "args": [
                {"visible": [v == vehicle for vehicle in vehicles]},
                {"title": f"Anomaly Score (Bar) - {v}"}
            ]
        } for v in vehicles
    ]

    fig.update_layout(
        updatemenus=[
            {
                "buttons": dropdown_buttons,
                "direction": "down",
                "showactive": True,
                "x": 0.5,
                "xanchor": "center",
                "y": 1.15,
                "yanchor": "top"
            }
        ],
        title=f"Anomaly Score (Bar) - {vehicles[0]}",
        xaxis_title="Date",
        yaxis_title="Anomaly Score",
        barmode='group'
    )

    fig.show()

if __name__ == "__main__":
    generate_anomaly_chart()