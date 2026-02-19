"""Risk assessment models."""

from pydantic import BaseModel, Field
from enum import Enum


class RiskFactor(str, Enum):
    """Known risk factors."""

    CACHING_CHANGES = "caching_changes"
    DATABASE_SCHEMA = "database_schema"
    API_CONTRACT = "api_contract"
    TRAFFIC_PATTERN = "traffic_pattern"
    DEPENDENCY_UPDATE = "dependency_update"
    PERMISSION_CHANGES = "permission_changes"
    ENCRYPTION_CHANGES = "encryption_changes"
    LOAD_BALANCING = "load_balancing"
    STORAGE_CHANGES = "storage_changes"


class RiskAssessment(BaseModel):
    """Risk assessment for a deployment."""

    risk_level: str  # 'critical', 'high', 'medium', 'low'
    risk_score: float  # 0-100

    # Contributing factors
    identified_factors: list[RiskFactor] = Field(default_factory=list)

    # SLO impact predictions
    predicted_error_rate_increase_percent: float = 0.0
    predicted_p95_latency_increase_percent: float = 0.0
    predicted_p99_latency_increase_percent: float = 0.0

    # Blast radius
    affected_users_estimated: int = 0
    affected_services: list[str] = Field(default_factory=list)

    # Confidence
    confidence_percent: float = 50.0
    reasoning: str = ""
