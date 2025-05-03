import React, { useEffect, useState } from "react";

const PredictiveMaintenanceTable = () => {
  const [data, setData] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(false);
  const [vehicleFilter, setVehicleFilter] = useState("");
  const [spareFilter, setSpareFilter] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:5000/predictive_maintenance");
      const json = await res.json();
      setData(json);
      setFiltered(json);
    } catch (error) {
      console.error("Error fetching predictive maintenance data:", error);
      alert("Failed to fetch predictive maintenance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    const result = data.filter((item) => {
      return (
        item.vehicle_reg_no
          .toLowerCase()
          .includes(vehicleFilter.toLowerCase()) &&
        item.spare_name.toLowerCase().includes(spareFilter.toLowerCase())
      );
    });
    setFiltered(result);
  }, [vehicleFilter, spareFilter, data]);

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Predictive Maintenance</h2>

      <div className="flex flex-col gap-4 md:flex-row items-center">
        <input
          type="text"
          placeholder="Filter by Vehicle Number"
          value={vehicleFilter}
          onChange={(e) => setVehicleFilter(e.target.value)}
          className="p-2 border rounded"
        />
        <input
          type="text"
          placeholder="Filter by Spare Name"
          value={spareFilter}
          onChange={(e) => setSpareFilter(e.target.value)}
          className="p-2 border rounded"
        />
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="overflow-auto">
          <table className="min-w-full border text-sm text-left">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-2">Vehicle Number</th>
                <th className="border p-2">Spare Name</th>
                <th className="border p-2">Quantity Available</th>
                <th className="border p-2">Unit Price</th>
                <th className="border p-2">Usage Before Last Replacement (hrs)</th>
                <th className="border p-2">Next Expected Replacement</th>
                <th className="border p-2">Emergency Condition</th>
                <th className="border p-2">Tamper Condition</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((item, index) => (
                  <tr key={index}>
                    <td className="border p-2">{item.vehicle_reg_no}</td>
                    <td className="border p-2">{item.spare_name}</td>
                    <td className="border p-2">{item.quantity_available}</td>
                    <td className="border p-2">{item.unit_price}</td>
                    <td className="border p-2">
                      {isNaN(item.usage_before_last_replacement)
                        ? "N/A"
                        : item.usage_before_last_replacement}
                    </td>
                    <td className="border p-2">
                      {item.next_expected_replacement
                        ? new Date(item.next_expected_replacement).toLocaleDateString()
                        : "N/A"}
                    </td>
                    <td className="border p-2">{item.emergency_condition}</td>
                    <td className="border p-2">{item.tamper_condition}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="p-2 text-center">
                    No data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PredictiveMaintenanceTable;
