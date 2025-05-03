import React, { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

const HeatmapLayer = ({ points }) => {
  const map = useMap();

  useEffect(() => {
    if (!map || !points.length) return;

    const heatLayer = L.heatLayer(points, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
    }).addTo(map);

    setTimeout(() => {
      map.invalidateSize();
      const latLngs = points.map(([lat, lng]) => [lat, lng]);
      if (latLngs.length > 0) {
        const bounds = L.latLngBounds(latLngs);
        map.fitBounds(bounds);
      }
    }, 300);

    return () => {
      map.removeLayer(heatLayer);
    };
  }, [map, points]);

  return null;
};

const FleetUtilization = ({ points, loading }) => {
  return (
    <div
      className="flex-1 bg-white rounded-xl shadow-md p-4 border"
      style={{ height: "400px", width: "80%" }}
    >
      <h3 className="text-xl font-semibold mb-2">Fleet Heatmap</h3>
      {loading ? (
        <p>Loading heatmap...</p>
      ) : points.length > 0 ? (
        <MapContainer
          center={[20.5937, 78.9629]}
          zoom={5}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <HeatmapLayer points={points} />
        </MapContainer>
      ) : (
        <p>No heatmap data available.</p>
      )}
    </div>
  );
};

export default FleetUtilization;
