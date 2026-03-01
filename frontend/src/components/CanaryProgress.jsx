import React from "react";

const stages = ["smoke", "light", "half", "majority", "full"];

export default function CanaryProgress({ currentStage, traffic }) {
  return (
    <div className="card">
      <h2>Canary Rollout</h2>

      <p>
        Current Stage: <strong>{currentStage}</strong>
      </p>
      <p>
        Traffic: <strong>{traffic}%</strong>
      </p>

      <div className="stage-bar">
        {stages.map((stage) => (
          <span
            key={stage}
            className={
              stage === currentStage ? "stage active" : "stage"
            }
          >
            {stage}
          </span>
        ))}
      </div>
    </div>
  );
}
