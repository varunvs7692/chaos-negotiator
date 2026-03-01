"""FastAPI HTTP server for Chaos Negotiator agent."""

import hmac
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Header, HTTPException, Request, Response  # type: ignore[import-not-found]
from fastapi.responses import FileResponse  # type: ignore[import-not-found]
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.main import get_example_context
from chaos_negotiator.models import DeploymentContext, DeploymentChange

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown logic."""
    global agent
    logger.info("Starting Chaos Negotiator server...")

    # Initialize agent on startup
    try:
        agent = ChaosNegotiatorAgent()
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        agent = None

    yield

    logger.info("Shutting down Chaos Negotiator server...")
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
    changes: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    agent_ready: bool


class AnalysisResponse(BaseModel):
    """Deployment analysis response."""

    deployment_id: str
    risk_assessment: dict
    rollback_plan: dict
    deployment_contract: dict


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
    return HealthResponse(status="healthy" if agent else "unhealthy", agent_ready=agent is not None)


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


@app.post("/analyze")
async def analyze_deployment(
    request: DeploymentRequest, x_api_key: str | None = Header(default=None)
) -> AnalysisResponse:
    """Analyze a deployment for risk and contract requirements."""
    _require_api_key_if_configured(x_api_key)

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Convert request to DeploymentContext
        changes = [DeploymentChange(**change) for change in request.changes]

        context = DeploymentContext(
            deployment_id=request.deployment_id,
            service_name=request.service_name,
            environment=request.environment,
            version=request.version,
            changes=changes,
        )

        # Run analysis
        logger.info(f"Analyzing deployment {request.deployment_id}...")
        deployment_contract = agent.process_deployment(context)
        risk_assessment = _model_to_dict(deployment_contract.risk_assessment)
        rollback_plan = _model_to_dict(deployment_contract.rollback_plan)

        return AnalysisResponse(
            deployment_id=request.deployment_id,
            risk_assessment=risk_assessment,
            rollback_plan=rollback_plan,
            deployment_contract=deployment_contract.model_dump(),
        )

    except Exception as e:
        logger.error(f"Error analyzing deployment: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to analyze deployment")


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
        context = get_example_context("default")
        assessment = agent.risk_predictor.predict(context)

        return {
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence_percent": assessment.confidence_percent,
            "identified_factors": [f.value for f in assessment.identified_factors],
            "predicted_error_rate_increase": assessment.predicted_error_rate_increase_percent,
            "predicted_latency_increase": assessment.predicted_p95_latency_increase_percent,
        }
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


@app.get("/api/dashboard/canary")
async def get_canary_strategy() -> dict[str, Any]:
    """Get canary deployment strategy for a default scenario."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        context = get_example_context("default")
        policy = agent.generate_canary_policy(context)

        return {
            "deployment_id": policy.deployment_id,
            "risk_score": policy.risk_score,
            "confidence_percent": policy.confidence_percent,
            "error_rate_threshold": policy.error_rate_threshold,
            "latency_threshold_ms": policy.latency_threshold_ms,
            "stages": [
                {
                    "stage_number": s.stage_number,
                    "traffic_percent": s.traffic_percent,
                    "duration_seconds": s.duration_seconds,
                    "name": s.name,
                }
                for s in policy.stages
            ],
        }
    except Exception as e:
        logger.error(f"Error getting canary strategy: {e}")
        raise HTTPException(status_code=400, detail="Failed to get canary strategy")


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
