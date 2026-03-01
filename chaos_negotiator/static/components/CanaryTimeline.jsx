import React from 'react';

export default function CanaryTimeline({ data }) {
  const isHighRisk = data.risk_score >= 70;
  const isLowConfidence = data.confidence_percent < 50;

  return (
    <div className="canary-timeline">
      <div className="canary-info">
        <div className="info-badge">
          <span className="badge-label">Deployment ID:</span>
          <span className="badge-value">{data.deployment_id?.substring(0, 8)}...</span>
        </div>
        <div className="info-badge">
          <span className="badge-label">Risk:</span>
          <span className={`badge-value ${isHighRisk ? 'high-risk' : 'low-risk'}`}>
            {data.risk_score}
          </span>
        </div>
        <div className="info-badge">
          <span className="badge-label">Confidence:</span>
          <span className={`badge-value ${isLowConfidence ? 'low-conf' : 'high-conf'}`}>
            {data.confidence_percent}%
          </span>
        </div>
      </div>

      <div className="timeline-container">
        {data.stages.map((stage, idx) => {
          const isCurrentOrPassed = idx === 0; // First stage is current (simplified demo)
          const allPassed = idx < 0;

          return (
            <div key={idx} className="timeline-item">
              <div className={`stage-node ${isCurrentOrPassed ? 'current' : ''} ${allPassed ? 'passed' : ''}`}>
                <span className="stage-number">{stage.stage_number}</span>
              </div>
              <div className="stage-content">
                <div className="stage-name">{stage.name}</div>
                <div className="stage-details">
                  <div className="detail">
                    <span className="detail-label">Traffic:</span>
                    <span className="detail-value">{stage.traffic_percent}%</span>
                    <div className="traffic-bar">
                      <div className="traffic-fill" style={{ width: `${stage.traffic_percent}%` }} />
                    </div>
                  </div>
                  <div className="detail">
                    <span className="detail-label">Duration:</span>
                    <span className="detail-value">{stage.duration_seconds}s</span>
                  </div>
                </div>
              </div>
              {idx < data.stages.length - 1 && <div className="timeline-line" />}
            </div>
          );
        })}
      </div>

      <div className="strategy-note">
        {isHighRisk && isLowConfidence && (
          <p>
            ⚠️ <strong>Cautious Strategy:</strong> High risk + low confidence → slow, incremental rollout with very small initial traffic.
          </p>
        )}
        {isHighRisk && !isLowConfidence && (
          <p>
            ⚠️ <strong>Moderate Strategy:</strong> High risk but good confidence → measured rollout with medium initial traffic.
          </p>
        )}
        {!isHighRisk && isLowConfidence && (
          <p>
            📊 <strong>Learning Strategy:</strong> Low risk but low confidence → staged discovery with medium initial traffic.
          </p>
        )}
        {!isHighRisk && !isLowConfidence && (
          <p>
            ✅ <strong>Rapid Strategy:</strong> Low risk + high confidence → fast rollout with aggressive initial traffic.
          </p>
        )}
      </div>
    </div>
  );
}
