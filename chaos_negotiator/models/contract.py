"""Deployment contract models."""

from datetime import datetime
from typing import Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class GuardrailType(str, Enum):
    """Types of guardrails in deployment contracts."""

    ERROR_RATE = "error_rate"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    TRAFFIC_RAMP = "traffic_ramp"
    RESOURCE_LIMIT = "resource_limit"


class GuardrailRequirement(BaseModel):
    """A single guardrail requirement."""

    guardrail_type: GuardrailType
    max_value: float
    unit: str  # '%', 'ms', 'rps', etc.
    description: str
    enforcement_window_seconds: int = 300


class Guardrail(BaseModel):
    """Simplified guardrail for enforcement (compatible with older code)."""

    metric_name: str
    threshold: float
    comparison: str = "less_than"  # 'less_than', 'greater_than', 'equals'


class ValidatorRequirement(BaseModel):
    """A validation requirement before deployment approval."""

    validator_type: str  # 'test', 'canary', 'feature_flag', 'manual', 'rollback_plan'
    required: bool = True
    description: str
    estimated_duration_seconds: int = 0


class DeploymentContract(BaseModel):
    """
    Auto-drafted deployment contract.

    Answers:
    - What could break? (risk prediction)
    - What are the guardrails? (max error rate, latency budget, traffic ramp limits)
    - How fast can we undo it? (rollback window + tested steps)
    - What proof is required? (tests, canary metrics, safe rollback)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contract_id": "contract-123",
                "deployment_id": "deploy-123",
                "service_name": "user-service",
                "predicted_risk_level": "high",
                "risk_score": 72.5,
                "risk_summary": "Cache logic change impacts latency-sensitive path",
                "guardrails": [
                    {
                        "guardrail_type": "error_rate",
                        "max_value": 0.5,
                        "unit": "%",
                        "description": "Error rate must stay below 0.5%",
                    },
                    {
                        "guardrail_type": "latency_p95",
                        "max_value": 250,
                        "unit": "ms",
                        "description": "P95 latency must stay under 250ms",
                    },
                ],
                "validators": [
                    {
                        "validator_type": "canary",
                        "required": True,
                        "description": "Canary deployment to 5% traffic",
                    },
                    {
                        "validator_type": "rollback_plan",
                        "required": True,
                        "description": "Tested rollback procedure",
                    },
                ],
                "rollback_window_seconds": 300,
                "rollback_possible": True,
                "status": "draft",
            }
        }
    )

    contract_id: str
    deployment_id: str
    service_name: str

    # Risk assessment
    predicted_risk_level: str  # 'critical', 'high', 'medium', 'low'
    risk_score: float  # 0-100
    risk_summary: str

    # Guardrails (the terms) - accepts both GuardrailRequirement and Guardrail
    guardrails: list[Union[GuardrailRequirement, "Guardrail"]] = Field(default_factory=list)

    # Validators (proof requirements)
    validators: list[ValidatorRequirement] = Field(default_factory=list)

    # Rollback capability
    rollback_window_seconds: int = 300
    rollback_possible: bool = False
    rollback_steps_count: int = 0

    # Contract status
    status: str = (
        "draft"  # 'draft', 'negotiating', 'approved', 'deployed', 'violated', 'rolled_back'
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None

    # Suggested fixes (negotiation)
    suggested_fixes: list[str] = Field(default_factory=list)

    # Detailed reasoning
    reasoning: str = ""
    
    # Optional nested structures (for agent-generated contracts)
    deployment_context: Optional[Any] = None  # DeploymentContext
    risk_assessment: Optional[Any] = None  # RiskAssessment
    rollback_plan: Optional[Any] = None  # RollbackPlan
    approval_status: str = "pending"  # 'pending', 'approved', 'rejected'
