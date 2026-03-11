# Judge Guide

## Core Requirement Proof

### 1. Working project

Chaos Negotiator is a working end-to-end project with:

- FastAPI backend
- React dashboard
- deployment evaluation API
- approval workflow
- GitHub webhook ingestion
- deployment outcome recording
- Azure deployment via Bicep and GitHub Actions

### 2. Required developer tools

This project uses the required developer tooling:

- public GitHub repository
- VS Code development workflow
- GitHub Actions CI/CD
- GitHub Copilot-assisted development workflow

### 3. Hero technologies

This project uses the required Microsoft technologies:

- Microsoft Agent Framework / Semantic Kernel orchestration path
- Azure MCP-style Azure integration through Azure telemetry and monitoring adapters
- Azure OpenAI for reasoning
- Azure Container Apps for hosting
- Azure Monitor / Log Analytics / Application Insights for telemetry

### 4. Deployable to Azure

Deployment assets are included:

- `infra/main.bicep`
- `.github/workflows/deploy.yml`
- `Dockerfile`

## What To Test

### Local verification

```bash
pip install -e ".[dev]"
pytest tests -q
python -m chaos_negotiator.server
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`

### API verification

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/hackathon/proof
curl http://127.0.0.1:8000/api/dashboard/risk
curl http://127.0.0.1:8000/api/dashboard/history
curl http://127.0.0.1:8000/api/dashboard/canary
```

### Deployment evaluation flow

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "judge-demo-001",
    "service_name": "checkout-service",
    "environment": "production",
    "version": "v1.2.0",
    "changes": [
      {
        "file_path": "src/api/checkout.py",
        "change_type": "modify",
        "lines_changed": 42,
        "risk_tags": ["api", "payments"],
        "description": "Change checkout response orchestration"
      }
    ]
  }'
```

Then verify:

```bash
curl http://127.0.0.1:8000/api/deployments/pending
curl http://127.0.0.1:8000/api/deployments/judge-demo-001
```

### Approval workflow

```bash
curl -X POST http://127.0.0.1:8000/api/deployments/judge-demo-001/approve \
  -H "Content-Type: application/json" \
  -d '{"reason":"Judge verification approval"}'
```

### GitHub webhook flow

```bash
curl -X POST http://127.0.0.1:8000/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: workflow_run" \
  -d '{
    "action": "completed",
    "workflow_run": {
      "id": 123456,
      "name": "deploy.yml",
      "head_sha": "abc123def456"
    },
    "repository": {
      "name": "chaos-negotiator"
    }
  }'
```

## Expected Judge Experience

- dashboard loads without a blank screen
- risk endpoint returns JSON
- canary endpoint returns rollout stages
- pending deployment list updates after evaluation
- approval endpoint changes deployment state
- telemetry shows either:
  - `live` when Azure Monitor access is configured
  - `degraded` when telemetry access is unavailable

`degraded` is an intentional fallback mode, not a broken server.

## Azure Notes

For live telemetry, the deployed Container App managed identity must have:

- `Log Analytics Data Reader`

Without that role, the dashboard remains functional but will show fallback telemetry status.
