"""Deployment context and change models."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DeploymentChange(BaseModel):
    """Represents a code change in the deployment."""

    file_path: str
    change_type: str  # 'add', 'modify', 'delete'
    lines_changed: int
    risk_tags: list[str] = Field(default_factory=list)
    description: str


class ServiceDependency(BaseModel):
    """External service dependency affected by this deployment."""

    service_name: str
    service_type: str  # 'database', 'cache', 'api', 'queue', etc.
    criticality: str  # 'critical', 'high', 'medium', 'low'
    average_latency_ms: float
    error_rate_percent: float


class DeploymentContext(BaseModel):
    """Full context of a deployment request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deployment_id": "deploy-123",
                "service_name": "user-service",
                "environment": "production",
                "version": "v2.1.0",
                "changes": [
                    {
                        "file_path": "src/cache/manager.py",
                        "change_type": "modify",
                        "lines_changed": 45,
                        "risk_tags": ["caching", "performance"],
                        "description": "Optimize cache TTL strategy",
                    }
                ],
                "target_error_rate_percent": 0.1,
                "target_p95_latency_ms": 250.0,
            }
        }
    )

    deployment_id: str
    service_name: str
    environment: str  # 'staging', 'production', etc.
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Change information
    changes: list[DeploymentChange] = Field(default_factory=list)
    total_lines_changed: int = 0

    # Service health baseline
    current_error_rate_percent: float = 0.0
    current_p95_latency_ms: float = 0.0
    current_p99_latency_ms: float = 0.0

    # Service dependencies
    dependencies: list[ServiceDependency] = Field(default_factory=list)

    # SLO targets
    target_error_rate_percent: float = 0.1
    target_p95_latency_ms: float = 500.0
    target_p99_latency_ms: float = 1000.0

    # Traffic info
    current_qps: float = 0.0
    peak_qps: float = 0.0

    # Metadata
    owner_team: str = ""
    reviewers: list[str] = Field(default_factory=list)
    rollback_capability: bool = False

    #
