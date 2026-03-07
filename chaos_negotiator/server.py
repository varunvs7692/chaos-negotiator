"""FastAPI HTTP server for Chaos Negotiator agent."""

import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, TypedDict, cast

from fastapi import FastAPI, Header, HTTPException, Request, Response, WebSocket, WebSocketDisconnect  # type: ignore[import-not-found]
from fastapi.responses import FileResponse  # type: ignore[import-not-found]
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.main import get_example_context
from chaos_negotiator.metrics.opentelemetry import configure_opentelemetry
from chaos_negotiator.models import DeploymentContext, DeploymentChange

# Configure OpenTelemetry
configure_opentelemetry()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DASHBOARD_PATH = STATIC_DIR / "dashboard.html"

# Global agent instance
agent: ChaosNegotiatorAgent | None = None


class RiskState(TypedDict):
    risk_score: float
    risk_level: str
    confidence_percent: float
    identified_factors: list[str]
    predicted_error_rate_increase: float
    predicted_latency_increase: float


class GlobalState(TypedDict):
    risk: RiskState
    last_update: float | None


# Global state for real-time updates
GLOBAL_STATE: GlobalState = {
    "risk": {
        "risk_score": 0,
        "risk_level": "unknown",
        "confidence_percent": 0,
        "identified_factors": [],
        "predicted_error_rate_increase": 0,
        "predicted_latency_increase": 0,
    },
    "last_update": None,
}

# Background task reference
risk_monitor_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown logic."""
    global agent, risk_monitor_task
    logger.info("Starting Chaos Negotiator server...")

    # Initialize agent on startup
    try:
        agent = ChaosNegotiatorAgent()
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        agent = None

    if agent:
        await update_risk_state()

    # Start background risk monitoring task
    logger.info("Starting background risk monitoring task...")
    risk_monitor_task = asyncio.create_task(risk_monitor_loop())

    yield

    logger.info("Shutting down Chaos Negotiator server...")

    # Stop background risk monitoring task
    if risk_monitor_task:
        logger.info("Stopping background risk monitoring task...")
        risk_monitor_task.cancel()
        try:
            await risk_monitor_task
        except asyncio.CancelledError:
            pass

    # gracefully stop background scheduler if agent supports it
    if agent and hasattr(agent, "shutdown"):
        try:
            agent.shutdown()
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Chaos Negotiator",
    description="AI agent that treats every deploy like a contract between developers and reliability goals",
    version="0.1.0",
    lifespan=lifespan,
)

# allow dashboard page or external tools to call our API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Response:
    """Apply baseline security headers to all HTTP responses."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    return response


# Request/Response models
class DeploymentRequest(BaseModel):
    """Deployment context for analysis."""

    deployment_id: str
    service_name: str
    environment: str
    version: str
    changes: list[DeploymentChange]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


class CanaryStageResponse(BaseModel):
    """Serialized canary rollout stage."""

    stage_number: int
    traffic_percent: float
    duration_seconds: int
    name: str


class CanaryStrategyResponse(BaseModel):
    """Serialized canary rollout strategy."""

    deployment_id: str
    risk_score: float
    confidence_percent: float
    error_rate_threshold: float
    latency_threshold_ms: float
    rollback_on_violation: bool
    stages: list[CanaryStageResponse]


class EvaluationResponse(BaseModel):
    """Judge-facing deployment evaluation response."""

    deployment_id: str
    risk_score: float
    risk_level: str
    confidence_percent: float
    canary_strategy: CanaryStrategyResponse


class DeploymentResultRequest(BaseModel):
    """Request model for recording a deployment outcome."""

    deployment_id: str
    actual_error_rate_percent: float
    actual_latency_change_percent: float
    rollback_triggered: bool


@app.get("/", response_model=None)
async def root() -> FileResponse | dict[str, str]:
    """Serve dashboard homepage; fallback to JSON if static file is missing."""
    if DASHBOARD_PATH.exists():
        return FileResponse(str(DASHBOARD_PATH))
    return {"message": "Chaos Negotiator AI Agent", "docs": "/docs", "status": "running"}


@app.get("/api")
async def api_info() -> dict[str, str]:
    """API info endpoint for programmatic clients."""
    return {"message": "Chaos Negotiator AI Agent", "docs": "/docs", "status": "running"}


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service="chaos-negotiator", version="1.0")


@app.get("/static/{file_path:path}", response_model=None)
async def serve_static(file_path: str) -> FileResponse | dict[str, str]:
    """Serve static files (CSS, JS, images)."""
    try:
        full_path = STATIC_DIR / file_path
        if full_path.exists() and full_path.is_file():
            return FileResponse(str(full_path))
    except Exception as e:
        logger.error(f"Error serving static file {file_path}: {e}")
    raise HTTPException(status_code=404, detail="Static file not found")


def _model_to_dict(value: Any) -> dict[str, Any]:
    """Convert a Pydantic model or dict to a plain dict."""
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _require_api_key_if_configured(x_api_key: str | None) -> None:
    """Require API key for protected endpoints when API_AUTH_KEY is configured."""
    configured_key = os.getenv("API_AUTH_KEY", "").strip()
    if not configured_key:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _build_deployment_context(request: DeploymentRequest) -> DeploymentContext:
    """Convert the API request model into the internal deployment context."""
    return DeploymentContext(
        deployment_id=request.deployment_id,
        service_name=request.service_name,
        environment=request.environment,
        version=request.version,
        changes=request.changes,
    )


def _build_canary_strategy(context: DeploymentContext) -> CanaryStrategyResponse:
    """Generate a JSON-safe canary strategy for API responses."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    policy = agent.generate_canary_policy(context)
    return CanaryStrategyResponse(
        deployment_id=policy.deployment_id,
        risk_score=policy.risk_score,
        confidence_percent=policy.confidence_percent,
        error_rate_threshold=policy.error_rate_threshold,
        latency_threshold_ms=policy.latency_threshold_ms,
        rollback_on_violation=policy.rollback_on_violation,
        stages=[
            CanaryStageResponse(
                stage_number=stage.stage_number,
                traffic_percent=stage.traffic_percent,
                duration_seconds=stage.duration_seconds,
                name=stage.name,
            )
            for stage in policy.stages
        ],
    )


def _evaluate_deployment_request(
    request: DeploymentRequest, operation_label: str
) -> EvaluationResponse:
    """Evaluate deployment input and return the public demo response."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        context = _build_deployment_context(request)

        logger.info(f"[{operation_label}] Analyzing deployment {request.deployment_id}...")
        deployment_contract = agent.process_deployment(context)
        risk_assessment = deployment_contract.risk_assessment
        if risk_assessment is None:
            raise HTTPException(status_code=500, detail="Risk assessment unavailable")
        canary_strategy = _build_canary_strategy(context)

        return EvaluationResponse(
            deployment_id=request.deployment_id,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,
            confidence_percent=risk_assessment.confidence_percent,
            canary_strategy=canary_strategy,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in {operation_label.lower()}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to evaluate deployment")


@app.post("/api/deployments/evaluate")
async def evaluate_deployment(
    request: DeploymentRequest, x_api_key: str | None = Header(default=None)
) -> EvaluationResponse:
    """Evaluate a deployment, record outcome, and return contract."""
    _require_api_key_if_configured(x_api_key)
    return _evaluate_deployment_request(request, "EVALUATE")


@app.post("/analyze")
async def analyze_deployment(
    request: DeploymentRequest, x_api_key: str | None = Header(default=None)
) -> EvaluationResponse:
    """Backward-compatible alias for /api/deployments/evaluate."""
    _require_api_key_if_configured(x_api_key)
    return _evaluate_deployment_request(request, "ANALYZE")


@app.get("/demo/{scenario}")
async def run_demo(
    scenario: str = "default", x_api_key: str | None = Header(default=None)
) -> dict[str, object]:
    """Run a demo scenario."""
    _require_api_key_if_configured(x_api_key)

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        scenarios = {
            "default": get_example_context("default"),
            "high-risk": get_example_context("high_risk"),
            "low-risk": get_example_context("low_risk"),
        }

        if scenario not in scenarios:
            raise HTTPException(
                status_code=400, detail=f"Unknown scenario. Valid: {list(scenarios.keys())}"
            )

        context = scenarios[scenario]
        logger.info(f"Running demo scenario: {scenario}")

        deployment_contract = agent.process_deployment(context)
        risk_assessment = _model_to_dict(deployment_contract.risk_assessment)
        rollback_plan = _model_to_dict(deployment_contract.rollback_plan)

        return {
            "scenario": scenario,
            "deployment_id": context.deployment_id,
            "risk_assessment": risk_assessment,
            "rollback_plan": rollback_plan,
            "deployment_contract": deployment_contract.model_dump(),
        }

    except Exception as e:
        logger.error(f"Error running demo: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to run demo scenario")


@app.get("/api/dashboard/risk")
async def get_latest_risk() -> dict[str, Any]:
    """Get latest risk assessment from most recent deployment."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        if GLOBAL_STATE["last_update"] is None:
            await update_risk_state()

        risk_data: dict[str, Any] = dict(GLOBAL_STATE["risk"])
        if GLOBAL_STATE["last_update"] is not None:
            risk_data["last_update"] = GLOBAL_STATE["last_update"]
        return risk_data
    except Exception as e:
        logger.error(f"Error getting risk assessment: {e}")
        raise HTTPException(status_code=400, detail="Failed to get risk assessment")


@app.get("/api/dashboard/history")
async def get_deployment_history(limit: int = 20) -> dict[str, Any]:
    """Get recent deployment history from the learning store."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        outcomes = agent.history_store.recent(limit)
        logger.info(f"[HISTORY] Returning {len(outcomes)} deployment outcomes.")
        return {
            "total": len(outcomes),
            "outcomes": [
                {
                    "deployment_id": o.deployment_id,
                    "heuristic_score": o.heuristic_score,
                    "ml_score": o.ml_score,
                    "final_score": o.final_score,
                    "actual_error_rate": o.actual_error_rate_percent,
                    "actual_latency_change": o.actual_latency_change_percent,
                    "rollback_triggered": o.rollback_triggered,
                    "timestamp": o.timestamp.isoformat(),
                }
                for o in outcomes
            ],
        }
    except Exception as e:
        logger.error(f"Error getting deployment history: {e}")
        raise HTTPException(status_code=400, detail="Failed to get deployment history")


@app.post("/api/deployments/record-result")
async def record_deployment_result(
    result: DeploymentResultRequest, x_api_key: str | None = Header(default=None)
) -> dict[str, Any]:
    """Record the actual outcome of a deployment for learning.

    Call this after deployment completes with the real metrics observed.
    This data feeds the learning loop so the risk engine improves over time.
    """
    _require_api_key_if_configured(x_api_key)

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        logger.info(f"Recording result for deployment: {result.deployment_id}")

        # Build a minimal context for the deployment (we mainly need the ID)
        context = DeploymentContext(
            deployment_id=result.deployment_id,
            service_name="unknown",
            environment="production",
            version="unknown",
            changes=[],
        )

        # Record the outcome
        outcome = agent.record_deployment_result(
            context,
            actual_error_rate_percent=result.actual_error_rate_percent,
            actual_latency_change_percent=result.actual_latency_change_percent,
            rollback_triggered=result.rollback_triggered,
        )

        if outcome is None:
            raise HTTPException(status_code=400, detail="Failed to record deployment result")

        logger.info(f"✅ Deployment result recorded successfully: {result.deployment_id}")

        return {
            "status": "success",
            "deployment_id": outcome.deployment_id,
            "final_score": outcome.final_score,
            "timestamp": outcome.timestamp.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording deployment result: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to record deployment result: {str(e)}")


@app.get("/api/dashboard/canary")
async def get_canary_strategy() -> dict[str, Any]:
    """Get canary deployment strategy for a default scenario."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        context = get_example_context("default")
        return _build_canary_strategy(context).model_dump()
    except Exception as e:
        logger.error(f"Error getting canary strategy: {e}")
        raise HTTPException(status_code=400, detail="Failed to get canary strategy")


# ==================== REAL-TIME WEBSOCKET SUPPORT ====================


async def update_risk_state() -> dict[str, Any]:
    """Update the global risk state by calling the risk predictor."""
    global GLOBAL_STATE

    if not agent:
        return cast(dict[str, Any], GLOBAL_STATE["risk"])

    try:
        context = get_example_context("default")
        assessment = agent.risk_predictor.predict(context)

        GLOBAL_STATE["risk"] = {
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence_percent": assessment.confidence_percent,
            "identified_factors": [f.value for f in assessment.identified_factors],
            "predicted_error_rate_increase": assessment.predicted_error_rate_increase_percent,
            "predicted_latency_increase": assessment.predicted_p95_latency_increase_percent,
        }
        GLOBAL_STATE["last_update"] = asyncio.get_running_loop().time()

        return cast(dict[str, Any], GLOBAL_STATE["risk"])
    except Exception as e:
        logger.error(f"Error updating risk state: {e}")
        return cast(dict[str, Any], GLOBAL_STATE["risk"])


async def risk_monitor_loop() -> None:
    """Background task that periodically updates the risk assessment."""
    logger.info("[RISK MONITOR] Starting background risk monitoring (5s interval)")

    while True:
        try:
            await update_risk_state()
            logger.debug(f"[RISK MONITOR] Updated risk: score={GLOBAL_STATE['risk']['risk_score']}")
        except Exception as e:
            logger.error(f"[RISK MONITOR] Error in monitoring loop: {e}")

        await asyncio.sleep(5)  # Update every 5 seconds


@app.websocket("/ws/risk")
async def websocket_risk(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming real-time risk updates."""
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/risk")

    try:
        while True:
            # Get latest risk data from global state
            risk_data: dict[str, Any] = dict(GLOBAL_STATE["risk"])
            risk_data["timestamp"] = asyncio.get_running_loop().time()

            # Send to client
            await websocket.send_json(risk_data)

            # Wait before next update
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
