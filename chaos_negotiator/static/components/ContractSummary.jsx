import React from 'react';

export default function ContractSummary({ data }) {
  const isStrictLatency = data.latency_threshold_ms === 200;

  return (
    <div className="contract-summary">
      <div className="guardrail-section">
        <h3>🛡️ Error Rate Guardrail</h3>
        <div className="guardrail-value">
          <span className="value">{data.error_rate_threshold.toFixed(2)}%</span>
          <span className="label">max acceptable error increase</span>
        </div>
        <p className="guardrail-description">
          {data.error_rate_threshold <= 0.2
            ? 'Very strict: critical system, minimal tolerance'
            : data.error_rate_threshold <= 0.35
              ? 'Standard: balanced safety and speed'
              : 'Relaxed: lower-priority service, more tolerance'}
        </p>
      </div>

      <div className="guardrail-section">
        <h3>⏱️ Latency Guardrail</h3>
        <div className="guardrail-value">
          <span className="value">{data.latency_threshold_ms}ms</span>
          <span className="label">max acceptable latency increase</span>
        </div>
        <p className="guardrail-description">
          {isStrictLatency
            ? 'Strict (200ms): cache layer changes detected, speed-sensitive endpoints'
            : 'Standard (500ms): typical deployment, normal latency tolerance'}
        </p>
      </div>

      <div className="guardrail-section">
        <h3>🔄 Rollback Authority</h3>
        <div className="rollback-setting">
          <span className={`setting-badge ${data.rollback_on_violation ? 'enabled' : 'disabled'}`}>
            {data.rollback_on_violation ? '✓ Automatic' : '✗ Manual'}
          </span>
        </div>
        <p className="guardrail-description">
          {data.rollback_on_violation
            ? 'System will automatically trigger rollback if guardrails are violated'
            : 'Manual approval required before rollback execution'}
        </p>
      </div>

      <div className="guardrail-hint">
        <strong>💡 How it works:</strong> During canary deployment, each stage is monitored against these guardrails. If error rate or latency
        exceeds the threshold, the deployment is either automatically rolled back or flagged for manual intervention.
      </div>
    </div>
  );
}
