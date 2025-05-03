import React, { useEffect, useState } from "react";
import { Gantt, Task } from "gantt-task-react";
import "gantt-task-react/dist/index.css";

const GanttChart = () => {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/predictive_maintenance")
      .then((res) => res.json())
      .then((data) => {
        const ganttTasks = data
          .filter((item) => item.next_expected_replacement !== null)
          .map((item, index) => {
            const start = new Date(item.next_expected_replacement);
            const end = new Date(start.getTime() + 1 * 24 * 60 * 60 * 1000); // +1 day

            // Determine color based on quantity_available
            let color = "#28a745"; // green
            if (item.quantity_available === 0) {
              color = "#dc3545"; // red
            } else if (item.quantity_available <= 10) {
              color = "#fd7e14"; // orange
            }

            return {
              id: `task-${index}`,
              name: `${item.spare_name} (${item.vehicle_reg_no})`,
              start,
              end,
              type: "task",
              progress: 0,
              isDisabled: false,
              styles: {
                progressColor: color,
                progressSelectedColor: color,
              },
            };
          });

        setTasks(ganttTasks);
      })
      .catch((err) => console.error("Error fetching maintenance data:", err));
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Spare Replacement Schedule</h2>
      {tasks.length > 0 ? (
        <Gantt tasks={tasks} />
      ) : (
        <p>No upcoming replacements found.</p>
      )}
    </div>
  );
};

export default GanttChart;
