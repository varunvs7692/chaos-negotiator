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
  deployment_id: "",
  service_name: "",
  environment: "",
  version: "",
  telemetry_source: "startup",
  telemetry_status: "degraded",
  telemetry_message: "",
  current_error_rate_percent: 0,
  current_p95_latency_ms: 0,
  current_qps: 0,
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

  const telemetryTone = error ? "error" : risk.telemetry_status === "degraded" ? "pending" : "ok";
  const telemetrySummary = error
    ? error
    : risk.telemetry_status === "degraded"
      ? risk.telemetry_message || "Live telemetry is not available yet."
      : `Source: ${risk.telemetry_source || "azure_monitor"}`;

  return (
    <div className="container">
      <section className="hero">
        <div>
          <p className="eyebrow">AI Deployment Control Center</p>
          <h1>Chaos Negotiator Dashboard</h1>
          <p className="hero-copy">
            Track live deployment risk, rollout posture, and reliability signals in one view.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-kicker">{risk.telemetry_status === "degraded" ? "Degraded" : "Streaming"}</span>
          <strong>{isConnected ? "Live feed active" : "Waiting for feed"}</strong>
          <small>{lastUpdate ? `Updated ${lastUpdate}` : "No live update yet"}</small>
          <small>{risk.service_name || "chaos-negotiator"}</small>
        </div>
      </section>

      <div className={`status ${telemetryTone}`}>
        {error ? (
          <>
            <strong>Error:</strong> {error}
          </>
        ) : isConnected ? (
          <>
            <strong>{risk.telemetry_status === "degraded" ? "Connected with fallback" : "Connected"}</strong>
            <span>{telemetrySummary}</span>
          </>
        ) : (
          <strong>Connecting...</strong>
        )}
      </div>

      <section className="meta-strip">
        <span className="meta-pill">Service: {risk.service_name || "unknown"}</span>
        <span className="meta-pill">Deployment: {risk.deployment_id || "awaiting event"}</span>
        <span className="meta-pill">Environment: {risk.environment || "unknown"}</span>
        <span className="meta-pill">Version: {risk.version || "unknown"}</span>
      </section>

      <div className="grid">
        <RiskCard
          risk={risk.risk_score}
          confidence={risk.confidence_percent}
          level={risk.risk_level}
        />

        <CanaryProgress currentStage={currentStage} traffic={currentTraffic} />
      </div>

      <section className="signals-grid">
        <div className="card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Reliability Signals</p>
              <h2>Live Telemetry</h2>
            </div>
          </div>
          <div className="metric-grid">
            <div className="metric-tile">
              <span>Current Error Rate</span>
              <strong>{Number(risk.current_error_rate_percent || 0).toFixed(2)}%</strong>
            </div>
            <div className="metric-tile">
              <span>Current P95 Latency</span>
              <strong>{Number(risk.current_p95_latency_ms || 0).toFixed(0)} ms</strong>
            </div>
            <div className="metric-tile">
              <span>Current QPS</span>
              <strong>{Number(risk.current_qps || 0).toFixed(1)}</strong>
            </div>
            <div className="metric-tile">
              <span>Telemetry Source</span>
              <strong>{risk.telemetry_source || "unknown"}</strong>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Risk Drivers</p>
              <h2>Identified Factors</h2>
            </div>
          </div>
          <div className="factors">
            {(risk.identified_factors || []).length ? (
              risk.identified_factors.map((factor) => (
                <span key={factor} className="factor">
                  {factor}
                </span>
              ))
            ) : (
              <span className="factor muted">No risk factors detected yet</span>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
