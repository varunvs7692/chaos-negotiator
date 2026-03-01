import React from 'react';

export default function HistoryTable({ data }) {
  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  };

  const getOutcomeColor = (rollback) => {
    return rollback ? '#ff4444' : '#44dd44';
  };

  return (
    <div className="history-table">
      {data.outcomes && data.outcomes.length > 0 ? (
        <>
          <div className="history-summary">
            <span className="summary-item">
              Total Deployments: <strong>{data.total}</strong>
            </span>
            <span className="summary-item">
              Success Rate:{' '}
              <strong>
                {Math.round(
                  ((data.total - data.outcomes.filter((o) => o.rollback_triggered).length) / data.total) * 100
                )}
                %
              </strong>
            </span>
          </div>

          <table className="outcomes-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Deployment ID</th>
                <th>Predicted Risk</th>
                <th>Actual Error Rate</th>
                <th>Actual Latency Δ</th>
                <th>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {data.outcomes.map((outcome, idx) => (
                <tr key={idx}>
                  <td className="time-cell">{formatDate(outcome.timestamp)}</td>
                  <td className="id-cell" title={outcome.deployment_id}>
                    {outcome.deployment_id.substring(0, 8)}...
                  </td>
                  <td className="score-cell">
                    <div className="ensemble-scores">
                      <span className="mini-badge" title="Heuristic Score">
                        H: {Math.round(outcome.heuristic_score)}
                      </span>
                      <span className="mini-badge" title="ML Score">
                        M: {Math.round(outcome.ml_score * 100)}
                      </span>
                      <span className="mini-badge bold" title="Final Ensemble Score">
                        E: {Math.round(outcome.final_score)}
                      </span>
                    </div>
                  </td>
                  <td className="metric-cell">
                    <span className={outcome.actual_error_rate > 1 ? 'metric-high' : ''}>
                      {outcome.actual_error_rate.toFixed(2)}%
                    </span>
                  </td>
                  <td className="metric-cell">
                    <span className={outcome.actual_latency_change > 200 ? 'metric-high' : ''}>
                      +{outcome.actual_latency_change.toFixed(0)}ms
                    </span>
                  </td>
                  <td className="outcome-cell">
                    <span
                      className={`outcome-badge ${outcome.rollback_triggered ? 'rollback' : 'success'}`}
                      style={{ backgroundColor: getOutcomeColor(outcome.rollback_triggered) }}
                    >
                      {outcome.rollback_triggered ? 'Rollback' : 'Success'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <div className="empty-state">
          <p>No deployment history yet. Run a deployment to see results here.</p>
        </div>
      )}
    </div>
  );
}
