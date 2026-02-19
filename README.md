# Chaos Negotiator
> *AI Agent for Deployment Contracts* — Treat every deploy like a contract between developers and reliability goals.

[![Test & Lint](https://github.com/varunvs7692/chaos-negotiator/actions/workflows/test.yml/badge.svg)](https://github.com/varunvs7692/chaos-negotiator/actions)
[![Deploy to Azure](https://github.com/varunvs7692/chaos-negotiator/actions/workflows/deploy.yml/badge.svg)](https://github.com/varunvs7692/chaos-negotiator/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 The Problem

Traditional DevOps gates ask: **"Did tests pass?"**

Chaos Negotiator asks: **"Can we safely fail and recover? Will we stay within SLOs?"**

Most deployment controls are binary: pass or fail. But reliability isn't binary. Chaos Negotiator treats every deployment as a **negotiation** between developers' intent and reliability guarantees—then enforces the agreed terms.

## ✨ Key Features

### 1. **Auto-Draft Deployment Contracts**
Analyzes code changes, service dependencies, and SLOs. Generates contracts answering:
- **What could break?** (SLO impact prediction)
- **What are the guardrails?** (max error rate, latency budget, traffic ramp limits)
- **How fast can we undo?** (rollback window + tested steps)
- **What proof is required?** (tests, canary metrics, safe rollback)

### 2. **SLO-Aware Risk Prediction**
- Identifies high-risk patterns (caching, DB migrations, API changes)
- Predicts latency/error impact
- Confidence-scored assessments

### 3. **Enforced Guardrails**
- Error rate budgets
- Latency thresholds (p95, p99)
- Canary traffic limits
- Rollback windows

### 4. **Smart Rollback Plans**
- Auto-generates rollback steps
- Estimates time to recovery
- Identifies data loss risk
- Validates tested procedures

### 5. **Agentic Negotiation**
Intelligent dialogue handling deployments:
- Explains why guardrails matter
- Suggests mitigations for high-risk changes
- Enforces non-negotiable safety terms

## 🚀 Quick Start

```bash
# Clone & install
git clone https://github.com/varunvs7692/chaos-negotiator.git
cd chaos-negotiator
pip install -e .

# Run with example
python -m chaos_negotiator.main

# Run with custom deployment context
python -m chaos_negotiator.main deployment.json
```

### Example: Generate a Contract

```python
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentContext, DeploymentChange

context = DeploymentContext(
    deployment_id="deploy-001",
    service_name="user-service",
    environment="production",
    version="v2.1.0",
    changes=[
        DeploymentChange(
            file_path="src/cache/manager.py",
            change_type="modify",
            lines_changed=45,
            risk_tags=["caching"],
            description="Optimize cache TTL strategy"
        )
    ],
    current_error_rate_percent=0.05,
    current_p95_latency_ms=180.0,
    target_p95_latency_ms=250.0,
    rollback_capability=True
)

agent = ChaosNegotiatorAgent()
contract = agent.process_deployment(context)
print(contract.reasoning)  # Detailed contract
```

## 📊 Contract Output

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
  - canary: REQUIRED (start at 5-10% traffic)
  - rollback_plan: REQUIRED (tested procedure)

ROLLBACK CAPABILITY:
  Possible: true
  Window: 300s
  Steps: 4

SUGGESTED IMPROVEMENTS:
  → Break changes into smaller PRs
  → Add feature flags for independent toggling
```

## 🏗️ Architecture

```
chaos_negotiator/
├── agent/                 # AI Agent
├── contracts/            # Contract Engine
├── models/               # Pydantic schemas
├── predictors/           # Risk Prediction
├── validators/           # Rollback Validation
├── mcp/                  # Azure MCP Integration
└── main.py              # CLI Entry Point

infra/                     # Bicep IaC
tests/                     # Test Suite
.github/workflows/         # CI/CD (Test + Deploy)
```

## ☁️ Technologies

- **Microsoft Agent Framework** - AI agent orchestration
- **Azure OpenAI (GPT-4)** - LLM reasoning
- **Azure MCP** - Deployment/monitoring integration
- **Azure Container Apps** - Serverless hosting
- **Bicep** - Infrastructure as code
- **GitHub Actions** - CI/CD automation

## 🔐 Security

- Azure Managed Identity (Entra ID)
- Key Vault for secrets
- Application Insights for audit trails
- RBAC for deployment approvals

## 📈 Monitoring

All contract decisions logged to Application Insights:
- Risk assessments
- Guardrail negotiations
- Deployment approvals/rejections
- SLO violations

## 🧪 Testing

```bash
pytest tests/ -v --cov=chaos_negotiator
```

## 🤖 AI Dev Days Hackathon

**Category**: Agentic DevOps Workflows

**Innovation**: Treats deployment safety as a **negotiable contract** rather than binary gates, enabling developers to engage with reliability constraints intelligently.

**Core Technologies**:
- ✅ Microsoft Agent Framework
- ✅ Azure MCP Integration  
- ✅ Azure Services (Container Apps, Monitor, Key Vault)
- ✅ GitHub (Repo + Actions)
- ✅ Bicep IaC
- ✅ VS Code Development

## 📝 License

MIT - see [LICENSE](LICENSE)

## 🤝 Contributing

Issues & PRs welcome! Check [GitHub Issues](https://github.com/varunvs7692/chaos-negotiator/issues).

---

**Built for reliability. Negotiated with intent.** 🚀
