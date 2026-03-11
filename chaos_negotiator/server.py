"""FastAPI HTTP server for Chaos Negotiator agent."""

import asyncio
import hashlib
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

from chaos_negotiator.approval_store import DeploymentApprovalStore
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.main import get_example_context
from chaos_negotiator.metrics.opentelemetry import configure_opentelemetry
from chaos_negotiator.mcp.azure_mcp import AzureMCPClient
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
FRONTEND_INDEX_PATH = STATIC_DIR / "index.html"
DASHBOARD_PATH = STATIC_DIR / "dashboard.html"

# Global agent instance
agent: ChaosNegotiatorAgent | None = None
approval_store = DeploymentApprovalStore()
telemetry_client = AzureMCPClient()


class RiskState(TypedDict):
    risk_score: float
    risk_level: str
    confidence_percent: float
    identified_factors: list[str]
    predicted_error_rate_increase: float
    predicted_latency_increase: float
    deployment_id: str
    service_name: str
    environment: str
    version: str
    telemetry_source: str
    telemetry_status: str
    telemetry_message: str
    current_error_rate_percent: float
    current_p95_latency_ms: float
    current_p99_latency_ms: float
    current_qps: float


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
        "deployment_id": "",
        "service_name": telemetry_client.default_service_name,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "version": "unknown",
        "telemetry_source": "startup",
        "telemetry_status": "degraded",
        "telemetry_message": "Dashboard is starting.",
        "current_error_rate_percent": 0,
        "current_p95_latency_ms": 0,
        "current_p99_latency_ms": 0,
        "current_qps": 0,
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


class ApprovalDecisionRequest(BaseModel):
    """Request payload for approving or rejecting a deployment."""

    reason: str = ""


class PendingDeploymentResponse(BaseModel):
    """Serialized deployment awaiting an approval decision."""

    deployment_id: str
    service_name: str
    environment: str
    version: str
    risk_score: float
    risk_level: str
    confidence_percent: float
    approval_status: str
    decision_reason: str
    canary_strategy: CanaryStrategyResponse
    created_at: str
    updated_at: str


class ApprovalDecisionResponse(PendingDeploymentResponse):
    """Serialized decision result for a deployment."""


class WebhookIngestResponse(BaseModel):
    """Response for GitHub webhook ingestion."""

    event: str
    action: str
    deployment_id: str
    status: str
    evaluation: EvaluationResponse


@app.get("/", response_model=None)
async def root() -> FileResponse | dict[str, str]:
    """Serve the built frontend homepage; fallback to legacy dashboard or JSON."""
    if FRONTEND_INDEX_PATH.exists():
        return FileResponse(str(FRONTEND_INDEX_PATH))
    if DASHBOARD_PATH.exists():
        return FileResponse(str(DASHBOARD_PATH))
    return {"message": "Chaos Negotiator AI Agent", "docs": "/docs", "status": "running"}


@app.get("/dashboard", response_model=None)
@app.get("/dashboard.html", response_model=None)
@app.get("/static/dashboard.html", response_model=None)
async def dashboard_entrypoint() -> FileResponse | dict[str, str]:
    """Serve the resilient dashboard entrypoint for current and legacy URLs."""
    return await root()


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
        candidate_paths = [
            STATIC_DIR / file_path,
            STATIC_DIR / "static" / file_path,
        ]
        for full_path in candidate_paths:
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


def _require_github_signature_if_configured(body: bytes, signature: str | None) -> None:
    """Require a valid GitHub webhook signature when GITHUB_WEBHOOK_SECRET is configured."""
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="Missing GitHub signature")

    expected = (
        "sha256="
        + hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")


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


def _approval_record_to_response(record: dict[str, Any]) -> ApprovalDecisionResponse:
    """Convert approval store records to API response models."""
    return ApprovalDecisionResponse(
        deployment_id=record["deployment_id"],
        service_name=record["service_name"],
        environment=record["environment"],
        version=record["version"],
        risk_score=record["risk_score"],
        risk_level=record["risk_level"],
        confidence_percent=record["confidence_percent"],
        approval_status=record["approval_status"],
        decision_reason=record["decision_reason"],
        canary_strategy=CanaryStrategyResponse.model_validate(record["canary_strategy"]),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


def _evaluate_deployment_contract(
    request: DeploymentRequest, operation_label: str
) -> tuple[EvaluationResponse, dict[str, Any]]:
    """Evaluate deployment input and return the public response plus contract payload."""
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

        response = EvaluationResponse(
            deployment_id=request.deployment_id,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,
            confidence_percent=risk_assessment.confidence_percent,
            canary_strategy=canary_strategy,
        )
        return response, deployment_contract.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in {operation_label.lower()}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to evaluate deployment")


def _save_evaluation_record(
    request: DeploymentRequest,
    response: EvaluationResponse,
    contract: dict[str, Any],
) -> None:
    """Persist an evaluated deployment for review workflows."""
    contract_payload = dict(contract)
    contract_payload["deployment_context"] = request.model_dump(mode="json")
    approval_store.save_evaluation(
        deployment_id=request.deployment_id,
        service_name=request.service_name,
        environment=request.environment,
        version=request.version,
        risk_score=response.risk_score,
        risk_level=response.risk_level,
        confidence_percent=response.confidence_percent,
        contract=contract_payload,
        canary_strategy=response.canary_strategy.model_dump(),
    )


def _get_latest_dashboard_record() -> dict[str, Any] | None:
    """Return the most recent evaluated deployment if available."""
    records = approval_store.list_recent(limit=1)
    if not records:
        return None
    return records[0]


def _deserialize_changes(raw_changes: Any) -> list[DeploymentChange]:
    """Best-effort conversion of persisted change payloads into models."""
    if not isinstance(raw_changes, list):
        return []
    changes: list[DeploymentChange] = []
    for item in raw_changes:
        if not isinstance(item, dict):
            continue
        try:
            changes.append(DeploymentChange.model_validate(item))
        except Exception:
            logger.warning("Skipping invalid persisted deployment change: %s", item)
    return changes


async def _build_live_dashboard_context() -> tuple[DeploymentContext | None, dict[str, Any] | None, dict[str, Any]]:
    """Build dashboard context from latest real deployment plus Azure telemetry."""
    latest_record = _get_latest_dashboard_record()
    service_name = (
        latest_record["service_name"] if latest_record else telemetry_client.default_service_name
    )
    telemetry = await telemetry_client.get_current_metrics(
        service_name,
        ["error_rate", "p95_latency", "p99_latency", "qps"],
    )

    environment = (
        latest_record["environment"]
        if latest_record
        else os.getenv("ENVIRONMENT", "production")
    )
    version = latest_record["version"] if latest_record else os.getenv("APP_VERSION", "live")
    deployment_id = (
        latest_record["deployment_id"]
        if latest_record
        else f"live-{service_name.replace(' ', '-')}"
    )

    context_payload: dict[str, Any] = {}
    if latest_record:
        contract = latest_record.get("contract") or {}
        raw_context = contract.get("deployment_context")
        if isinstance(raw_context, dict):
            context_payload = dict(raw_context)

    changes = _deserialize_changes(context_payload.get("changes"))
    total_lines_changed = context_payload.get("total_lines_changed")
    if not isinstance(total_lines_changed, int):
        total_lines_changed = sum(change.lines_changed for change in changes)

    context = DeploymentContext(
        deployment_id=str(context_payload.get("deployment_id") or deployment_id),
        service_name=str(context_payload.get("service_name") or service_name),
        environment=str(context_payload.get("environment") or environment),
        version=str(context_payload.get("version") or version),
        changes=changes,
        total_lines_changed=total_lines_changed,
        current_error_rate_percent=float(
            telemetry["error_rate_percent"]
            if telemetry.get("available", False)
            else context_payload.get("current_error_rate_percent", 0.0)
        ),
        current_p95_latency_ms=float(
            telemetry["p95_latency_ms"]
            if telemetry.get("available", False)
            else context_payload.get("current_p95_latency_ms", 0.0)
        ),
        current_p99_latency_ms=float(
            telemetry["p99_latency_ms"]
            if telemetry.get("available", False)
            else context_payload.get("current_p99_latency_ms", 0.0)
        ),
        target_error_rate_percent=float(context_payload.get("target_error_rate_percent", 0.1)),
        target_p95_latency_ms=float(context_payload.get("target_p95_latency_ms", 500.0)),
        target_p99_latency_ms=float(context_payload.get("target_p99_latency_ms", 1000.0)),
        current_qps=float(
            telemetry["qps"] if telemetry.get("available", False) else context_payload.get("current_qps", 0.0)
        ),
        peak_qps=float(context_payload.get("peak_qps", context_payload.get("current_qps", 0.0))),
        owner_team=str(context_payload.get("owner_team", "")),
        reviewers=[
            str(reviewer) for reviewer in context_payload.get("reviewers", []) if isinstance(reviewer, str)
        ],
        rollback_capability=bool(context_payload.get("rollback_capability", True)),
    )
    return context, latest_record, telemetry


async def _build_live_risk_payload() -> dict[str, Any]:
    """Build the live dashboard risk payload from real deployment and telemetry data."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    context, latest_record, telemetry = await _build_live_dashboard_context()
    telemetry_status = "live" if telemetry.get("available", False) else "degraded"
    telemetry_message = str(telemetry.get("message", ""))

    if context is not None:
        assessment = agent.risk_predictor.predict(context)
        risk_payload = {
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence_percent": assessment.confidence_percent,
            "identified_factors": [factor.value for factor in assessment.identified_factors],
            "predicted_error_rate_increase": assessment.predicted_error_rate_increase_percent,
            "predicted_latency_increase": assessment.predicted_p95_latency_increase_percent,
            "deployment_id": context.deployment_id,
            "service_name": context.service_name,
            "environment": context.environment,
            "version": context.version,
        }
    elif latest_record is not None:
        risk_payload = {
            "risk_score": float(latest_record["risk_score"]),
            "risk_level": str(latest_record["risk_level"]),
            "confidence_percent": float(latest_record["confidence_percent"]),
            "identified_factors": [],
            "predicted_error_rate_increase": 0.0,
            "predicted_latency_increase": 0.0,
            "deployment_id": str(latest_record["deployment_id"]),
            "service_name": str(latest_record["service_name"]),
            "environment": str(latest_record["environment"]),
            "version": str(latest_record["version"]),
        }
    else:
        risk_payload = {
            "risk_score": 0.0,
            "risk_level": "unknown",
            "confidence_percent": 0.0,
            "identified_factors": [],
            "predicted_error_rate_increase": 0.0,
            "predicted_latency_increase": 0.0,
            "deployment_id": "",
            "service_name": telemetry_client.default_service_name,
            "environment": os.getenv("ENVIRONMENT", "production"),
            "version": "unknown",
        }
        telemetry_message = telemetry_message or "No deployment evaluation or Azure telemetry is available yet."

    risk_payload.update(
        {
            "telemetry_source": str(telemetry.get("source", "unknown")),
            "telemetry_status": telemetry_status,
            "telemetry_message": telemetry_message,
            "current_error_rate_percent": float(telemetry.get("error_rate_percent", 0.0)),
            "current_p95_latency_ms": float(telemetry.get("p95_latency_ms", 0.0)),
            "current_p99_latency_ms": float(telemetry.get("p99_latency_ms", 0.0)),
            "current_qps": float(telemetry.get("qps", 0.0)),
        }
    )
    return risk_payload


def _build_request_from_github_webhook(event: str, payload: dict[str, Any]) -> DeploymentRequest:
    """Translate GitHub deployment/workflow payloads into an internal deployment request."""
    repo = payload.get("repository") or {}
    repo_name = repo.get("name", "unknown-service")
    workflow_run = payload.get("workflow_run") or {}
    deployment = payload.get("deployment") or {}
    workflow_name = workflow_run.get("name") or payload.get("workflow") or "github-workflow"
    environment = (
        deployment.get("environment")
        or workflow_run.get("environment")
        or payload.get("environment")
        or "production"
    )
    version = (
        payload.get("after") or workflow_run.get("head_sha") or deployment.get("sha") or "unknown"
    )
    deployment_id = str(
        deployment.get("id")
        or workflow_run.get("id")
        or payload.get("delivery")
        or f"{event}-{version[:12]}"
    )
    file_count = len(payload.get("commits", [])) or len(
        payload.get("head_commit", {}).get("modified", [])
    )
    lines_changed = max(file_count * 25, 1)
    risk_tags = ["ci-cd", "github"]
    if environment == "production":
        risk_tags.append("production")
    if event == "deployment_status":
        risk_tags.append("deployment")
    if event == "workflow_run":
        risk_tags.append("workflow")

    change = DeploymentChange(
        file_path=f".github/workflows/{workflow_name}",
        change_type="modify",
        lines_changed=lines_changed,
        risk_tags=risk_tags,
        description=f"GitHub {event} event for {workflow_name}",
    )
    return DeploymentRequest(
        deployment_id=deployment_id,
        service_name=repo_name,
        environment=environment,
        version=version[:40],
        changes=[change],
    )


@app.post("/api/deployments/evaluate")
async def evaluate_deployment(
    request: DeploymentRequest, x_api_key: str | None = Header(default=None)
) -> EvaluationResponse:
    """Evaluate a deployment, record outcome, and return contract."""
    _require_api_key_if_configured(x_api_key)
    response, contract = _evaluate_deployment_contract(request, "EVALUATE")
    _save_evaluation_record(request, response, contract)
    return response


@app.post("/analyze")
async def analyze_deployment(
    request: DeploymentRequest, x_api_key: str | None = Header(default=None)
) -> EvaluationResponse:
    """Backward-compatible alias for /api/deployments/evaluate."""
    _require_api_key_if_configured(x_api_key)
    response, _ = _evaluate_deployment_contract(request, "ANALYZE")
    return response


@app.post("/api/webhooks/github")
async def ingest_github_webhook(
    request: Request,
    x_github_event: str = Header(alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> WebhookIngestResponse:
    """Ingest GitHub deployment/workflow events and turn them into deployment evaluations."""
    body = await request.body()
    _require_github_signature_if_configured(body, x_hub_signature_256)

    if x_github_event not in {"workflow_run", "deployment", "deployment_status"}:
        raise HTTPException(status_code=400, detail="Unsupported GitHub event")

    payload = await request.json()
    deployment_request = _build_request_from_github_webhook(x_github_event, payload)
    evaluation, contract = _evaluate_deployment_contract(
        deployment_request,
        f"GITHUB_{x_github_event.upper()}",
    )
    _save_evaluation_record(deployment_request, evaluation, contract)

    return WebhookIngestResponse(
        event=x_github_event,
        action=str(payload.get("action", "received")),
        deployment_id=deployment_request.deployment_id,
        status="ingested",
        evaluation=evaluation,
    )


@app.get("/api/deployments/pending")
async def list_pending_deployments(limit: int = 50) -> dict[str, list[PendingDeploymentResponse]]:
    """List deployments waiting for approval."""
    records = approval_store.list_pending(limit=limit)
    return {"deployments": [_approval_record_to_response(record) for record in records]}


@app.get("/api/deployments/{deployment_id}")
async def get_deployment_status(deployment_id: str) -> ApprovalDecisionResponse:
    """Return the persisted approval record for a deployment."""
    record = approval_store.get(deployment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _approval_record_to_response(record)


@app.post("/api/deployments/{deployment_id}/approve")
async def approve_deployment(
    deployment_id: str,
    decision: ApprovalDecisionRequest,
    x_api_key: str | None = Header(default=None),
) -> ApprovalDecisionResponse:
    """Approve a deployment after review."""
    _require_api_key_if_configured(x_api_key)
    record = approval_store.update_status(deployment_id, "approved", decision.reason)
    if record is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _approval_record_to_response(record)


@app.post("/api/deployments/{deployment_id}/reject")
async def reject_deployment(
    deployment_id: str,
    decision: ApprovalDecisionRequest,
    x_api_key: str | None = Header(default=None),
) -> ApprovalDecisionResponse:
    """Reject a deployment after review."""
    _require_api_key_if_configured(x_api_key)
    record = approval_store.update_status(deployment_id, "rejected", decision.reason)
    if record is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _approval_record_to_response(record)


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
    """Get recent deployment history from local learning data and Azure telemetry."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        outcomes = agent.history_store.recent(limit)
        latest_record = _get_latest_dashboard_record()
        service_name = (
            latest_record["service_name"]
            if latest_record is not None
            else telemetry_client.default_deployment_history_service
        )
        live_deployments = await telemetry_client.get_deployment_history(service_name, limit=min(limit, 10))
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
            "live_deployments": live_deployments,
            "service_name": service_name,
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
    """Get canary deployment strategy for the latest real deployment context."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        context, latest_record, telemetry = await _build_live_dashboard_context()
        if context is not None:
            payload = _build_canary_strategy(context).model_dump()
        elif latest_record is not None:
            payload = dict(latest_record["canary_strategy"])
        else:
            raise HTTPException(status_code=404, detail="No live deployment context available")

        payload["telemetry_status"] = "live" if telemetry.get("available", False) else "degraded"
        payload["telemetry_source"] = telemetry.get("source", "unknown")
        payload["service_name"] = payload.get("service_name") or telemetry.get("service_name")
        return payload
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
        GLOBAL_STATE["risk"] = cast(RiskState, await _build_live_risk_payload())
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
