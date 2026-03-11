# User Guide

## What This Project Does

Chaos Negotiator helps a user:

- evaluate deployment risk
- generate canary rollout guidance
- review and approve or reject deployments
- record real deployment outcomes
- view live or degraded telemetry in a dashboard

## Run It Locally

### 1. Install

```bash
git clone https://github.com/varunvs7692/chaos-negotiator.git
cd chaos-negotiator
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Useful variables:

- `API_AUTH_KEY`
- `GITHUB_WEBHOOK_SECRET`
- `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_MONITOR_WORKSPACE_ID`
- `CN_DASHBOARD_SERVICE_NAME`
- `CN_HISTORY_DB`
- `CN_APPROVAL_DB`

### 3. Start the app

```bash
python -m chaos_negotiator.server
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`

## Use the Dashboard

The dashboard shows:

- deployment risk
- confidence
- canary rollout stage
- telemetry status
- risk factors
- deployment history

If you see `Connected with fallback`, the app is running but live Azure telemetry is not available yet.

## Use the API

### Evaluate a deployment

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "demo123",
    "service_name": "payment-service",
    "environment": "production",
    "version": "v1.0.0",
    "changes": [
      {
        "file_path": "api/payment.py",
        "change_type": "modify",
        "lines_changed": 120,
        "risk_tags": ["api", "database"],
        "description": "Change payment orchestration path"
      }
    ]
  }'
```

### See pending approvals

```bash
curl http://127.0.0.1:8000/api/deployments/pending
```

### Approve a deployment

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/demo123/approve \
  -H "Content-Type: application/json" \
  -d '{"reason":"Reviewed and approved"}'
```

### Reject a deployment

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/demo123/reject \
  -H "Content-Type: application/json" \
  -d '{"reason":"Rollback proof is missing"}'
```

### Record a real result

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "demo123",
    "actual_error_rate_percent": 0.12,
    "actual_latency_change_percent": 3.4,
    "rollback_triggered": false
  }'
```

## Use It With GitHub

Send GitHub workflow or deployment events:

```bash
curl -X POST http://127.0.0.1:8000/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: workflow_run" \
  -d '{
    "action": "completed",
    "workflow_run": {
      "id": 987654,
      "name": "deploy.yml",
      "head_sha": "abc123def4567890"
    },
    "repository": {
      "name": "chaos-negotiator"
    }
  }'
```

## Use It On Azure

To get live telemetry instead of fallback mode:

1. deploy the app to Azure Container Apps
2. set `AZURE_MONITOR_WORKSPACE_ID`
3. give the Container App managed identity `Log Analytics Data Reader`

Without that permission, the dashboard will not read live Log Analytics data.
