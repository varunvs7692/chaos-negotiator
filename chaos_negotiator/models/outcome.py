"""Models related to deployment outcomes and history."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class DeploymentOutcome(BaseModel):
    """Represents the real-world result of a deployment.

    This record is primarily used for learning: after a deployment runs we
    store what the agent predicted and what actually happened so the risk
    engine can adjust its weights over time.
    """

    deployment_id: str
    heuristic_score: float
    ml_score: float
    final_score: float

    actual_error_rate_percent: float
    actual_latency_change_percent: float
    rollback_triggered: bool

    timestamp: datetime = Field(default_factory=datetime.utcnow)
