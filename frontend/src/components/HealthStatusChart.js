import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from "recharts";

const HealthStatusChart = ({ healthChartData }) => (
  <div
    className="flex-1 bg-white rounded-xl shadow-md p-4 border"
    style={{ height: "400px", minWidth: "300px" }}
  >
    <h3 className="text-xl font-semibold mb-2">Vehicle Health Status</h3>
    {healthChartData.length > 0 ? (
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={healthChartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={[-1.2, 1.2]} hide />
          <Tooltip
            formatter={(value) => (value === 1 ? "Healthy" : "Anomaly")}
          />
          <Legend />
          <Bar dataKey="score">
            {healthChartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.score === 1 ? "#82ca9d" : "#ff4d4f"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    ) : (
      <p>No health data available.</p>
    )}
  </div>
);

export default HealthStatusChart;
