import React, { useEffect, useState, useCallback } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#FF6384",
  "#36A2EB",
  "#FFCE56",
];

const FailureAnalysisChart = () => {
  const [vehicleList, setVehicleList] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState("");
  const [clusterData, setClusterData] = useState([]);
  const [predictionHighlights, setPredictionHighlights] = useState([]);

  const fetchVehicleList = useCallback(async () => {
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
  }, []);

  const fetchFailureAnalysis = useCallback(async (vehicleNumber) => {
    try {
      const res = await fetch(
        `http://localhost:5000/failure-analysis?vehicle_number=${vehicleNumber}`
      );
      const data = await res.json();
      if (res.ok && data.cluster_data) {
        setClusterData(data.cluster_data);
        if (data.predictions?.length > 0) {
          const predicted = data.predictions.flatMap((p) => p.rules);
          setPredictionHighlights(predicted);
        } else {
          setPredictionHighlights([]);
        }
      } else {
        alert(data.message || "No cluster data found");
      }
    } catch (err) {
      console.error("Error fetching failure analysis:", err);
      alert("Failed to load failure analysis.");
    }
  }, []);

  useEffect(() => {
    fetchVehicleList();
  }, [fetchVehicleList]);

  useEffect(() => {
    if (selectedVehicle) {
      fetchFailureAnalysis(selectedVehicle);
    }
  }, [selectedVehicle, fetchFailureAnalysis]);

  const handleVehicleChange = (e) => {
    setSelectedVehicle(e.target.value);
  };

  // Calculate active indexes (to explode predicted slices)
  const activeIndexes = clusterData
    .map((entry, idx) =>
      predictionHighlights.includes(entry.highlight) ? idx : -1
    )
    .filter((idx) => idx !== -1);

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Failure Analysis Pie Chart</h2>

      <div className="mb-4">
        <label className="mr-2">Select Vehicle:</label>
        <select
          value={selectedVehicle}
          onChange={handleVehicleChange}
          className="border p-2"
        >
          {vehicleList.map((v) => (
            <option key={v.vehicle_number} value={v.vehicle_number}>
              {v.vehicle_number}
            </option>
          ))}
        </select>
      </div>

      {clusterData.length > 0 ? (
        <PieChart width={600} height={600}>
          <Pie
            data={clusterData}
            dataKey="cluster_size"
            nameKey="highlight"
            cx="50%"
            cy="50%"
            outerRadius={90}
            label={({ name, percent }) => {
              const percentage = (percent * 100).toFixed(0);
              if (predictionHighlights.includes(name)) {
                return `⭐ ${name} (${percentage}%)`; // Highlight label
              }
              return `${name} (${percentage}%)`;
            }}
            activeIndex={activeIndexes} // Explode predicted slices
            activeShape={{
              outerRadius: 110, // Move out predicted slices
            }}
            isAnimationActive={true} // Smooth animation
          >
            {clusterData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  predictionHighlights.includes(entry.highlight)
                    ? "#FF0000" // Red color for predicted slice
                    : COLORS[index % COLORS.length]
                }
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      ) : (
        <p>No cluster data available.</p>
      )}
    </div>
  );
};

export default FailureAnalysisChart;
