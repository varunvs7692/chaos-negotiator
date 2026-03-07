import React, { useEffect, useState } from "react";
import RiskCard from "../components/RiskCard";
import CanaryProgress from "../components/CanaryProgress";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    console.log("[Dashboard] Setting up WebSocket connection...");
    const ws = new WebSocket("ws://localhost:8000/ws/dashboard");

    ws.onopen = () => {
      console.log("[Dashboard] WebSocket connection established.");
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        // The data from the server is a string that needs to be parsed.
        // It's also double-encoded because of how it's being sent from the backend.
        const parsedData = JSON.parse(event.data.replace(/'/g, '"'));
        console.log("[Dashboard] ✅ Data received via WebSocket:", parsedData);
        setData(parsedData);
        setLastUpdate(new Date().toLocaleTimeString());
        setError(null);
      } catch (err) {
        console.error("[Dashboard] ❌ Error parsing WebSocket message:", err.message);
        setError("Error processing incoming data.");
      }
    };

    ws.onerror = (err) => {
      console.error("[Dashboard] ❌ WebSocket Error:", err);
      setError("WebSocket connection error. Is the server running?");
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log("[Dashboard] WebSocket connection closed.");
      setIsConnected(false);
    };

    return () => {
      console.log("[Dashboard] 🛑 Closing WebSocket connection on unmount");
      ws.close();
    };
  }, []);

  return (
    <div className="container">
      <h1>Chaos Negotiator Dashboard</h1>
      
      {/* Status bar */}
      <div style={{ 
        padding: "1rem", 
        marginBottom: "1rem",
        backgroundColor: error ? "#fee" : isConnected ? "#efe" : "#ffe",
        borderRadius: "4px",
        border: `1px solid ${error ? "#c00" : isConnected ? "#0c0" : "#cc0"}`
      }}>
        {error ? (
          <>
            <strong>❌ API Error:</strong> {error}
          </>
        ) : isConnected ? (
          <>
            <strong>✅ Connected</strong> | Last update: {lastUpdate}
          </>
        ) : (
          <>
            <strong>🔄 Connecting...</strong>
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
