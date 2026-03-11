# Azure Deployment Plan

> **Status:** Executing

Generated: 2026-03-11

---

## 1. Project Overview

**Goal:** Convert Chaos Negotiator from demo/example telemetry to a real-time deployment risk dashboard backed by live Azure monitoring and deployment data.

**Path:** Add Components

---

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | Production |
| Scale | Medium |
| Budget | Balanced |
| **Subscription** | `f60b9eb5-c74a-461f-ac97-2d5b60f54ce0` |
| **Location** | `eastus` |

### Working assumptions

- Existing app remains hosted on Azure Container Apps.
- Real-time dashboard data should come from Azure Monitor / Application Insights instead of example contexts.
- Dashboard should continue to work in a degraded mode if Azure telemetry is temporarily unavailable.
- Existing FastAPI + React architecture should be preserved rather than replaced.

---

## 3. Components Detected

| Component | Type | Technology | Path |
|-----------|------|------------|------|
| Backend API | API | Python, FastAPI | `chaos_negotiator/server.py` |
| Risk Engine | Domain service | Python | `chaos_negotiator/agent/`, `chaos_negotiator/predictors/` |
| Azure telemetry client | Integration | Azure Monitor Query SDK | `chaos_negotiator/mcp/azure_mcp.py` |
| Dashboard UI | Frontend | React | `frontend/` |
| Static production UI | Frontend bundle | HTML/CSS/JS served by FastAPI | `chaos_negotiator/static/` |
| Infrastructure | IaC | Bicep | `infra/` |
| Deployment pipeline | CI/CD | GitHub Actions | `.github/workflows/deploy.yml` |

---

## 4. Recipe Selection

**Selected:** Bicep

**Rationale:** The project already uses Bicep and GitHub Actions with Azure Container Apps. Extending the current infrastructure and application code is lower risk than introducing AZD or Terraform now.

---

## 5. Architecture

**Stack:** Containers

### Service Mapping

| Component | Azure Service | SKU |
|-----------|---------------|-----|
| FastAPI backend + bundled dashboard | Azure Container Apps | Existing Container Apps environment |
| Live metrics / request telemetry | Application Insights + Log Analytics | Existing / standard workspace-backed setup |
| Secrets and config | Key Vault + Container App env vars | Existing |
| Container image storage | Azure Container Registry | Existing |

### Supporting Services

| Service | Purpose |
|---------|---------|
| Log Analytics | Query live request/error/latency telemetry |
| Application Insights | Source of request and deployment event data |
| Key Vault | Secrets management |
| Managed Identity | Access Azure Monitor without embedded credentials |

### Planned real-time data flow

1. Backend loads Azure resource identifiers and monitoring configuration from environment.
2. `AzureMCPClient` queries Azure Monitor / Application Insights for live request metrics.
3. Backend dashboard endpoints expose live risk, canary, and deployment history derived from telemetry plus persisted deployment results.
4. WebSocket stream pushes refreshed live risk snapshots to the dashboard.
5. If Azure telemetry is unavailable, backend returns an explicit degraded/fallback state instead of silently pretending everything is live.

---

## 6. Execution Checklist

### Phase 1: Planning
- [x] Analyze workspace
- [x] Gather requirements
- [x] Confirm subscription and location with user
- [x] Scan codebase
- [x] Select recipe
- [x] Plan architecture
- [x] **User approved this plan**

### Phase 2: Execution
- [x] Research components (load references, invoke skills)
- [x] Generate infrastructure files
- [x] Generate application configuration
- [ ] Generate Dockerfiles (if containerized)
- [ ] Update plan status to "Ready for Validation"

### Phase 3: Validation
- [ ] Invoke azure-validate skill
- [ ] All validation checks pass
- [ ] Update plan status to "Validated"
- [ ] Record validation proof below

### Phase 4: Deployment
- [ ] Invoke azure-deploy skill
- [ ] Deployment successful
- [ ] Update plan status to "Deployed"

---

## 7. Validation Proof

> **REQUIRED**: The azure-validate skill MUST populate this section before setting status to `Validated`. If this section is empty and status is `Validated`, the validation was bypassed improperly.

| Check | Command Run | Result | Timestamp |
|-------|-------------|--------|-----------|
| Pending | Pending | Pending | Pending |

**Validated by:** Pending
**Validation timestamp:** Pending

---

## 8. Files to Generate

| File | Purpose | Status |
|------|---------|--------|
| `.azure/plan.md` | This plan | Complete |
| `chaos_negotiator/mcp/azure_mcp.py` | Real Azure telemetry and deployment queries | Complete |
| `chaos_negotiator/server.py` | Live dashboard API wiring and fallback semantics | Complete |
| `frontend/src/pages/Dashboard.jsx` | Real-time dashboard UX for live/degraded states | Complete |
| `infra/main.bicep` | Monitoring/config additions if required | Complete |
| `.github/workflows/deploy.yml` | Deployment validation for live telemetry config | Pending |

---

## 9. Next Steps

> Current: Awaiting Azure validation and deployment

1. Confirm subscription, Azure region, and whether this should target production-grade live telemetry.
2. Implement backend live-data ingestion from Azure Monitor/Application Insights and remove demo-only dashboard dependencies.
3. Validate and deploy after code and infrastructure updates.
