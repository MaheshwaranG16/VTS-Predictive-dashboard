import React, { useEffect, useState, useCallback } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import {
  BarChart,
  Bar,
  Pie,
  PieChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { Gantt, Task } from "gantt-task-react";
import "gantt-task-react/dist/index.css";

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
      const latLngs = points.map(([lat, lon]) => [lat, lon]);
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

const Dashboard = () => {
  const [vehicleList, setVehicleList] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState("");
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [healthData, setHealthData] = useState([]);
  const [ganttTasks, setGanttTasks] = useState([]);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [clusterData, setClusterData] = useState([]);
  const [predictionHighlights, setPredictionHighlights] = useState([]);
  const [highlightedSlice, setHighlightedSlice] = useState(null); // Track which slice is highlighted
  const highlightedColor = "#ffcc00"; // Yellow for hover effect
  const colors = [
    "#8884d8",
    "#82ca9d",
    "#ff4d4f",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
  ];

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

  const fetchHealthData = useCallback(async (vehicleNumber) => {
    try {
      const res = await fetch(
        `http://localhost:5000/vehicle-health-status?vehicle_reg_no=${vehicleNumber}`
      );
      const data = await res.json();
      if (res.ok && data.length > 0) {
        setHealthData(data);
      } else {
        setHealthData([]);
        alert("No health data found");
      }
    } catch (err) {
      console.error("Error fetching health data:", err);
      alert("Failed to load health data.");
    }
  }, []);

  const fetchHeatmapData = useCallback(
    async (vehicleNumber) => {
      setLoading(true);
      try {
        const query = new URLSearchParams({
          vehicle_id: vehicleNumber,
          start_date: startDate || "",
          end_date: endDate || "",
        });

        const res = await fetch(
          `http://localhost:5000/generate-fleet-heatmap?${query}`
        );
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
    },
    [startDate, endDate]
  );

  const fetchGanttTasks = useCallback(async (vehicleNumber) => {
    try {
      const res = await fetch("http://localhost:5000/predictive_maintenance");
      const data = await res.json();
      const filtered = data
        .filter((item) => item.vehicle_reg_no === vehicleNumber)
        .map((item, index) => {
          const start = item.next_expected_replacement
            ? new Date(item.next_expected_replacement)
            : null;
          const end = start
            ? new Date(start.getTime() + 1 * 24 * 60 * 60 * 1000)
            : null;

          let color = "#28a745";
          if (item.quantity_available === 0) color = "#dc3545";
          else if (item.quantity_available <= 10) color = "#fd7e14";

          return {
            id: `task-${index}`,
            name: `${item.spare_name} (${item.vehicle_reg_no})`,
            start,
            end,
            type: "task",
            progress: 100,
            isDisabled: false,
            usage_before_last_replacement:
              item.usage_before_last_replacement || 0,
            styles: {
              backgroundColor: color,
              backgroundSelectedColor: color,
            },
          };
        });

      setGanttTasks(filtered);

      const dates = filtered
        .map((task) => task.start?.getTime())
        .filter(Boolean);

      const minDate = Math.min(...dates);
      const maxDate = Math.max(...dates);
      const dateRange = maxDate - minDate;

      if (dateRange <= 86400000) {
        setZoomLevel(2);
      } else if (dateRange <= 604800000) {
        setZoomLevel(3);
      } else {
        setZoomLevel(4);
      }
    } catch (err) {
      console.error("Error fetching maintenance data:", err);
    }
  }, []);

  const fetchFailureAnalysis = useCallback(async (vehicleNumber) => {
    try {
      const res = await fetch(
        `http://localhost:5000/failure-analysis?vehicle_number=${vehicleNumber}`
      );
      const data = await res.json();

      if (res.ok && data) {
        // Handle the received data
        setClusterData(data.cluster_data);
        if (data.predictions?.length > 0) {
          const predicted = data.predictions.flatMap((p) => p.rules);
          setPredictionHighlights(predicted);
        } else {
          setPredictionHighlights([]);
        }
      } else {
        setClusterData([]);
        setPredictionHighlights([]);
        alert("No failure analysis data found.");
      }
    } catch (err) {
      console.error("Error fetching failure analysis data:", err);
      alert("Failed to load failure analysis data.");
    }
  }, []);

  useEffect(() => {
    fetchVehicleList();
  }, [fetchVehicleList]);

  useEffect(() => {
    if (selectedVehicle) {
      fetchHeatmapData(selectedVehicle);
      fetchHealthData(selectedVehicle);
      fetchGanttTasks(selectedVehicle);
      fetchFailureAnalysis(selectedVehicle);
    }
  }, [
    selectedVehicle,
    startDate,
    endDate,
    fetchHeatmapData,
    fetchHealthData,
    fetchGanttTasks,
    fetchFailureAnalysis,
  ]);

  const healthChartData = healthData.map((item) => ({
    date: item.date,
    score: item.anomaly_score === 1 ? 1 : -1,
  }));

  const usageChartData = ganttTasks.map((task) => ({
    spare_name: task.name.split(" (")[0],
    usage_before_last_replacement: task.usage_before_last_replacement,
    next_expected_replacement: task.start ? task.start.toDateString() : "N/A",
  }));

  const activeIndexes = clusterData
    .map((entry, idx) =>
      predictionHighlights.includes(entry.highlight) ? idx : -1
    )
    .filter((idx) => idx !== -1);

  return (
    <div style={{ padding: "20px" }}>
      <h2>VTS Dashboard</h2>

      {/* Filter + Gantt row */}
      <div style={{ display: "flex", gap: "20px", marginBottom: "20px" }}>
        {/* Filters */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {/* Row 1: Date filters */}
          <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
            <label>
              Start Date:
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{ marginLeft: "10px" }}
              />
            </label>

            <label>
              End Date:
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{ marginLeft: "10px" }}
              />
            </label>
          </div>

          {/* Row 2: Vehicle dropdown */}
          <div>
            <label>
              Vehicle:
              <select
                value={selectedVehicle}
                onChange={(e) => setSelectedVehicle(e.target.value)}
                style={{ marginLeft: "10px", padding: "5px", width: "200px" }}
              >
                {vehicleList.map((v) => (
                  <option key={v.vehicle_id} value={v.vehicle_number}>
                    {v.vehicle_number}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* Gantt Chart */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: "10px",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgb(29, 113, 116)",
            overflowX: "auto",
          }}
        >
          <h4 style={{ marginTop: 0 }}>Spare Replacement Schedule</h4>
          {ganttTasks.filter((t) => t.start).length > 0 ? (
            <Gantt
              tasks={ganttTasks.filter((t) => t.start)}
              zoomLevel={zoomLevel}
              listCellWidth=""
              rowHeight={30}
            />
          ) : (
            <p>No upcoming replacements.</p>
          )}
        </div>
      </div>

      {/* Fleet Heatmap + Vehicle Health */}
      <div
        style={{
          display: "flex",
          gap: "20px",
          alignItems: "stretch",
          marginBottom: "20px",
        }}
      >
        {/* Heatmap */}
        <div
          style={{
            flex: 1.5,
            background: "#fff",
            padding: "10px",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgb(29, 113, 116)",
            minWidth: "300px",
          }}
        >
          <h3>Fleet Utilization</h3>
          <div style={{ height: "350px" }}>
            {points.length > 0 ? (
              <MapContainer
                center={[20.5937, 78.9629]}
                zoom={5}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <HeatmapLayer points={points} />
              </MapContainer>
            ) : (
              !loading && <p>No heatmap data available.</p>
            )}
          </div>
        </div>

        {/* Vehicle Health */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: "10px",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgb(29, 113, 116)",
          }}
        >
          <h3>Vehicle Health Status (Last 7d)</h3>
          {healthChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={healthChartData}>
                <CartesianGrid vertical={false} horizontal={false} />
                <XAxis dataKey="date" />
                <YAxis
                  domain={[-1.2, 1.2]}
                  axisLine={false}
                  tickLine={false}
                  ticks={[0]} // Only show 0 as a tick
                  tick={{ fill: "transparent" }} // Hide the tick label
                />
                <ReferenceLine y={0} stroke="#000" strokeWidth={2} />
                <Tooltip formatter={(v) => (v === 1 ? "Healthy" : "Anomaly")} />
                <Bar dataKey="score" barSize={50}>
                  {healthChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.score === 1 ? "#195e33" : "#bf0a1f"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p>No health data available.</p>
          )}
        </div>
      </div>

      {/* Spare Usage Hours + Failure Clusters */}
      <div
        style={{
          display: "flex",
          gap: "20px",
          alignItems: "stretch",
          marginBottom: "20px",
        }}
      >
        {/* Spare Usage */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: "10px",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgb(29, 113, 116)",
          }}
        >
          <h3>Spare Usage Hours Before Replacement</h3>
          {usageChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={usageChartData}>
                <CartesianGrid vertical={false} horizontal={false} />
                <XAxis dataKey="spare_name" />
                <YAxis />
                <Tooltip
                  formatter={(value) => [`${value} hrs`, "Usage"]}
                  labelFormatter={(label, payload) =>
                    `Spare: ${label}\nNext: ${
                      payload?.[0]?.payload?.next_expected_replacement || "N/A"
                    }`
                  }
                />
                <Bar
                  dataKey="usage_before_last_replacement"
                  fill="#8884d8"
                  barSize={50}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p>No usage data available.</p>
          )}
        </div>

        {/* Failure Clusters */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: "10px",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgb(29, 113, 116)",
          }}
        >
          <h3>Expected Spare Failure</h3>
          {clusterData.length > 0 ? (
            <>
              <ResponsiveContainer width="90%" height={250}>
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
                        return `‼️ ${name} (${percentage}%)`; // Highlight label
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
                            : colors[index % colors.length]
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </>
          ) : (
            <p>No failure analysis data available.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
