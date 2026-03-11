# Final Submission Checklist

Use this before submitting the hackathon entry.

## Core Requirement Checklist

- [ ] Public GitHub repository is accessible
- [ ] Project is developed with VS Code / Visual Studio workflow
- [ ] GitHub Copilot-assisted development is mentioned in submission
- [ ] Azure deployment is working or deployable from included assets
- [ ] At least one hero technology is clearly demonstrated
- [ ] Project description is ready
- [ ] Demo video link is ready
- [ ] Architecture diagram is ready
- [ ] Team member information is ready

## Required Artifact Checklist

- [ ] `README.md` is present and accurate
- [ ] `USER_GUIDE.md` is present
- [ ] `JUDGE_GUIDE.md` is present
- [ ] `SUBMISSION_ARCHITECTURE.md` is present
- [ ] Public app URL is included
- [ ] GitHub repo link is included
- [ ] Demo video link is included in submission form

## Technical Readiness Checklist

- [ ] CI is green
- [ ] `pytest tests -q` passes locally
- [ ] Public dashboard loads
- [ ] `/health` returns `200`
- [ ] `/docs` loads
- [ ] `/api/dashboard/risk` returns JSON
- [ ] `/api/dashboard/history` returns JSON
- [ ] `/api/dashboard/canary` returns JSON
- [ ] Deployment evaluation endpoint works
- [ ] Approval workflow works
- [ ] GitHub webhook ingestion works

## Azure Readiness Checklist

- [ ] Azure Container App is deployed
- [ ] Log Analytics workspace is configured
- [ ] Managed identity exists on the Container App
- [ ] Managed identity has `Log Analytics Data Reader` if live telemetry is required
- [ ] `AZURE_MONITOR_WORKSPACE_ID` is set
- [ ] `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` are set if live model reasoning is required

## Demo Checklist

- [ ] Show the problem in one sentence
- [ ] Show deployment evaluation
- [ ] Show risk score and canary plan
- [ ] Show approval or rejection
- [ ] Show telemetry state
- [ ] Mention Microsoft Agent Framework, Azure MCP-style integration, Azure services, GitHub Copilot
- [ ] Keep video under 2 minutes

## Final Go / No-Go

- [ ] A judge can understand the product in under 30 seconds
- [ ] A judge can verify the project in under 5 minutes
- [ ] The deployed app does not show a broken or blank screen
- [ ] Any fallback mode is documented and intentional
