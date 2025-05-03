import React, { useState } from "react";

function MailAlert() {
  const [statusMsg, setStatusMsg] = useState("");

  const sendFailureReport = async () => {
    try {
      const response = await fetch("/send-failure-report", {
        method: "POST",
      });
      const data = await response.json();
      setStatusMsg(data.message || data.error);
    } catch (error) {
      setStatusMsg("Error sending report.");
    }
  };

  return (
    <div>
      {/* Other dashboard content here */}

      <button onClick={sendFailureReport}>Send Report</button>
      <p style={{ color: "green", fontWeight: "bold" }}>{statusMsg}</p>
    </div>
  );
}

export default MailAlert;
