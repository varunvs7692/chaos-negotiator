# Dashboard Guide

## Overview

The Chaos Negotiator **Interactive Dashboard** provides real-time visualization of:
- **Risk Assessments**: Risk score (0-100) and confidence levels (0-100%)
- **Canary Strategies**: Dynamic stage recommendations based on risk and confidence
- **Deployment History**: Recent deployment outcomes with actual metrics vs predictions
- **Guardrails**: Error rate and latency thresholds that trigger rollbacks

## Starting the Dashboard

1. **Start the FastAPI server** (or use uvicorn directly):
   ```bash
   python -m chaos_negotiator.server
   # or, for live code reloading:
   uvicorn chaos_negotiator.agent.api:app --reload
   ```
   The server listens on `http://localhost:8000` by default and provides the `/api` endpoints the UI consumes.

2. **Open the dashboard**:
   Navigate to `http://localhost:8000` in your browser. The dashboard will load automatically.

> The front-end uses an internal poll to refresh data every 10 seconds, so it stays up-to-date without manual page reloads.

## Dashboard Components

### 1. Risk Assessment Card
Located at the top of the dashboard, displays:
- **Risk Score**: Visual gauge showing 0-100 risk level
  - **Green** (0-29): Low risk, safe to deploy rapidly
  - **Yellow** (30-49): Moderate risk, staged approach recommended
  - **Orange** (50-69): High risk, cautious deployment required
  - **Red** (70+): Critical risk, minimal traffic initially

- **Confidence Level**: Progress bar showing 0-100% confidence in the prediction
  - Combines: Predictor agreement (60%) + Heuristic baseline (20%) + Historical calibration (20%)
  - Higher confidence means the risk prediction is more reliable

- **Predicted Metrics**:
  - Estimated error rate increase
  - Estimated P95 latency increase
  - Risk factors contributing to the score

### 2. Canary Deployment Timeline
Shows the recommended multi-stage rollout strategy:
- **Stages**: Ordered list of traffic increase steps
  - Stage 1 (Smoke): Very small traffic percentage (5-25%) to detect critical issues
  - Stage 2-4 (Light, Half, Majority): Incremental traffic increases (10%-50%)
  - Stage 5 (Full): 100% traffic, full rollout complete

- **Stage Details**:
  - Traffic percentage for this stage
  - Duration in seconds before advancing to the next stage
  - Visual progress bars showing traffic ramp

- **Strategy Note**: Explains the rollout approach based on risk/confidence combination:
  - **Cautious** (high risk + low confidence): 5 stages, very slow
  - **Moderate** (high risk + confidence): 4 stages, balanced
  - **Learning** (low risk + low confidence): 5 stages, discovery mode
  - **Rapid** (low risk + high confidence): 3 stages, fast deployment

### 3. Guardrail Summary
Displays the contract constraints that trigger automatic rollbacks:
- **Error Rate Threshold**: Maximum acceptable increase in error rate (0.2-0.5%)
  - `0.2%`: Very strict (critical systems, e.g., user auth)
  - `0.35%`: Standard (most services)
  - `0.5%`: Relaxed (non-critical services)

- **Latency Threshold**: Maximum acceptable latency increase (200ms or 500ms)
  - `200ms`: Strict (detected cache layer changes, speed-sensitive endpoints)
  - `500ms`: Standard (normal deployment)

- **Rollback Authority**:
  - ✓ **Automatic**: System triggers rollback if guardrails violated
  - ✗ **Manual**: Alerts team for approval before rollback

### 4. Deployment History Table
Shows recent deployment outcomes (last 20 deployments):
- **Time**: When the deployment occurred
- **Deployment ID**: Short ID of the deployment
- **Predicted Risk**: 
  - H (Heuristic score)
  - M (ML score)
  - E (Ensemble final score)
- **Actual Error Rate**: Observed error rate increase
- **Actual Latency Δ**: Observed latency increase in milliseconds
- **Outcome**: 
  - ✅ **Success** (green): Deployment completed successfully
  - ⚠️ **Rollback** (red): Automatic rollback triggered

**Metrics Highlighted**:
- Error rate > 1%: Highlighted in orange
- Latency change > 200ms: Highlighted in orange

## API Endpoints

The dashboard consumes these backend API endpoints:

### GET `/api/dashboard/risk`
Returns the latest risk assessment:
```json
{
  "risk_score": 45,
  "risk_level": "MODERATE",
  "confidence_percent": 75,
  "identified_factors": ["MULTI_SERVICE_CHANGE", "DATABASE_SCHEMA_CHANGE"],
  "predicted_error_rate_increase": 0.3,
  "predicted_latency_increase": 150
}
```

### GET `/api/dashboard/history`
Returns recent deployment outcomes (configurable limit, default 20):
```json
{
  "total": 15,
  "outcomes": [
    {
      "deployment_id": "abc123...",
      "heuristic_score": 45,
      "ml_score": 0.38,
      "final_score": 42,
      "actual_error_rate": 0.28,
      "actual_latency_change": 120,
      "rollback_triggered": false,
      "timestamp": "2024-01-20T14:35:22.123456"
    }
  ]
}
```

### GET `/api/dashboard/canary`
Returns the canary policy for the current scenario:
```json
{
  "deployment_id": "def456...",
  "risk_score": 65,
  "confidence_percent": 82,
  "error_rate_threshold": 0.35,
  "latency_threshold_ms": 500,
  "stages": [
    {
      "stage_number": 1,
      "traffic_percent": 5,
      "duration_seconds": 300,
      "name": "smoke"
    },
    {
      "stage_number": 2,
      "traffic_percent": 25,
      "duration_seconds": 600,
      "name": "light"
    }
  ]
}
```

## Auto-Refresh

The dashboard **auto-refreshes every 10 seconds** to show the latest data. You can manually refresh by pressing `F5` or clicking your browser's refresh button.

## Interpreting the Dashboard

### Risk Score Interpretation
- **0-29 (Green)**: Safe. Low risk deployments can proceed quickly with minimal guardrails.
- **30-49 (Yellow)**: Caution. Moderate risk requires careful monitoring and staged rollout.
- **50-69 (Orange)**: High risk. Slow, incremental rollout with strict guardrails.
- **70+ (Red)**: Critical. Minimal initial traffic, extensive monitoring, manual approval recommended.

### Confidence Interpretation
- **80-100%**: High confidence. System is very sure about the risk prediction. Deploy according to recommended stages.
- **60-79%**: Good confidence. Risk prediction is reliable. Use recommended strategy.
- **40-59%**: Moderate confidence. Consider manual review or additional testing.
- **0-39%**: Low confidence. System lacks training data; use conservative approach with manual oversight.

### Stage Duration
Stage duration auto-scales based on risk:
- Low risk: 0.8× base duration (faster progression)
- Moderate risk: 1.2× base duration (balanced)
- High risk: 1.8-2.0× base duration (slower progression)

## Learning Loop Integration

Each deployment outcome updates the system's ensemble weights:
- **Heuristic Predictor**: Rule-based (file count, API changes, DB migrations, etc.)
- **ML Predictor**: Lightweight neural-style predictor trained on historical outcomes
- **Weights**: Auto-tuned based on prediction accuracy

The dashboard history table shows all three scores (H, M, E) so you can observe how the ensemble is learning and adapting over time.

## Troubleshooting

### Dashboard not loading
1. Ensure server is running: `python -m chaos_negotiator.server`
2. Check console for errors: `F12` → **Console** tab
3. Verify `/api/dashboard/risk`, `/api/dashboard/history`, `/api/dashboard/canary` respond with valid JSON

### Stale data
- Dashboard refreshes every 10 seconds automatically
- Press `F5` to force-refresh
- Check server logs for API errors

### No deployment history
- History is stored in SQLite at `deployment_history.db` (configurable via `CN_HISTORY_DB` env var)
- Run `/demo/default` to generate sample deployment outcomes
- History appears after first deployment

## Environment Variables

- **`CN_HISTORY_DB`**: Path to SQLite deployment history database (default: `deployment_history.db`)
- **`CN_HEURISTIC_WEIGHT`**: Heuristic predictor weight in ensemble 0.0-1.0 (default: 0.6)
- **`CN_ML_WEIGHT`**: ML predictor weight in ensemble 0.0-1.0 (default: 0.4)
- **`API_AUTH_KEY`**: Optional API key for protecting endpoints

## Advanced Features

### Canary Policy Customization
The canary orchestrator generates policies based on a risk/confidence matrix:

```
Risk 70+, Conf any     → 5 slow stages (2× duration)
Risk 50, Conf 60+      → 4 moderate stages (1.2× duration)
Risk 50, Conf <60      → 5 slow stages (1.8× duration)
Risk <30, Conf 80+     → 3 fast stages (0.8× duration)
```

### Learning from Outcomes
To record a real deployment outcome and improve weights:

```python
agent.record_deployment_result(
    context=deployment_context,
    actual_error_rate=0.15,
    actual_latency=120,
    rollback_triggered=False
)
```

The ensemble automatically tunes its weights after recording outcomes.

### Confidence Calibration
Confidence is computed as:
$$\text{Confidence} = 0.6 \times \text{Agreement} + 0.2 \times \text{Baseline} + 0.2 \times \text{Historical Calibration}$$

- **Agreement**: How much ML and heuristic predictors agree (0-100%)
- **Baseline**: Default 50% (neutral starting point)
- **Historical Calibration**: Based on recent prediction errors (inverse-weighted)

## Next Steps

1. **Run a deployment**: Use `/demo/default`, `high-risk`, or `low-risk` scenario
2. **Monitor a canary**: Watch the timeline stages as the deployment progresses
3. **Check history**: View outcomes and learn from past deployments
4. **Adjust guardrails**: Modify error rate and latency thresholds as needed
5. **Integrate with CI/CD**: Call `/analyze` endpoint from your deployment pipeline

For more details, see [ARCHITECTURE.md](../ARCHITECTURE.md) and [README.md](../README.md).
