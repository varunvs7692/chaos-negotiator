# Development Guide - Chaos Negotiator

## 🛠️ Development Setup

### Prerequisites

- Python 3.10+
- Git
- Azure CLI (optional, for cloud deployment)
- Azure OpenAI API key and endpoint

### 1. Clone & Environment Setup

```bash
# Clone repository
git clone https://github.com/varunvs7692/chaos-negotiator.git
cd chaos-negotiator

# Create virtual environment
python -m venv venv

# Activate
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
# AZURE_OPENAI_KEY=xxx
# AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
# AZURE_SUBSCRIPTION_ID=xxx
```

### 3. Verify Installation

```python
python -c "import chaos_negotiator; print('✅ Installation successful')"
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=chaos_negotiator --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Run Specific Test

```bash
pytest tests/test_agent.py::test_risk_prediction -v
```

### Run Tests in Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch
ptw
```

## 🔍 Code Quality

### Linting

```bash
# Check code with ruff
ruff check chaos_negotiator tests

# Fix fixable issues
ruff check --fix chaos_negotiator tests
```

### Formatting

```bash
# Format with black
black chaos_negotiator tests

# Check without changing
black --check chaos_negotiator tests
```

### Type Checking

```bash
# Check types with mypy
mypy chaos_negotiator
```

### All Quality Checks

```bash
# Run all in sequence
black chaos_negotiator tests && \
ruff check chaos_negotiator tests && \
mypy chaos_negotiator && \
pytest tests/ -v --cov=chaos_negotiator
```

## 🚀 Running the Agent

### With Example Deployment

```bash
python -m chaos_negotiator.main
```

This uses a built-in example deployment context.

### With Custom Deployment

```bash
python -m chaos_negotiator.main deployment-example.json
```

See `deployment-example.json` for the JSON schema.

### Interactive Mode

```python
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentContext, DeploymentChange

# Create context
context = DeploymentContext(
    deployment_id="test-001",
    service_name="my-service",
    environment="production",
    version="v1.0.0",
    # ... add fields
)

# Run agent
agent = ChaosNegotiatorAgent()
contract = agent.process_deployment(context)

# Print contract
print(contract.reasoning)
```

## 📝 Project Structure Deep Dive

### Models (`chaos_negotiator/models/`)

**deployment.py**
- `DeploymentContext` - Full deployment context (changes, metrics, SLOs)
- `DeploymentChange` - Individual code change
- `ServiceDependency` - External service dependency

**contract.py**
- `DeploymentContract` - The negotiated contract
- `GuardrailRequirement` - A single guardrail (error rate, latency, etc.)
- `ValidatorRequirement` - Validation requirement (test, canary, rollback, etc.)

**risk.py**
- `RiskAssessment` - Risk analysis results
- `RiskFactor` - Enum of known risk factors

**rollback.py**
- `RollbackPlan` - Complete rollback strategy
- `RollbackStep` - Individual rollback step

### Predictors (`chaos_negotiator/predictors/`)

**risk_predictor.py**
- Pattern matching for risk factors
- Latency/error impact calculation
- Confidence scoring
- User impact estimation

Methods:
- `predict(context: DeploymentContext) -> RiskAssessment`

### Validators (`chaos_negotiator/validators/`)

**rollback_validator.py**
- Rollback step generation
- Time estimation
- Data loss risk assessment
- Service disruption analysis

Methods:
- `validate_and_create(context, risk) -> RollbackPlan`

### Contracts (`chaos_negotiator/contracts/`)

**contract_engine.py**
- Risk-proportional guardrail generation
- Validator requirement specification
- Fix suggestion generation
- Detailed reasoning

Methods:
- `draft_contract(context, risk, rollback) -> DeploymentContract`

### Agent (`chaos_negotiator/agent/`)

**agent.py**
- Orchestrates all components
- Anthropic Claude integration
- Interactive negotiation capability

Key methods:
- `process_deployment(context) -> DeploymentContract`
- `negotiate_with_user(context) -> DeploymentContract`
- `explain_contract(contract) -> str`

### MCP (`chaos_negotiator/mcp/`)

**azure_mcp.py**
- Azure Monitor client for metrics
- Managed Identity authentication
- Deployment orchestration hooks

Classes:
- `AzureMCPClient` - Main Azure integration
- `ManagedIdentityHandler` - Auth handling

## 🐳 Docker Development

### Build Local Docker Image

```bash
docker build -t chaos-negotiator:dev .
```

### Run Container Locally

```bash
docker run -e ANTHROPIC_API_KEY=xxx chaos-negotiator:dev
```

### Build with Buildkit

```bash
DOCKER_BUILDKIT=1 docker build -t chaos-negotiator:dev .
```

## ☁️ Azure Deployment

### Prerequisites

```bash
# Install Azure CLI
# https://learn.microsoft.com/en-us/cli/azure/install-azure-cli

# Login to Azure
az login

# Set subscription
az account set --subscription <SUBSCRIPTION_ID>
```

### Deploy Infrastructure

```bash
# Create resource group
az group create \
  --name chaos-negotiator-rg \
  --location eastus

# Deploy Bicep template
az deployment group create \
  --resource-group chaos-negotiator-rg \
  --template-file infra/main.bicep \
  --parameters location=eastus environment=prod appName=chaos-negotiator
```

### Deploy to Container Apps

```bash
# Build and push image
docker build -t chaos-negotiator:latest .
docker tag chaos-negotiator:latest <REGISTRY>.azurecr.io/chaos-negotiator:latest
docker push <REGISTRY>.azurecr.io/chaos-negotiator:latest

# Update container app
az containerapp update \
  --name chaos-negotiator \
  --resource-group chaos-negotiator-rg \
  --image <REGISTRY>.azurecr.io/chaos-negotiator:latest
```

## 🔄 GitHub Actions CI/CD

### Test Workflow (`.github/workflows/test.yml`)

Triggers on:
- Push to main/develop
- Pull requests to main/develop

Runs:
- Linting (ruff)
- Formatting check (black)
- Type checking (mypy)
- Unit tests on Python 3.10, 3.11, 3.12
- Coverage reporting

### Deploy Workflow (`.github/workflows/deploy.yml`)

Triggers on:
- Push to main
- Manual trigger

Runs:
- Tests
- Docker build
- Push to Azure Container Registry
- Deploy to Azure Container Apps via Bicep

## 🎯 Common Development Tasks

### Add a New Risk Factor

1. Add to `RiskFactor` enum in `models/risk.py`
2. Add pattern to `RiskPredictor.risk_patterns` in `predictors/risk_predictor.py`
3. Update risk calculation logic
4. Add tests in `tests/test_agent.py`

Example:
```python
# In models/risk.py
class RiskFactor(str, Enum):
    MY_NEW_FACTOR = "my_new_factor"

# In predictors/risk_predictor.py
"my_pattern": {
    "keywords": ["keyword1", "keyword2"],
    "risk_factor": RiskFactor.MY_NEW_FACTOR,
    "latency_increase": 10.0,
}
```

### Add a New Guardrail Type

1. Add to `GuardrailType` enum in `models/contract.py`
2. Update `ContractEngine._build_guardrails()` to generate it
3. Add tests

### Extend the Agent

1. Add new methods to `ChaosNegotiatorAgent`
2. Update `process_deployment()` or add new entry point
3. Test interactions

## 🐛 Troubleshooting

### Import Errors

```bash
# Reinstall package
pip install -e . --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

### Anthropic API Issues

```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Check API status
curl https://api.anthropic.com/health
```

### Azure Errors

```bash
# Login to Azure
az login

# Check subscription
az account show

# Check resource group
az group show --name chaos-negotiator-rg
```

### Test Failures

```bash
# Run with verbose output
pytest tests/ -vv -s

# Run specific test with full traceback
pytest tests/test_agent.py::test_name -vv --tb=long
```

## 📚 Code Style Guide

### Naming Conventions
- Classes: `PascalCase` (e.g., `RiskPredictor`)
- Functions/variables: `snake_case` (e.g., `predict_risk`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RISK_SCORE`)
- Private members: Leading `_` (e.g., `_init_patterns`)

### Type Hints

Always use type hints:
```python
def process(context: DeploymentContext) -> DeploymentContract:
    """Process deployment and return contract."""
    # ...
```

### Docstrings

Use Google-style docstrings:
```python
def predict(self, context: DeploymentContext) -> RiskAssessment:
    """Predict risk for a deployment.
    
    Args:
        context: Deployment context with changes and metrics.
        
    Returns:
        RiskAssessment with predicted impact and factors.
    """
```

### Error Handling

```python
import logging

logger = logging.getLogger(__name__)

try:
    # code
except SpecificException as e:
    logger.error(f"Failed: {e}", exc_info=True)
    raise
```

## 🚀 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test: `pytest tests/ -v`
4. Run quality checks: `black . && ruff check . && mypy chaos_negotiator`
5. Commit: `git commit -m "feat: description"`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

## 📖 Resources

- [Anthropic API Docs](https://docs.anthropic.com/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Pytest Docs](https://docs.pytest.org/)

---

**Happy coding! 🚀**
