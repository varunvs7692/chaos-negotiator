import React from "react";

export default function RiskCard({ risk, confidence, level }) {
  return (
    <div className="card">
      <h2>Deployment Risk</h2>

      <div className="metric">
        <span>Risk</span>
        <strong>{risk}%</strong>
      </div>

      <div className="metric">
        <span>Confidence</span>
        <strong>{confidence}%</strong>
      </div>

      <div className={`badge ${level}`}>
        {level.toUpperCase()}
      </div>
    </div>
  );
}
