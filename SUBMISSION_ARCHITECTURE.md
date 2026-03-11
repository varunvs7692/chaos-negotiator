# Submission Architecture Diagram

```mermaid
flowchart LR
  Dev[Developer in VS Code<br/>GitHub Copilot-assisted workflow]
  GitHub[Public GitHub Repository<br/>GitHub Actions CI/CD]
  Webhook[GitHub deployment/workflow events]

  Frontend[React Dashboard]
  API[FastAPI API on Azure Container Apps]

  Agent[Chaos Negotiator Agent]
  Risk[Risk Assessor]
  Contract[Contract Drafter]
  Canary[Canary Planner]
  Approvals[Approval Workflow]
  Learning[Outcome Learning Store]

  AzureOpenAI[Azure OpenAI]
  AzureMCP[Azure MCP-style Azure Integration Layer]
  AppInsights[Application Insights]
  LogAnalytics[Log Analytics]
  KeyVault[Key Vault]
  Identity[Managed Identity]

  Dev --> GitHub
  GitHub --> API
  Webhook --> API
  Frontend --> API
  API --> Agent

  Agent --> Risk
  Agent --> Contract
  Agent --> Canary
  Agent --> Approvals
  Agent --> Learning

  Risk --> AzureOpenAI
  API --> AzureMCP
  AzureMCP --> AppInsights
  AzureMCP --> LogAnalytics
  API --> KeyVault
  API --> Identity
```

## Why This Matches The Hackathon

- `Microsoft Agent Framework`: agent orchestration and deployment negotiation flow
- `Azure MCP`: Azure telemetry and cloud integration layer
- `Azure services`: Container Apps, Application Insights, Log Analytics, Key Vault, Managed Identity
- `GitHub + Copilot`: public repo, CI/CD, and Copilot-assisted development workflow
- `Agentic DevOps`: evaluates deployments, applies guardrails, and supports approval and rollout decisions
