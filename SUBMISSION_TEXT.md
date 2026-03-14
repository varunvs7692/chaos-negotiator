# Submission Text

## Working project built with the required developer tools that meets the core requirements

Chaos Negotiator is a working end-to-end AI-powered project built with the required developer tools and aligned to the hackathon core requirements. It is developed in VS Code, maintained in a public GitHub repository, and built with GitHub Copilot-assisted workflows. The solution uses Microsoft Agent Framework concepts for agentic deployment reasoning, Azure MCP-style Azure integrations for telemetry-aware decision support, and Azure services for hosting, monitoring, identity, and infrastructure.

The project is deployable to Azure and runs on Azure Container Apps with Log Analytics, Application Insights, Managed Identity, Key Vault, and Bicep-based infrastructure. It includes a functional FastAPI backend, a React dashboard, GitHub Actions CI/CD, deployment evaluation APIs, GitHub webhook ingestion, approval workflows, and real-time or fallback telemetry visibility.

Chaos Negotiator is a working system that can:

- evaluate deployments using AI-assisted risk logic
- generate deployment contracts and canary strategies
- ingest GitHub deployment-style events
- store approval decisions and deployment outcomes
- display deployment and telemetry state in a usable dashboard
- run locally and be deployed to Azure for judging and testing

The running application also exposes `/api/hackathon/proof`, a machine-readable endpoint that summarizes the working features, required developer tools, hero technologies, and Azure deployment alignment for judge verification.

## Core requirement mapping

- AI-powered solution: deployment risk analysis, contract generation, and agentic decision support
- Hero technologies: Microsoft Agent Framework concepts, Azure MCP-style Azure integration, Azure OpenAI, Azure services
- Deploy to Azure: Azure Container Apps deployment with Bicep and GitHub Actions
- Use GitHub for development: public GitHub repository, GitHub Actions CI/CD, GitHub Copilot-assisted workflow

## Paste-Ready Innovation Studio Description

One-line pitch:
Chaos Negotiator is an agentic DevOps system that turns deployment approval from a binary CI gate into an AI-driven reliability contract with Azure-backed telemetry, guardrails, and rollback-aware rollout control.

Problem:
Modern deployment gates are mostly binary and test-only. Teams can pass tests but still cause user-visible reliability issues in production. This is especially risky for fast-moving services where rollback speed and SLO protection matter.

Who this is for:
DevOps engineers, SRE teams, and platform teams that need safer production rollouts with explainable risk decisions.

Why it matters:
Outages and regressions usually happen after "green" CI. Teams need deployment decisions that combine code-change context, SLO constraints, canary strategy, and rollback readiness.

Why this is valuable in production:
- reduces the chance of risky deployments reaching 100% traffic
- makes rollout decisions explainable to engineering and operations teams
- improves operational discipline with approvals, guardrails, and rollback readiness
- gives teams a practical path from CI success to production safety

Solution summary:
Chaos Negotiator is an AI-powered deployment contract agent. It evaluates each release, predicts reliability risk, drafts guardrails, recommends canary rollout stages, and enforces approval decisions before promotion.

AI value:
The agent uses Azure OpenAI-backed reasoning with contract logic to convert deployment context into actionable safety terms. Instead of generic pass/fail feedback, teams get structured guardrails, confidence-aware risk explanations, and mitigation guidance.

How it works:
- Ingest deployment context from API or GitHub webhook events
- Score risk and confidence from change patterns and service context
- Draft a deployment contract with validators and rollback constraints
- Generate canary strategy and monitor telemetry
- Trigger approval/rejection workflow and record outcomes for learning

Microsoft technologies used:
- Microsoft Agent Framework concepts via Semantic Kernel orchestration
- Azure MCP-style integration layer for telemetry and cloud interactions
- Azure OpenAI for reasoning
- Azure Container Apps for hosting
- Azure Monitor, Log Analytics, and Application Insights for observability
- Azure Key Vault and Managed Identity for secure access patterns
- GitHub Copilot and GitHub Actions for development and delivery workflow

Links:
- Live app: https://chaos-negotiator.happycoast-63bd2242.eastus.azurecontainerapps.io/
- Code repository: https://github.com/varunvs7692/chaos-negotiator
- Demo video: https://youtu.be/pRWTjbU5-Ug?si=ESbJjHA2Zle_-tH7
- Architecture diagram: see SUBMISSION_ARCHITECTURE.md in the repository

Participant information:
- Microsoft Learn username: varunvs7692
- Microsoft Learn profile: https://learn.microsoft.com/en-us/users/varunvs7692/

## Hackathon Category Fit

Primary category: Automate and Optimize Software Delivery - Agentic DevOps

Chaos Negotiator directly targets agentic DevOps outcomes by automating deployment risk evaluation, generating SLO guardrails, supporting approval workflows, and enabling safer progressive delivery decisions with rollback-aware enforcement.

Secondary category: Best Azure Integration

The solution is deeply integrated with Azure services for hosting, monitoring, telemetry, security, and cloud deployment readiness.

Enterprise positioning:
Chaos Negotiator is also a strong enterprise operations solution because it combines policy-like deployment controls, approval checkpoints, observability, secure cloud deployment patterns, and audit-friendly rollout decisions in one workflow.

## Maximum Win Priority

Prize targeting order:
1. Grand Prize - Automate and Optimize Software Delivery - Agentic DevOps
2. Best Azure Integration
3. Best Enterprise Solution

Judge-first positioning strategy:
- Lead with the deployment safety problem in the first sentence
- Demonstrate one end-to-end release decision flow (evaluate -> guardrails -> approval -> telemetry)
- Emphasize production reliability impact over generic AI capability
- Keep all claims evidence-backed with live endpoint behavior, CI, and Azure deployment artifacts

What not to over-claim:
- Do not present this as a multi-agent category-first project
- Do not dilute the story with unrelated AI features outside release safety and reliability

## Judging Criteria Alignment Summary

1. Technological Implementation
- Structured Python backend and React dashboard with reproducible setup
- Test coverage and CI workflow are included
- Azure deployment assets are included (Bicep + pipeline)

2. Agentic Design and Innovation
- Agentic contract model replaces binary deployment gates
- Risk reasoning, guardrail drafting, canary planning, and approval logic are integrated in one workflow

3. Real-World Impact and Applicability
- Addresses production reliability and incident prevention in real deployment pipelines
- Designed for practical DevOps and SRE adoption

4. User Experience and Presentation
- Interactive dashboard plus straightforward API verification flow
- 2-minute demo script available in JUDGE_GUIDE.md

5. Adherence to Hackathon Category
- Explicitly built as an Agentic DevOps workflow using Microsoft AI platform technologies
