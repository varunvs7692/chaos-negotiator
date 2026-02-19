# Chaos Negotiator - Architecture & Design

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
│  - Pull Requests with deployment changes                     │
│  - CI/CD Pipeline (GitHub Actions)                          │
│  - VS Code Development (with Copilot)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          Chaos Negotiator Agent (Container Apps)             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ChaosNegotiatorAgent (Orchestrator)                   │ │
│  │  - Powered by Azure OpenAI GPT-4                       │ │
│  │  - Accepts DeploymentContext                          │ │
│  │  - Returns DeploymentContract                         │ │
│  └────────────────────┬─────────────────────────────────┘ │
│                       │                                     │
│       ┌───────────────┼───────────────┬──────────────┐    │
│       ▼               ▼               ▼              ▼    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────┐ │
│  │    Risk    │  │  Rollback  │  │ Contract   │  │ Azure│ │
│  │ Predictor  │  │ Validator  │  │  Engine    │  │ MCP  │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────┘ │
│        │               │               │              │    │
│  - Pattern matching    │  - Auto       │  - Guard     │    │
│  - Impact prediction   │    generate   │    rail      │    │
│  - Confidence scoring  │    steps      │    building  │    │
│                        │  - Time est.  │  - Validator │    │
│                        │  - Data risk  │    spec      │    │
│                        │               │  - Mitig.    │    │
│                        │               │    suggest   │    │
│                        │               │              │    │
│                        │  Connects to: │              │    │
│                        │  - K8s API    │              │    │
│                        │  - DB APIs    │              │    │
│                        │  - Cache      │              │    │
│                        │    APIs       │              │    │
│                        └───────────────┘              │    │
│                                                       │    │
│              Connects to Azure Monitor,               │    │
│         Application Insights, Key Vault               │    │
│                    via MCP                            │    │
└─────────────────────┬─────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    ┌────────┐  ┌────────────┐  ┌─────────┐
    │ Azure  │  │ Application│  │   Key   │
    │Monitor │  │ Insights   │  │  Vault  │
    │        │  │ (Logging)  │  │ (Secrets)
    └────────┘  └────────────┘  └─────────┘
        │
        ▼
   Real-time metrics:
   - Error rates
   - Latency (p95, p99)
   - Traffic (QPS)
   - Deployment status
```

## 📊 Data Flow

### 1. Deployment Request to Contract

```
DeploymentContext (input)
├─ deployment_id: str
├─ service_name: str
├─ changes: List[DeploymentChange]
│  ├─ file_path: str
│  ├─ change_type: str (add/modify/delete)
│  ├─ description: str
│  └─ risk_tags: List[str]
├─ current_error_rate_percent: float
├─ current_p95_latency_ms: float
├─ target_error_rate_percent: float
├─ target_p95_latency_ms: float
├─ current_qps: float
├─ rollback_capability: bool
└─ dependencies: List[ServiceDependency]
         │
         ▼
[RiskPredictor.predict()]
         │
         ▼
RiskAssessment
├─ risk_level: str (critical/high/medium/low)
├─ risk_score: float (0-100)
├─ identified_factors: List[RiskFactor]
├─ predicted_error_rate_increase_percent: float
├─ predicted_p95_latency_increase_percent: float
└─ reasoning: str
         ▼
         │
         ▼ (parallel with RiskAssessment)
[RollbackValidator.validate_and_create()]
         │
         ▼
RollbackPlan
├─ rollback_possible: bool
├─ steps: List[RollbackStep]
├─ total_estimated_time_seconds: int
├─ data_loss_risk: str
└─ reasoning: str
         │
         ▼
[ContractEngine.draft_contract()]
         │
         ▼
DeploymentContract (output)
├─ contract_id: str
├─ predicted_risk_level: str
├─ risk_score: float
├─ guardrails: List[GuardrailRequirement]
│  ├─ guardrail_type: GuardrailType
│  ├─ max_value: float
│  ├─ unit: str
│  └─ enforcement_window_seconds: int
├─ validators: List[ValidatorRequirement]
│  ├─ validator_type: str
│  ├─ required: bool
│  └─ description: str
├─ rollback_window_seconds: int
├─ suggested_fixes: List[str]
├─ status: str (draft)
└─ reasoning: str
```

## 🧠 Risk Assessment Logic

```
DeploymentContext (with changes)
    │
    ▼
[Pattern Matching]
    ├─ Caching changes? → +5% latency, risk score +15
    ├─ Database schema? → +15% latency, +2% errors, risk score +15
    ├─ API contract? → +8% latency, +1.5% errors, risk score +15
    ├─ Traffic pattern? → +20% latency, risk score +15
    └─ ... (8+ patterns)
    │
    ├─ Base score = (change count × 2) + (pattern count × 15) + (size factor)
    │
    ▼
[Score Interpretation]
    ├─ 70+: CRITICAL (dark red)
    ├─ 50-70: HIGH (red)
    ├─ 30-50: MEDIUM (yellow)
    └─ <30: LOW (green)
    │
    ├─ User impact = current_qps × (affected_percentage)
    ├─ Confidence = 50 + (pattern_count × 10), capped at 95%
    │
    ▼
RiskAssessment
```

## 🛡️ Guardrail Generation

```
Risk Level → Guardrail Thresholds

CRITICAL:
├─ Error rate < 0.2%
├─ P95 latency < target × 1.2
├─ P99 latency < target × 1.25
├─ Traffic ramp < 5%
└─ Canary required

HIGH:
├─ Error rate < 0.3%
├─ P95 latency < target × 1.3
├─ P99 latency < target × 1.25
├─ Traffic ramp < 10%
└─ Canary required

MEDIUM:
├─ Error rate < 0.5%
├─ P95 latency < target × 1.4
├─ P99 latency < target × 1.3
└─ Traffic ramp < 25% (optional)

LOW:
├─ Error rate < 0.5%
├─ P95 latency < target × 1.5
└─ P99 latency < target × 1.4
```

## ✅ Validator Requirements

```
Risk Level → Required Validators

ALWAYS:
└─ Tests (unit + integration)

HIGH/CRITICAL:
├─ Canary deployment (5-10% traffic)
├─ Rollback plan (if available)
└─ Manual approval (optional)

MEDIUM:
├─ Canary deployment (10-25% traffic)
└─ Rollback plan (if available)

DATABASE CHANGES:
├─ Feature flag (always)
└─ Migration rollback script

PERMISSION CHANGES:
├─ Security review
└─ RBAC audit
```

## 📦 Component Interactions

### ChaosNegotiatorAgent

```python
ChaosNegotiatorAgent
├─ __init__(api_key)
│  ├─ Creates Azure OpenAI client
│  ├─ Initializes RiskPredictor
│  ├─ Initializes RollbackValidator
│  └─ Initializes ContractEngine
│
├─ process_deployment(context) → DeploymentContract
│  ├─ Calls risk_predictor.predict()
│  ├─ Calls rollback_validator.validate_and_create()
│  ├─ Calls contract_engine.draft_contract()
│  └─ Returns complete contract
│
├─ negotiate_with_user(context) → DeploymentContract
│  ├─ Gets initial contract via process_deployment()
│  ├─ Sets up conversation with Claude
│  ├─ Interactive loop for negotiation
│  └─ Returns approved/rejected contract
│
└─ explain_contract(contract) → str
   └─ Returns contract.reasoning
```

### RiskPredictor

```python
RiskPredictor
├─ predict(context) → RiskAssessment
│  ├─ Analyzes each change description
│  ├─ Pattern matches against risk_patterns
│  ├─ Accumulates risk factors
│  ├─ Calculates impact percentages
│  ├─ Computes overall risk score
│  ├─ Determines risk_level
│  ├─ Estimates user impact
│  └─ Generates reasoning
│
└─ risk_patterns dict
   ├─ caching: +5% latency
   ├─ database: +15% latency, +2% errors
   ├─ api: +8% latency, +1.5% errors
   ├─ traffic: +20% latency
   └─ ... (4 more patterns)
```

### RollbackValidator

```python
RollbackValidator
├─ validate_and_create(context, risk) → RollbackPlan
│  ├─ Checks rollback_capability
│  ├─ Skips plan if low risk
│  ├─ Generates 4-5 rollback steps
│  ├─ Calculates total time
│  ├─ Assesses data loss risk
│  ├─ Estimates disruption window
│  └─ Generates reasoning
│
└─ _generate_steps(context) → List[RollbackStep]
   ├─ Kubernetes rollout undo
   ├─ Pod health verification
   ├─ Cache clear
   └─ DB migration rollback (if needed)
```

### ContractEngine

```python
ContractEngine
├─ draft_contract(context, risk, rollback) → DeploymentContract
│  ├─ Creates contract shell
│  ├─ Calls _build_guardrails()
│  ├─ Calls _build_validators()
│  ├─ Calls _suggest_fixes()
│  ├─ Calls _generate_reasoning()
│  └─ Returns complete contract
│
├─ _build_guardrails() → List[GuardrailRequirement]
│  ├─ Risk-proportional error rate thresholds
│  ├─ Latency budgets (p95, p99)
│  └─ Traffic ramp limits (for high risk)
│
├─ _build_validators() → List[ValidatorRequirement]
│  ├─ Always: tests
│  ├─ High risk: canary + rollback_plan
│  ├─ DB changes: feature_flag
│  └─ Permission changes: security_review
│
└─ _suggest_fixes() → List[str]
   ├─ "Break into smaller PRs"
   ├─ "Add feature flags"
   ├─ "Implement rollback capability"
   └─ "Add security scan"
```

## 🔄 State Transitions

```
DeploymentContract Status Flow:

draft ──(approves)──> approved ──(deploys)──> deployed
  ▲                       │                       │
  │                       │                       ▼
  │────(violates SLO)─────┴─(automatic rollback)─► rolled_back
  │
  └────(rejects)──────> rejected
```

## 🔌 Azure MCP Integration

```
AzureMCPClient
├─ get_current_metrics(resource_id, metrics)
│  └─ Queries Azure Monitor
│
├─ get_deployment_history(service_name)
│  └─ Retrieves recent deployments
│
├─ trigger_canary_deployment(service, version, traffic%)
│  └─ Initiates canary via orchestration
│
└─ monitor_deployment(deployment_id, guardrails)
   └─ Real-time enforcement

ManagedIdentityHandler
├─ get_auth_token(scope)
│  └─ Azure Entra ID authentication
```

## 🔐 Security Model

```
REQUEST FLOW:
1. Deployment request arrives (from GitHub webhook)
2. Managed Identity authenticates to Azure
3. Secrets retrieved from Key Vault
4. Azure OpenAI API key and endpoint loaded from vault
5. Contract generated
6. Decision logged to App Insights
7. Metrics queried from Monitor
8. Deployment gated by guardrails

NO HARDCODED CREDENTIALS
```

---

## 📚 Additional Resources

- [Pydantic Models](https://docs.pydantic.dev/): Type-safe data validation
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/): GPT-4 integration
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/): Serverless hosting
- [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/): Infrastructure as Code
