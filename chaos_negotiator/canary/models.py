"""Canary deployment models and orchestration."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List


class CanaryStage(BaseModel):
    """A single stage in the canary rollout."""

    stage_number: int
    traffic_percent: float
    duration_seconds: int
    name: str = ""


class CanaryPolicy(BaseModel):
    """Policy that defines canary rollout based on risk and confidence."""

    deployment_id: str
    risk_score: float  # 0-100
    confidence_percent: float  # 0-100
    stages: List[CanaryStage] = Field(default_factory=list)

    # Guardrails that trigger rollback
    error_rate_threshold: float = 0.5  # %
    latency_threshold_ms: float = 500.0
    rollback_on_violation: bool = True

    # Status
    current_stage: int = 0
    completed: bool = False


class CanaryResult(BaseModel):
    """Result/recommendation from canary orchestrator."""

    deployment_id: str
    recommended_traffic_percent: float
    reason: str
    guardrails: dict = Field(default_factory=dict)
    ready_to_promote: bool = False
