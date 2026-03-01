from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from chaos_negotiator.agent.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentContext, DeploymentChange

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()
# allow the dashboard (running on localhost:3000) to call our API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ChaosNegotiatorAgent()
logger.info("✅ ChaosNegotiatorAgent initialized on API startup")


def _build_demo_context() -> DeploymentContext:
    """Create a minimal deployment context for live demo.

    Eventually this data will come from actual CI/CD payloads, webhooks, etc.
    For now we hardcode a couple of `DeploymentChange` entries to exercise the
    risk predictor and canary engine.
    """
    ctx = DeploymentContext(
        deployment_id="deploy-demo-001",
        service_name="payments",
        environment="production",
        version="v1.2.3",
        changes=[
            DeploymentChange(
                file_path="src/services/payments/api.py",
                change_type="modify",
                lines_changed=120,
                risk_tags=["api"],
                description="Add new payment endpoint with API changes",
            ),
            DeploymentChange(
                file_path="infra/db/migration.sql",
                change_type="add",
                lines_changed=60,
                risk_tags=["db"],
                description="Database migration for transaction table",
            ),
        ],
        current_error_rate_percent=0.05,
        current_p95_latency_ms=150.0,
        target_error_rate_percent=0.1,
        target_p95_latency_ms=300.0,
        rollback_capability=True,
    )
    return ctx


@app.get("/api/deployments/latest")
def get_latest_assessment() -> dict[str, object]:
    """Return a live assessment based on the demo context.

    The response is built from the *contract* returned by the agent so that the
    frontend is always reflecting the same data that would be stored or acted
    on by the system.
    """
    request_id = int(time.time() * 1000)
    logger.info(f"\n{'='*60}")
    logger.info(f"[{request_id}] 🔵 API REQUEST: /api/deployments/latest")
    logger.info(f"[{request_id}] Building demo context...")

    ctx = _build_demo_context()
    logger.info(f"[{request_id}] ✅ Demo context built: {ctx.deployment_id}")

    # full processing returns a deployment contract with risk & rollback info
    logger.info(f"[{request_id}] 🔄 Calling agent.process_deployment()...")
    contract = agent.process_deployment(ctx)
    logger.info(f"[{request_id}] ✅ Contract generated: {contract.contract_id}")
    logger.info(
        f"[{request_id}] ✅ Risk Assessment: score={contract.risk_assessment.risk_score:.1f}, confidence={contract.risk_assessment.confidence_percent:.1f}%"
    )

    # generate canary policy from the same context (uses contract internally)
    logger.info(f"[{request_id}] 🔄 Calling agent.generate_canary_policy()...")
    policy = agent.generate_canary_policy(ctx)
    logger.info(f"[{request_id}] ✅ Canary policy generated with {len(policy.stages)} stages")

    first_stage = policy.stages[0] if policy.stages else None

    ra = contract.risk_assessment
    response = {
        "service": ctx.service_name,
        # risk_score already ranges 0–100, so we expose it directly as percent
        "risk_percent": ra.risk_score,
        "confidence_percent": ra.confidence_percent,
        "risk_level": ra.risk_level,
        "canary_stage": first_stage.name if first_stage else "smoke",
        "traffic_percent": first_stage.traffic_percent if first_stage else 0,
    }

    logger.info(
        f"[{request_id}] 📤 RESPONSE: risk={response['risk_percent']:.1f}%, confidence={response['confidence_percent']:.1f}%, stage={response['canary_stage']}"
    )
    logger.info(f"[{request_id}] ✅ Request complete\n{'='*60}\n")

    return response
