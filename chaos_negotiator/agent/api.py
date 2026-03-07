from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import asyncio
import json

from chaos_negotiator.agent.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentChange, DeploymentContext
from chaos_negotiator.models.risk import RiskAssessment


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


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
logger.info("ChaosNegotiatorAgent initialized on API startup")


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
    logger.info("\n%s", "=" * 60)
    logger.info("[%s] API REQUEST: /api/deployments/latest", request_id)
    logger.info("[%s] Building demo context...", request_id)

    ctx = _build_demo_context()
    logger.info("[%s] Demo context built: %s", request_id, ctx.deployment_id)

    contract = agent.process_deployment(ctx)
    logger.info("[%s] Contract generated: %s", request_id, contract.contract_id)

    risk_assessment = contract.risk_assessment
    if not isinstance(risk_assessment, RiskAssessment):
        raise RuntimeError("Deployment contract did not include a valid risk assessment")

    logger.info(
        "[%s] Risk Assessment: score=%.1f, confidence=%.1f%%",
        request_id,
        risk_assessment.risk_score,
        risk_assessment.confidence_percent,
    )

    policy = agent.generate_canary_policy(ctx)
    logger.info("[%s] Canary policy generated with %s stages", request_id, len(policy.stages))

    first_stage = policy.stages[0] if policy.stages else None

    response: dict[str, object] = {
        "service": ctx.service_name,
        # risk_score already ranges 0-100, so we expose it directly as percent
        "risk_percent": risk_assessment.risk_score,
        "confidence_percent": risk_assessment.confidence_percent,
        "risk_level": risk_assessment.risk_level,
        "canary_stage": first_stage.name if first_stage else "smoke",
        "traffic_percent": first_stage.traffic_percent if first_stage else 0,
    }

    logger.info(
        "[%s] RESPONSE: risk=%.1f%%, confidence=%.1f%%, stage=%s",
        request_id,
        response["risk_percent"],
        response["confidence_percent"],
        response["canary_stage"],
    )
    logger.info("[%s] Request complete\n%s\n", request_id, "=" * 60)

    return response


@app.websocket("/ws/dashboard")
async def ws_dashboard_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # We are just broadcasting, so we don't expect any data from the client
            # This will keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from dashboard websocket")


async def broadcast_dashboard_data() -> None:
    """Periodically fetches dashboard data and broadcasts it to all connected WebSocket clients."""
    while True:
        try:
            if manager.active_connections:
                logger.info(
                    "Broadcasting dashboard data to %d clients", len(manager.active_connections)
                )
                data = get_latest_assessment()
                await manager.broadcast(json.dumps(data))
            else:
                logger.info("No active websocket clients to broadcast to.")
        except Exception as e:
            logger.error("Error broadcasting dashboard data: %s", e)
        await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting background task to broadcast dashboard data.")
    asyncio.create_task(broadcast_dashboard_data())
