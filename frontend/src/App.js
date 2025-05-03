import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";
import Dashboard from "./pages/Dashboard";
import MailAlert from "./pages/MailAlert";

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/alert" element={<MailAlert />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
