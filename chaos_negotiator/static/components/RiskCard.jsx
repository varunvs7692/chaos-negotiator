import React from 'react';

export default function RiskCard({ data }) {
  const getRiskColor = (score) => {
    if (score >= 70) return '#ff4444';
    if (score >= 50) return '#ffaa00';
    if (score >= 30) return '#ffdd44';
    return '#44dd44';
  };

  const getConfidenceColor = (conf) => {
    if (conf >= 80) return '#44dd44';
    if (conf >= 60) return '#ffdd44';
    if (conf >= 40) return '#ffaa00';
    return '#ff4444';
  };

  return (
    <div className="risk-card">
      <div className="risk-circle">
        <svg viewBox="0 0 100 100" className="risk-gauge">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" strokeWidth="2" />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={getRiskColor(data.risk_score)}
            strokeWidth="8"
            strokeDasharray={`${(data.risk_score / 100) * 282} 282`}
            strokeLinecap="round"
          />
          <text x="50" y="45" textAnchor="middle" fontSize="28" fontWeight="bold" fill={getRiskColor(data.risk_score)}>
            {Math.round(data.risk_score)}
          </text>
          <text x="50" y="60" textAnchor="middle" fontSize="12" fill="#666">
            Risk Score
          </text>
        </svg>
      </div>

      <div className="risk-details">
        <div className="detail-row">
          <label>Risk Level:</label>
          <span className="risk-level" style={{ color: getRiskColor(data.risk_score) }}>
            {data.risk_level}
          </span>
        </div>

        <div className="detail-row">
          <label>Confidence:</label>
          <div className="confidence-bar">
            <div
              className="confidence-fill"
              style={{
                width: `${data.confidence_percent}%`,
                backgroundColor: getConfidenceColor(data.confidence_percent),
              }}
            />
          </div>
          <span className="confidence-text">{Math.round(data.confidence_percent)}%</span>
        </div>

        <div className="detail-row">
          <label>Predicted Error Rate ↑:</label>
          <span>{data.predicted_error_rate_increase}%</span>
        </div>

        <div className="detail-row">
          <label>Predicted Latency ↑:</label>
          <span>{data.predicted_latency_increase}ms</span>
        </div>

        {data.identified_factors && data.identified_factors.length > 0 && (
          <div className="detail-row full-width">
            <label>Risk Factors:</label>
            <div className="factors-list">
              {data.identified_factors.map((factor, idx) => (
                <span key={idx} className="factor-badge">
                  {factor}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
