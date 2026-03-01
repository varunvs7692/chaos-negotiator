import React, { useEffect, useState } from "react";
import { fetchLatestDeployment } from "../services/api";
import RiskCard from "../components/RiskCard";
import CanaryProgress from "../components/CanaryProgress";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    // Fetch immediately on mount
    const fetchData = async () => {
      try {
        console.log("[Dashboard] 🔵 Fetching latest deployment...");
        const response = await fetchLatestDeployment();
        console.log("[Dashboard] ✅ Data received:", response);
        setData(response);
        setLastUpdate(new Date().toLocaleTimeString());
        setError(null);
      } catch (err) {
        console.error("[Dashboard] ❌ API Error:", err.message);
        setError(err.message);
      }
    };

    // Initial fetch
    fetchData();

    // Set up polling every 10 seconds
    console.log("[Dashboard] ⏰ Setting up 10s polling interval");
    const id = setInterval(() => {
      console.log(`[Dashboard] 🔄 Poll tick at ${new Date().toLocaleTimeString()}`);
      fetchData();
    }, 10000);

    return () => {
      clearInterval(id);
      console.log("[Dashboard] 🛑 Cleaned up polling interval on unmount");
    };
  }, []);

  return (
    <div className="container">
      <h1>Chaos Negotiator Dashboard</h1>
      
      {/* Status bar */}
      <div style={{ 
        padding: "1rem", 
        marginBottom: "1rem",
        backgroundColor: error ? "#fee" : "#efe",
        borderRadius: "4px",
        border: `1px solid ${error ? "#c00" : "#0c0"}`
      }}>
        {error ? (
          <>
            <strong>❌ API Error:</strong> {error}
          </>
        ) : lastUpdate ? (
          <>
            <strong>✅ Connected</strong> | Last update: {lastUpdate}
          </>
        ) : (
          <>
            <strong>🔄 Loading...</strong>
          </>
        )}
      </div>

      {!data ? (
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <p>Waiting for data...</p>
        </div>
      ) : (
        <>
          <RiskCard
            risk={data.risk_percent}
            confidence={data.confidence_percent}
            level={data.risk_level}
          />

          <CanaryProgress
            currentStage={data.canary_stage}
            traffic={data.traffic_percent}
          />
        </>
      )}
    </div>
  );
}
