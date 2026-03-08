import React, { useEffect, useMemo, useState } from "react";
import RiskCard from "../components/RiskCard";
import CanaryProgress from "../components/CanaryProgress";
import api from "../services/api";

const initialRisk = {
  risk_score: 0,
  risk_level: "unknown",
  confidence_percent: 0,
  identified_factors: [],
  predicted_error_rate_increase: 0,
  predicted_latency_increase: 0,
};

export default function Dashboard() {
  const [risk, setRisk] = useState(initialRisk);
  const [canary, setCanary] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadCanary() {
      try {
        const response = await api.get("/api/dashboard/canary");
        if (isMounted) {
          setCanary(response.data);
        }
      } catch (loadError) {
        if (isMounted) {
          setError("Failed to load canary strategy.");
        }
      }
    }

    loadCanary();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/risk`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setRisk(payload);
        setLastUpdate(new Date().toLocaleTimeString());
        setError(null);
      } catch (parseError) {
        setError("Error processing incoming data.");
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error.");
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  const currentStage = useMemo(() => {
    if (!canary?.stages?.length) {
      return "pending";
    }
    return canary.stages[0].name;
  }, [canary]);

  const currentTraffic = useMemo(() => {
    if (!canary?.stages?.length) {
      return 0;
    }
    return canary.stages[0].traffic_percent;
  }, [canary]);

  return (
    <div className="container">
      <h1>Chaos Negotiator Dashboard</h1>
      <div className={`status ${error ? "error" : isConnected ? "ok" : "pending"}`}>
        {error ? (
          <>
            <strong>Error:</strong> {error}
          </>
        ) : isConnected ? (
          <>
            <strong>Connected</strong> <span>Last update: {lastUpdate || "just now"}</span>
          </>
        ) : (
          <strong>Connecting...</strong>
        )}
      </div>

      <div className="grid">
        <RiskCard
          risk={risk.risk_score}
          confidence={risk.confidence_percent}
          level={risk.risk_level}
        />

        <CanaryProgress currentStage={currentStage} traffic={currentTraffic} />
      </div>

      <div className="card">
        <h2>Live Signals</h2>
        <div className="metric">
          <span>Predicted Error Rate Increase</span>
          <strong>{risk.predicted_error_rate_increase}%</strong>
        </div>
        <div className="metric">
          <span>Predicted Latency Increase</span>
          <strong>{risk.predicted_latency_increase}%</strong>
        </div>
        <div className="factors">
          {(risk.identified_factors || []).map((factor) => (
            <span key={factor} className="factor">
              {factor}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
