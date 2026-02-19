# Chaos Negotiator - AI Dev Days Hackathon Submission

## 📋 Project Overview

**Chaos Negotiator** is an AI-powered DevOps agent that treats every deployment like a **contract negotiation** between developers and reliability goals. Instead of binary pass/fail gates, it:

1. **Auto-drafts deployment contracts** analyzing risk
2. **Predicts SLO impact** (latency, error rates)
3. **Enforces guardrails** (traffic ramp, error budgets)
4. **Validates rollback capability** (tested procedures, recovery time)
5. **Negotiates terms** with developers via AI reasoning

## 🎯 Problem Statement

Traditional DevOps asks: *"Did tests pass?"*

Chaos Negotiator asks: *"Can we safely fail and recover? Will we stay within SLOs?"*

Most deployment controls are binary. Reliability isn't. This solution treats deployment safety as an **enforceable contract** with intelligent negotiation.

## ✨ Solution Architecture

```
DEPLOYMENT REQUEST
        ↓
[ChaosNegotiatorAgent - Semantic Kernel + Azure OpenAI]
    ├─ RiskPredictor: Analyzes changes → Risk Score (0-100)
    ├─ RollbackValidator: Tests rollback capability
    ├─ ContractEngine: Drafts guardrails + validators
    └─ MCP Integration: Connects to Azure services
        ↓
[DEPLOYMENT CONTRACT]
    ├─ Guardrails (error<0.3%, p95<250ms, traffic ramp 10%)
    ├─ Validators (tests required, canary 5%, rollback tested)
    ├─ Rollback window (300s estimated)
    └─ Suggested fixes if risky
        ↓
[DEPLOYMENT WITH ENFORCEMENT]
    ├─ Metrics collection via Azure Monitor
    ├─ Real-time guardrail enforcement
    ├─ Automatic rollback if violated
    └─ Audit trail in Application Insights
```

## 🏗️ Technical Implementation

### Core Components

1. **Models** (`chaos_negotiator/models/`)
   - `DeploymentContext`: Captures PR changes, current metrics, SLOs
   - `DeploymentContract`: Auto-drafted contract with terms
   - `RiskAssessment`: Predicted impact on SLOs
   - `RollbackPlan`: Tested recovery procedures

2. **Agent** (`chaos_negotiator/agent/agent.py`)
   - **Azure OpenAI (GPT-4)** orchestrates decision-making
   - Analyzes deployment context
   - Coordinates predictor, validator, contract engine
   - Capable of interactive negotiation

3. **Risk Predictor** (`chaos_negotiator/predictors/risk_predictor.py`)
   - Pattern matching: caching changes, DB migrations, API breaks
   - Latency/error impact estimation
   - Confidence scoring
   - Affected user estimation

4. **Rollback Validator** (`chaos_negotiator/validators/rollback_validator.py`)
   - Auto-generates rollback steps (kubectl, cache flush, DB rollback)
   - Estimates recovery time
   - Identifies data loss risk
   - Validates tested procedures

5. **Contract Engine** (`chaos_negotiator/contracts/contract_engine.py`)
   - Builds risk-proportional guardrails
   - Specifies required validators (tests, canary, rollback plan)
   - Generates mitigation suggestions
   - Detailed reasoning for all decisions

6. **Azure MCP** (`chaos_negotiator/mcp/azure_mcp.py`)
   - Azure Monitor metrics collection
   - Deployment orchestration integration
   - Canary deployment triggering
   - Managed Identity authentication

### Infrastructure

**Bicep IaC** (`infra/`)
- **Container Apps** → Hosts Chaos Negotiator agent
- **Azure Container Registry** → Image storage
- **Application Insights** → Audit logging
- **Key Vault** → Secrets management (API keys)
- **Azure Monitor** → Metrics collection

### CI/CD

**GitHub Actions** (`.github/workflows/`)
- `test.yml`: Lint, type-check, unit tests (Python 3.10-3.12)
- `deploy.yml`: Build Docker image → Push → Deploy to Azure Container Apps

## 🤖 Key Features

### 1. Intelligent Risk Assessment
- Identifies 8+ risk factors (caching, schema, API, traffic, permissions, encryption, load balancing, storage)
- Scoring: 0-100 with confidence estimates
- Impacts prediction: latency increase %, error rate increase %

### 2. Dynamic Guardrails
- **Critical risk**: Error rate < 0.2%, canary at 5%
- **High risk**: Error rate < 0.3%, canary at 10%
- **Medium risk**: Error rate < 0.5%, canary at 25%
- **Low risk**: Error rate < 0.5%, no canary required

### 3. Rollback Automation
- Generates 4-5 validated rollback steps
- Supports: Kubernetes (rollout undo), cache flushing, DB migrations
- Estimates disruption window (0-30s typical)

### 4. Proof Requirements
- Tests: Always required
- Canary: Required for high/critical risk
- Rollback plan: Required for medium+ risk if rollback capable
- Feature flags: Required for database changes

### 5. Negotiable Terms
The agent handles deployment concerns via Azure OpenAI reasoning:
- Explains SLO risks
- Suggests concrete mitigations
- Enforces non-negotiable safety requirements

## 📊 Example Output

```
============================================================
DEPLOYMENT CONTRACT
============================================================

RISK ASSESSMENT:
  Level: HIGH
  Score: 72.5/100
  Confidence: 85%

GUARDRAILS (SLO PROTECTION):
  - error_rate: < 0.3 %
  - latency_p95: < 250 ms
  - latency_p99: < 1000 ms
  - traffic_ramp: < 10 %

VALIDATORS (PROOF REQUIRED):
  - test: REQUIRED
    Unit and integration tests must pass
  - canary: REQUIRED
    Canary deployment required (start at 5-10% traffic)
  - rollback_plan: REQUIRED
    Tested rollback procedure required
  - feature_flag: REQUIRED
    Database changes require feature flag

ROLLBACK CAPABILITY:
  Possible: true
  Window: 300s
  Steps: 4
  Data Loss Risk: low

SUGGESTED IMPROVEMENTS:
  → High risk deployment - consider breaking into smaller PRs
  → Add feature flags to make changes independently togglable
  → Implement automated rollback via CI/CD
```

## 🎯 Hackathon Submission Checklist

### ✅ Required Technologies

- **✅ Microsoft Agent Framework** → ChaosNegotiatorAgent implementation
- **✅ Azure MCP** → azure_mcp.py module for deployment/monitoring
- **✅ Azure OpenAI** → AI decision-making backbone (GPT-4)
- **✅ Azure Services** → Container Apps, Monitor, Key Vault, App Insights
- **✅ GitHub** → Public repo, Actions CI/CD, developed in VS Code
- **✅ Bicep IaC** → Complete infrastructure definition
- **✅ GitHub Copilot** → Code development with Copilot+

### ✅ Core Requirements

- **✅ AI-powered solution** → Uses Azure OpenAI + Semantic Kernel for intelligent negotiation
- **✅ Deployed to Azure** → Bicep infrastructure + Container Apps target
- **✅ GitHub repository** → Public repo with CI/CD
- **✅ Production-ready** → Tests, error handling, logging, security

### ✅ Innovation

- **Contract-based deployment safety** (not just pass/fail gates)
- **SLO-aware risk prediction** with confidence scoring
- **Automatic guardrail generation** proportional to risk
- **Smart rollback validation** with auto-generated steps
- **Agentic negotiation** using Semantic Kernel orchestration for developer interaction

## 📁 Project Structure

```
chaos-negotiator/
├── chaos_negotiator/          # Core package
│   ├── agent/                 # AI Agent orchestration
│   │   └── agent.py           # Main ChaosNegotiatorAgent (Semantic Kernel + Azure OpenAI)
│   ├── contracts/             # Contract generation engine
│   │   └── contract_engine.py
│   ├── models/                # Pydantic data models
│   │   ├── deployment.py      # DeploymentContext, DeploymentChange
│   │   ├── contract.py        # DeploymentContract, Guardrails
│   │   ├── risk.py            # RiskAssessment, RiskFactor
│   │   └── rollback.py        # RollbackPlan, RollbackStep
│   ├── predictors/            # Risk prediction
│   │   └── risk_predictor.py
│   ├── validators/            # Rollback validation
│   │   └── rollback_validator.py
│   ├── mcp/                   # Azure MCP integration
│   │   └── azure_mcp.py
│   └── main.py               # CLI entry point
├── infra/                     # Infrastructure as Code
│   ├── main.bicep            # Azure resources (Container Apps, KV, Monitor)
│   └── deployment.bicep      # Deployment wrapper
├── .github/workflows/         # CI/CD
│   ├── test.yml              # Test & lint pipeline
│   └── deploy.yml            # Build, push, deploy to Azure
├── tests/                     # Test suite
│   ├── conftest.py
│   └── test_agent.py
├── pyproject.toml            # Python project config
├── Dockerfile                # Multi-stage Docker build
├── .env.example              # Config template
├── deployment-example.json   # Example deployment context
└── README.md                 # Full documentation
```

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/varunvs7692/chaos-negotiator.git
cd chaos-negotiator

# 2. Install dependencies
pip install -e .

# 3. Set API keys
export AZURE_OPENAI_KEY=your_key_here
export AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/

# 4. Run with example
python -m chaos_negotiator.main

# 5. Run with custom deployment
python -m chaos_negotiator.main deployment-example.json

# 6. Run tests
pytest tests/ -v

# 7. Deploy to Azure
az deployment sub create \
  --template-file infra/main.bicep \
  --parameters location=eastus environment=prod
```

## 📦 Dependencies

**Core**:
- `azure-openai>=1.0.0` - GPT-4 AI backend
- `pydantic>=2.0.0` - Data validation
- `azure-identity>=1.14.0` - Managed Identity
- `azure-monitor-query>=1.4.0` - Metrics collection
- `aiohttp>=3.9.0` - Async HTTP

**Dev**:
- `pytest`, `pytest-asyncio` - Testing
- `black`, `ruff`, `mypy` - Code quality

## 🔐 Security Features

- ✅ **Managed Identity**: No hardcoded credentials
- ✅ **Key Vault**: Secure API key storage
- ✅ **RBAC**: Role-based deployment approvals
- ✅ **Audit Logging**: All decisions logged to App Insights
- ✅ **Non-root Container**: Docker runs as appuser

## 📈 Monitoring & Observability

All deployment decisions are logged to **Application Insights**:
- Contract generation events
- Risk assessments
- Guardrail negotiations
- Approval/rejection decisions
- SLO violations during deployment

## 🧪 Testing Strategy

- **Unit Tests**: Risk prediction, contract drafting, rollback validation
- **Integration Tests**: End-to-end deployment flow
- **Linting**: `ruff` for code quality
- **Type Checking**: `mypy` for type safety
- **Coverage**: Aim for >80% of core modules

## 💡 Innovation Highlights

1. **Contract as Code** - Deployment safety as machine-checkable contracts
2. **SLO-Aware** - Guardrails scale with actual reliability risk
3. **Negotiation Pattern** - AI reasoning about tradeoffs, not just rules
4. **Automatic Rollback** - Validated procedures, not guesswork
5. **Agentic** - LLM backend enables richer reasoning and dialogue

## 🎤 Hackathon Angle

This solution demonstrates:
- ✅ How to build **intelligent DevOps workflows** using AI agents
- ✅ **Safe, contract-based deployments** reducing incidents
- ✅ **Enterprise-grade Azure infrastructure** at scale
- ✅ **Real production challenges** (SLO enforcement, rollback validation)
- ✅ **Agentic reasoning** beyond simple rule engines

## 📞 Contact & Support

- **GitHub**: https://github.com/varunvs7692/chaos-negotiator
- **Issues**: Bug reports and feature requests
- **Documentation**: README.md + Inline code comments

---

**Built for the AI Dev Days Hackathon 🚀**

*Chaos Negotiator: Where developer intent meets reliability guarantees.*
