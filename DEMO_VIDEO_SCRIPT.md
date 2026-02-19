# Chaos Negotiator - Demo Video Script (2 minutes)

## Scene 1: Problem Statement (0:00 - 0:15)

**[Visual: GitHub PR screen showing code changes]**

**Narrator:** "Every deployment is a bet on reliability. Traditional DevOps asks: 'Did tests pass?' But we ask a smarter question..."

**[Cut to: SLO dashboard showing error rates and latency]**

**Narrator:** "Will this deployment keep us within our SLOs? Will we be able to safely recover if something breaks?"

**[Cut to: Red warning screen - deployment blocked]**

**Narrator:** "Most deployment controls are binary. But reliability isn't."

---

## Scene 2: The Solution - Chaos Negotiator (0:15 - 0:45)

**[Visual: Architecture diagram of Chaos Negotiator]**

**Narrator:** "Enter Chaos Negotiator - an AI agent powered by Azure OpenAI and Microsoft Agent Framework that treats every deployment like a **contract negotiation**."

**[Cut to: GitHub Actions pipeline triggering]**

**Narrator:** "When code is pushed, our agent springs into action..."

**[Show terminal/logs of agent running]**

```
DeploymentContext analyzed:
├─ Changes detected: 45 lines in cache manager
├─ Risk pattern: High-impact caching change
└─ Current metrics: 0.05% error rate, 180ms p95
```

**Narrator:** "First, it runs **risk prediction**..."

**[Visual: Risk scoring animation - moving from low to high]**

```
RiskAssessment:
├─ Risk Level: HIGH (score: 78/100)
├─ Predicted error increase: 0.2% → 0.35%
├─ Predicted latency increase: 180ms → 220ms
└─ Reasoning: Aggressive cache TTL without fallback...
```

**Narrator:** "Then it validates **rollback capability**..."

**[Show rollback procedure being tested]**

```
RollbackValidator:
├─ Procedure: 1. Revert cache config
├─ Estimated recovery: 85 seconds
├─ Data loss risk: None (read-only cache)
└─ Tested? ✓ YES
```

**Narrator:** "Finally, it **drafts a deployment contract** with guardrails and negotiation terms..."

**[Highlight: Contract Engine output]**

```
DEPLOYMENT CONTRACT
═══════════════════════════════════════

📋 NEGOTIATED TERMS:
├─ Error rate budget: <0.20% (max +0.15%)
├─ P95 latency budget: <210ms (max +30ms)
├─ Traffic ramp: 5% → 25% → 100% (5-min intervals)
├─ Canary metrics: 30 req samples minimum
└─ Rollback window: 300 seconds

✓ GUARDRAILS ENFORCEMENT:
├─ Real-time Azure Monitor integration
├─ Automatic rollback if violated
└─ Audit trail in Application Insights

📝 MITIGATIONS SUGGESTED:
├─ Add cache hit/miss metrics
├─ Implement fallback to DB
└─ Test under 2x load before production
```

---

## Scene 3: Live Enforcement (0:45 - 1:30)

**[Visual: Real-time metrics dashboard from Azure Monitor]**

**Narrator:** "Now watch it in action as we deploy..."

**[Show deployment starting with contract terms visible]**

**Narrator:** "The agent monitors convergence in real-time, tracking metrics against the negotiated contract..."

**[Graph shows metrics being collected]**

```
DEPLOYMENT MONITORING:
├─ Phase 1 [5%]: ✓ 0.07% error, 188ms p95 (within budget)
├─ Phase 2 [25%]: ✓ 0.09% error, 202ms p95 (within budget)
├─ Phase 3 [100%]: ⚠ 0.35% error detected! EXCEEDS 0.20%
└─ ACTION: Initiating automated rollback...
```

**[Visual: Automatic rollback triggered]**

**Narrator:** "When guardrails are violated, it automatically rolls back within the tested window - 85 seconds to full recovery."

**[Show metrics returning to baseline]**

```
ROLLBACK EXECUTED:
├─ Time to trigger: 2.3 seconds
├─ Recovery time: 85 seconds
├─ Error rate back to: 0.06%
└─ Audit entry: deployment-001-rollback-triggered
```

**[Visual: Audit trail in Application Insights]**

**Narrator:** "Every decision is logged for compliance and continuous learning."

---

## Scene 4: Key Benefits (1:30 - 1:50)

**[Visual: Three screens side-by-side showing benefits]**

**Narrator:** "Chaos Negotiator delivers three game-changing capabilities:"

1. **Screen 1: Intelligent Risk Analysis**
   - Pattern recognition of high-risk changes
   - Confidence-scored impact predictions
   - Smart mitigation suggestions

2. **Screen 2: Agentic DevOps Workflow**
   - Autonomous decision-making
   - Real-time guardrail enforcement
   - Automatic rollback with safe windows

3. **Screen 3: SLO-Centric Deployment**
   - Contract-based reliability gates
   - Data-driven negotiation
   - Audit-ready compliance trail

**Narrator:** "No more binary pass/fail. Just intelligent, enforceable reliability contracts."

---

## Scene 5: Technology Stack & Call to Action (1:50 - 2:00)

**[Visual: Quick tech logos/stack]**

**Narrator:** "Built on Microsoft's AI platform:"
- Microsoft Agent Framework for orchestration
- Azure OpenAI (GPT-4) for reasoning
- Azure MCP for service integration
- Azure Container Apps for deployment
- GitHub Actions & GitHub Copilot for development

**[Final screen: GitHub repo link + "Chaos Negotiator" title]**

**Narrator:** "Chaos Negotiator - where deployment contracts meet intelligent reliability. Open source. Production-ready. Join the negotiation."

**[End with: Link to repo, Microsoft Build 2026 logo]**

---

## 📹 Production Notes

- **Duration:** Exactly 2:00 minutes
- **Pacing:** Quick, energetic cuts (change screen every 3-5 seconds)
- **Visuals:** Use actual terminal output, dashboard screenshots, and metrics graphs
- **Narration:** Conversational, technical but accessible
- **Music:** Subtle, tech-oriented background track (no copyrighted material)
- **Captions:** Add for accessibility
- **Color scheme:** Azure blues (#0078D4), success greens (#238636), alert oranges (#FF6B35)

---

## 📺 Suggested Platform & Checklist

- [ ] Record locally with VS Code + terminal visible
- [ ] Capture Azure Monitor dashboard live (or recorded)
- [ ] Use screen recording tool (OBS, ScreenFlow, etc.)
- [ ] Upload to YouTube as **unlisted** (private until submission)
- [ ] No copyrighted music - use royalty-free options:
  - freepik.com/videos
  - pexels.com
  - pixabay.com
- [ ] Ensure video is **not larger than 2 min**
- [ ] Provide public YouTube link in submission
