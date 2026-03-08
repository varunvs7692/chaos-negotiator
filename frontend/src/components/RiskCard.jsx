import React from "react";

export default function RiskCard({ risk, confidence, level }) {
  const normalizedLevel = level || "unknown";

  return (
    <section className={`card risk-card risk-${normalizedLevel}`}>
      <div className="card-header">
        <div>
          <p className="eyebrow">Live Assessment</p>
          <h2>Deployment Risk</h2>
        </div>
        <div className={`badge ${normalizedLevel}`}>{normalizedLevel.toUpperCase()}</div>
      </div>

      <div className="risk-hero">
        <div>
          <p className="hero-label">Risk Score</p>
          <div className="hero-value">{risk}%</div>
        </div>
        <div className="confidence-ring">
          <span>{confidence}%</span>
          <small>confidence</small>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-tile">
          <span>Risk band</span>
          <strong>{normalizedLevel}</strong>
        </div>
        <div className="metric-tile">
          <span>Confidence</span>
          <strong>{confidence}%</strong>
        </div>
      </div>
    </section>
  );
}
