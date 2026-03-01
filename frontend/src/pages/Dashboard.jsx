import React, { useEffect, useState } from "react";
import { fetchLatestDeployment } from "../services/api";
import RiskCard from "../components/RiskCard";
import CanaryProgress from "../components/CanaryProgress";

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchLatestDeployment().then(setData);

    const id = setInterval(() => {
      fetchLatestDeployment().then(setData);
    }, 10000);

    return () => clearInterval(id);
  }, []);

  if (!data) return <div>Loading...</div>;

  return (
    <div className="container">
      <h1>Chaos Negotiator Dashboard</h1>

      <RiskCard
        risk={data.risk_percent}
        confidence={data.confidence_percent}
        level={data.risk_level}
      />

      <CanaryProgress
        currentStage={data.canary_stage}
        traffic={data.traffic_percent}
      />
    </div>
  );
}
