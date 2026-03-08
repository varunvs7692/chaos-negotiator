import React from "react";

const stages = ["smoke", "light", "half", "majority", "full"];

export default function CanaryProgress({ currentStage, traffic }) {
  const activeIndex = Math.max(stages.indexOf(currentStage), 0);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">Release Safety</p>
          <h2>Canary Rollout</h2>
        </div>
        <div className="traffic-pill">{traffic}% traffic</div>
      </div>

      <div className="progress-track" aria-hidden="true">
        <div
          className="progress-fill"
          style={{ width: `${((activeIndex + 1) / stages.length) * 100}%` }}
        />
      </div>

      <div className="stage-list">
        {stages.map((stage, index) => (
          <div
            key={stage}
            className={`stage-node ${index <= activeIndex ? "done" : ""} ${
              stage === currentStage ? "active" : ""
            }`}
          >
            <span className="stage-dot" />
            <span className="stage-label">{stage}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
