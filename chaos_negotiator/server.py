"""FastAPI HTTP server for Chaos Negotiator agent."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Header, HTTPException  # type: ignore[import-not-found]
from fastapi.responses import FileResponse  # type: ignore[import-not-found]
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

STATIC_INDEX_PATH = Path(__file__).resolve().parent / "static" / "index.html"

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


# Create FastAPI app
app = FastAPI(
    title="Chaos Negotiator",
    description="AI agent that treats every deploy like a contract between developers and reliability goals",
    version="0.1.0",
    lifespan=lifespan,
)


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
    """Serve UI homepage; fallback to JSON if static file is missing."""
    if STATIC_INDEX_PATH.exists():
        return FileResponse(str(STATIC_INDEX_PATH))
    return {"message": "Chaos Negotiator AI Agent", "docs": "/docs", "status": "running"}


@app.get("/api")
async def api_info() -> dict[str, str]:
    """API info endpoint for programmatic clients."""
    return {"message": "Chaos Negotiator AI Agent", "docs": "/docs", "status": "running"}


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy" if agent else "unhealthy", agent_ready=agent is not None)


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
    if not x_api_key or x_api_key != configured_key:
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
        raise HTTPException(status_code=400, detail=str(e))


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
        raise HTTPException(status_code=400, detail=str(e))


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
