# Quick Reference - Deployment History API

## The Problem ✋

Dashboard "Recent Deployment History" was always empty.

## The Solution ✅

Added `/api/deployments/record-result` endpoint to record actual deployment outcomes.

---

## Quick Start (30 seconds)

### 1. Start the server
```bash
python -m chaos_negotiator.server
```

### 2. Record a deployment
```bash
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "deploy-001",
    "actual_error_rate_percent": 0.08,
    "actual_latency_change_percent": 2.5,
    "rollback_triggered": false
  }'
```

### 3. Check history
```bash
curl http://localhost:8000/api/dashboard/history
```

### 4. Open dashboard
```
http://localhost:8000
```

Done! 📊 History now shows deployments.

---

## Request Model

```python
{
    "deployment_id": str,                    # Unique deployment identifier
    "actual_error_rate_percent": float,      # Observed error rate (0-100)
    "actual_latency_change_percent": float,  # Latency change observed (%)
    "rollback_triggered": bool               # Was rollback activated?
}
```

### Example Values
```json
{
    "deployment_id": "prod-payment-v2-2026-03-01",
    "actual_error_rate_percent": 0.15,       // 0.15% error rate observed
    "actual_latency_change_percent": 3.2,    // 3.2% latency increase
    "rollback_triggered": false              // No rollback needed
}
```

---

## Response

### Success (200)
```json
{
    "status": "success",
    "deployment_id": "prod-payment-v2-2026-03-01",
    "final_score": 68.5,
    "timestamp": "2026-03-01T15:45:22.123456"
}
```

### Error (400)
```json
{
    "detail": "Failed to record deployment result: ..."
}
```

---

## API Endpoint Reference

### POST `/api/deployments/record-result`

**Purpose:** Record the actual outcome of a deployment  
**Authentication:** Optional (API_AUTH_KEY if configured)  
**Content-Type:** `application/json`  

### GET `/api/dashboard/history?limit=10`

**Purpose:** Retrieve recent deployment outcomes  
**Query Params:** 
- `limit` (int, default=20) - Number of records to return  

**Response:**
```json
{
    "total": 5,
    "outcomes": [
        {
            "deployment_id": "deploy-001",
            "heuristic_score": 58.3,
            "ml_score": 62.1,
            "final_score": 60.2,
            "actual_error_rate": 0.08,
            "actual_latency_change": 2.5,
            "rollback_triggered": false,
            "timestamp": "2026-03-01T15:45:22.123456"
        },
        ...
    ]
}
```

---

## Integrated Examples

### Python
```python
import requests

def record_deployment_result(deployment_id, error_rate, latency_change, rollback):
    response = requests.post(
        "http://localhost:8000/api/deployments/record-result",
        json={
            "deployment_id": deployment_id,
            "actual_error_rate_percent": error_rate,
            "actual_latency_change_percent": latency_change,
            "rollback_triggered": rollback,
        }
    )
    return response.json()

# Use it
result = record_deployment_result("prod-001", 0.08, 2.5, False)
print(result['final_score'])  # 65.3
```

### Bash/Shell
```bash
#!/bin/bash

DEPLOY_ID="prod-deploy-$(date +%s)"

curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d "{
    \"deployment_id\": \"$DEPLOY_ID\",
    \"actual_error_rate_percent\": 0.05,
    \"actual_latency_change_percent\": 1.5,
    \"rollback_triggered\": false
  }"
```

### Flask Integration
```python
from flask import Flask
import requests

app = Flask(__name__)

@app.after_request
def record_deployment_metrics(response):
    """Record deployment outcome after request."""
    if request.path == "/api/deploy":
        requests.post(
            "http://chaos-negotiator:8000/api/deployments/record-result",
            json={
                "deployment_id": request.headers.get("X-Deploy-ID"),
                "actual_error_rate_percent": get_error_rate(),
                "actual_latency_change_percent": get_latency_change(),
                "rollback_triggered": should_rollback(),
            }
        )
    return response
```

### Docker/Kubernetes
```yaml
# In your deployment post-hook
apiVersion: v1
kind: Service
metadata:
  name: chaos-negotiator
spec:
  ports:
  - port: 8000
---
# After deployment completes, call:
# curl -X POST http://chaos-negotiator:8000/api/deployments/record-result ...
```

---

## What Gets Recorded

### Input Metrics (You Provide)
```
✓ deployment_id      - Your deployment identifier
✓ error_rate         - Actual error rate observed
✓ latency_change     - Actual latency change measured  
✓ rollback_triggered - Whether rollback was executed
```

### Calculated Scores (Agent Calculates)
```
✓ heuristic_score    - Rule-based risk score
✓ ml_score           - ML model prediction
✓ final_score        - Ensemble weighted score
```

### Stored Data (Goes to SQLite)
```
✓ deployment_id      - Identifier
✓ All input metrics  - Actual observations
✓ All calculated scores
✓ timestamp          - When recorded (UTC)
```

### Used For Learning
```
✓ Accuracy tracking  - Predicted vs actual
✓ Weight adjustment  - ML ensemble tuning
✓ Bias detection     - Systematic error analysis
✓ Confidence scoring - Decision reliability
```

---

## Testing

### Automated Tests
```bash
# Full test suite
python test_deployment_history_flow.py

# Interactive demo
python demo_deployment_history.py
```

### Manual Test
```bash
# 1. Record result
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{"deployment_id":"test","actual_error_rate_percent":0.1,"actual_latency_change_percent":1.0,"rollback_triggered":false}'

# 2. Check history
curl http://localhost:8000/api/dashboard/history | jq '.'

# 3. Count records
curl http://localhost:8000/api/dashboard/history | jq '.total'
```

---

## Server Logs

### When Recording
```
============================================================
📝 Recording deployment result: prod-001
  Actual Error Rate: 0.08%
  Actual Latency Change: 2.5%
  Rollback Triggered: False
✅ Saving outcome to history store...
  Heuristic Score: 58.3
  ML Score: 62.1
  Final Score: 60.2
✏️ Outcome saved successfully
============================================================
```

### When Retrieving
```
[Log shows GET request to /api/dashboard/history]
[Returns JSON with outcomes array]
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `503: Agent not initialized` | Server not running. Start with `python -m chaos_negotiator.server` |
| `400: Failed to record result` | Check request format matches model. See Request Model above. |
| History still empty | Verify server is running. Check logs for POST request. |
| `Connection refused` | Ensure server is on port 8000. Check firewall. |

---

## Key Files

| File | Purpose |
|------|---------|
| `chaos_negotiator/server.py` | API endpoint (POST /record-result, GET /history) |
| `chaos_negotiator/agent/agent.py` | Outcome recording logic + logging |
| `test_deployment_history_flow.py` | Test suite |
| `demo_deployment_history.py` | Interactive demo |
| `DEPLOYMENT_HISTORY_FIXED.md` | Full documentation |
| `CODE_CHANGES_SUMMARY.md` | Detailed code changes |

---

## The Data Flow

```
┌──────────────────────────┐
│ Your Deployment          │
└──────────┬───────────────┘
           │
           ├─→ Observes metrics
           │   (error rate, latency)
           │
           v
┌──────────────────────────┐
│ Your Application         │
│ (calls our API)          │
└──────────┬───────────────┘
           │
           v
┌──────────────────────────────────────────────────┐
│ POST /api/deployments/record-result              │
│ {                                                │
│   "deployment_id": "...",                        │
│   "actual_error_rate_percent": 0.08,             │
│   "actual_latency_change_percent": 2.5,          │
│   "rollback_triggered": false                    │
│ }                                                │
└──────────┬───────────────────────────────────────┘
           │
           v
┌──────────────────────────────────┐
│ Chaos Negotiator Agent           │
│ • Predicts risk                  │
│ • Calculates scores              │
│ • Saves to SQLite                │
└──────────┬──────────────────────┘
           │
           v
┌──────────────────────────────────┐
│ SQLite History Store             │
│ (deployment_history.db)          │
└──────────┬──────────────────────┘
           │
           v
┌──────────────────────────────────┐
│ GET /api/dashboard/history       │
│ ← Returns stored outcomes        │
└──────────┬──────────────────────┘
           │
           v
┌──────────────────────────────────┐
│ Dashboard                        │
│ "Recent Deployment History" ✅   │
└──────────────────────────────────┘
           │
           v
┌──────────────────────────────────┐
│ Learning Loop                    │
│ • Improve predictions            │
│ • Auto-tune weights              │
│ • Extract patterns               │
└──────────────────────────────────┘
```

---

## Summary

You now have a complete feedback loop:

1. **Evaluate** ✅ - Risk assessment (`/api/deployments/latest`)
2. **Deploy** ✅ - Canary rollout with safety checks
3. **Observe** ✅ - Collect real metrics
4. **Record** ✅ NEW - POST `/api/deployments/record-result`
5. **Learn** ✅ - Auto-tuning improves predictions
6. **Repeat** ✅ - Better decisions next time

Your deployment history is no longer empty. The learning loop is live. 🎉
