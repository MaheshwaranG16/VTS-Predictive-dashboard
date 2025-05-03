import React, { useEffect, useState } from "react";
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

    const latLngs = points.map(([lat, lng]) => [lat, lng]);
    const bounds = L.latLngBounds(latLngs);
    map.fitBounds(bounds);

    setTimeout(() => {
      map.invalidateSize();
    }, 100);

    return () => {
      map.removeLayer(heatLayer);
    };
  }, [map, points]);

  return null;
};

const FleetHeatmap = () => {
  const [vehicleList, setVehicleList] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState("");
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(""); // yyyy-mm-dd
  const [endDate, setEndDate] = useState("");

  const fetchVehicleList = async () => {
    try {
      const res = await fetch("http://localhost:5000/get-vehicle-list");
      const data = await res.json();
      if (res.ok && data.vehicles?.length > 0) {
        setVehicleList(data.vehicles);
        setSelectedVehicle(data.vehicles[0].vehicle_number);
      } else {
        alert(data.message || "No vehicles found");
      }
    } catch (err) {
      console.error("Error fetching vehicle list:", err);
      alert("Failed to load vehicle list.");
    }
  };

  const fetchHeatmapData = async (vehicleNumber) => {
    setLoading(true);
    try {
      const query = new URLSearchParams({
        vehicle_id: vehicleNumber,
        start_date: startDate || "", // "" to allow server to default to min
        end_date: endDate || "",     // "" to allow server to default to max
      });

      const res = await fetch(`http://localhost:5000/generate-fleet-heatmap?${query}`);
      const data = await res.json();

      if (res.ok && data.heatmap_data?.length > 0) {
        const formatted = data.heatmap_data.map(([lat, lon, count]) => [
          parseFloat(lat),
          parseFloat(lon),
          parseFloat(count),
        ]);
        setPoints(formatted);
      } else {
        setPoints([]);
        alert(data.message || "No heatmap data found");
      }
    } catch (err) {
      console.error("Error fetching heatmap:", err);
      alert("Failed to load heatmap data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVehicleList();
  }, []);

  useEffect(() => {
    if (selectedVehicle) {
      fetchHeatmapData(selectedVehicle);
    }
  }, [selectedVehicle, startDate, endDate]);

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Fleet Utilization Heatmap</h2>

      {/* Vehicle dropdown */}
      <div className="flex flex-col gap-4 md:flex-row items-center">
        <label>
          Vehicle Number:{" "}
          <select
            value={selectedVehicle}
            onChange={(e) => setSelectedVehicle(e.target.value)}
            className="p-2 border rounded"
          >
            {vehicleList.map((vehicle) => (
              <option key={vehicle.vehicle_id} value={vehicle.vehicle_number}>
                {vehicle.vehicle_number}
              </option>
            ))}
          </select>
          </label>
        {/* Date Range Inputs */}
        <div className="flex gap-2 items-center">
          <label>
            Start Date:{" "}
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="p-2 border rounded"
            />
          </label>
          <label>
            End Date:{" "}
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="p-2 border rounded"
            />
          </label>
        </div>
      </div>

      {loading && <p>Loading heatmap...</p>}

      <div style={{ height: "80vh", width: "100%" }}>
        {points.length > 0 ? (
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
          !loading && <p>No heatmap data available.</p>
        )}
      </div>
    </div>
  );
};

export default FleetHeatmap;

