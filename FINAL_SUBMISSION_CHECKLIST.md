# Final Submission Checklist

Use this before submitting the hackathon entry.

## Core Requirement Checklist

- [x] Public GitHub repository is accessible
- [x] Project is developed with VS Code / Visual Studio workflow
- [x] GitHub Copilot-assisted development is mentioned in submission
- [x] Azure deployment is working or deployable from included assets
- [x] At least one hero technology is clearly demonstrated
- [x] Project description is ready (problem, target users, and why it matters)
- [x] AI value is clearly explained (what AI does and why it improves outcomes)
- [x] Demo video link is ready
- [x] Architecture diagram is ready
- [x] Participant information is ready (your name, role, and Microsoft Learn username)

## Required Artifact Checklist

- [x] `README.md` is present and accurate
- [x] `USER_GUIDE.md` is present
- [x] `JUDGE_GUIDE.md` is present
- [x] `SUBMISSION_ARCHITECTURE.md` is present
- [x] Public app URL is included
- [x] GitHub repo link is included
- [ ] Demo video is <= 2 minutes
- [x] Demo video is uploaded to YouTube or Vimeo with a public or accessible link
- [x] Demo video link is included in submission form / project description
- [ ] Screenshots and architecture visuals are uploaded in the Images/Video section
- [x] Architecture diagram explicitly shows Foundry/Agent Framework/Azure MCP/GitHub Copilot/Azure services usage
- [x] Your Microsoft Learn username is included

## Technical Readiness Checklist

- [x] CI is green
- [x] `pytest tests -q` passes locally
- [x] Public dashboard loads
- [x] `/health` returns `200`
- [x] `/docs` loads
- [x] `/api/dashboard/risk` returns JSON
- [x] `/api/dashboard/history` returns JSON
- [x] `/api/dashboard/canary` returns JSON
- [x] Deployment evaluation endpoint works
- [x] Approval workflow works
- [x] GitHub webhook ingestion works

## Azure Readiness Checklist

- [x] Azure Container App is deployed
- [ ] Log Analytics workspace is configured
- [ ] Managed identity exists on the Container App
- [ ] Managed identity has `Log Analytics Data Reader` if live telemetry is required
- [ ] `AZURE_MONITOR_WORKSPACE_ID` is set
- [ ] `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` are set if live model reasoning is required

## Demo Checklist

- [x] Show the problem in one sentence
- [x] Show deployment evaluation
- [x] Show risk score and canary plan
- [x] Show approval or rejection
- [x] Show telemetry state
- [x] Mention Microsoft Agent Framework, Azure MCP-style integration, Azure services, GitHub Copilot
- [ ] Keep video under 2 minutes

## Judging Criteria Optimization (20% Each)

1. Technological Implementation
- [x] Code quality proof included (tests, CI, maintainable structure)
- [x] Hero technology usage is explicit and verifiable in docs and architecture
- [x] Setup and run instructions are clear for judges

2. Agentic Design and Innovation
- [x] Agentic reasoning flow is clearly explained (risk -> contract -> guardrails -> approval)
- [x] Novelty is stated in one sentence (contract-based deployment safety vs binary gates)
- [x] If multi-agent or orchestration is used, interaction flow is shown in architecture

3. Real-World Impact and Applicability
- [x] Problem significance is stated clearly for SRE/DevOps teams
- [x] Production readiness is demonstrated (Azure deployability, telemetry, rollback handling)
- [ ] Business/end-user impact is quantified or exemplified

4. User Experience and Presentation
- [x] Demo is clear, paced, and understandable in under 2 minutes
- [x] Dashboard/API flow is intuitive and visually understandable
- [x] Narrative connects problem -> solution -> value -> proof

5. Adherence to Hackathon Category
- [x] Submission explicitly names target category
- [x] Description language matches category requirements
- [x] Evidence for category fit appears in both submission text and demo narration

## Category Positioning

- Primary category target: Grand Prize - Automate and Optimize Software Delivery - Agentic DevOps
- Secondary category target: Best Azure Integration

## Maximum Win Priority Execution

- [x] Primary narrative is Agentic DevOps, not generic AI assistant functionality
- [x] Secondary narrative highlights Azure integration depth (Container Apps, Monitor, App Insights, Key Vault, Managed Identity)
- [x] Demo sequence is aligned to judging criteria and category fit
- [ ] Final submission form category selection prioritizes Agentic DevOps first
- [ ] Final submission text pasted from `SUBMISSION_TEXT.md` with win-priority language

## Final Go / No-Go

- [ ] Project is created and submitted on Innovation Studio Hackathon platform
- [ ] A judge can understand the product in under 30 seconds
- [ ] A judge can verify the project in under 5 minutes
- [ ] The deployed app does not show a broken or blank screen
- [ ] Any fallback mode is documented and intentional
- [ ] Submission is finalized before the hackathon deadline

## Dry-Run Status (2026-03-13)

Verified now:
- [x] Local tests pass (`pytest -q` -> 42 passed)
- [x] Core documentation exists (`README.md`, `USER_GUIDE.md`, `JUDGE_GUIDE.md`, `SUBMISSION_ARCHITECTURE.md`, `SUBMISSION_TEXT.md`)
- [x] Public app URL is documented
- [x] GitHub repository URL is documented
- [x] Architecture mapping to Foundry/Agent Framework/Azure MCP/Copilot/Azure services is documented
- [x] Live endpoint verification passed (`scripts/verify_deployment.py`)
- [x] Approval workflow verification passed (`/api/deployments/{id}/approve` -> 200)
- [x] GitHub webhook ingestion verification passed (`/api/webhooks/github` -> 200)
- [x] CI badge indicates passing (`test.yml` badge)

Still required before submit:
- [ ] Record and upload final demo video (<= 2 minutes)
- [x] Add public YouTube/Vimeo link to submission form and project description
- [ ] Upload screenshots and architecture visuals in the platform Images/Video section
- [ ] Confirm Innovation Studio submission is completed and finalized
- [x] Add your Microsoft Learn username
