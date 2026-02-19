"""Rollback plan models."""

from pydantic import BaseModel, Field


class RollbackStep(BaseModel):
    """A single step in rollback procedure."""

    step_number: int
    description: str
    command: str
    estimated_duration_seconds: int
    dependencies: list[int] = Field(default_factory=list)
    validation_method: str = ""  # 'health_check', 'metric_monitor', 'manual', etc.


class RollbackPlan(BaseModel):
    """Complete rollback plan for a deployment."""

    plan_id: str
    deployment_id: str
    rollback_possible: bool
    total_estimated_time_seconds: int = 0
    steps: list[RollbackStep] = Field(default_factory=list)
    rollback_steps_count: int = 0
    rollback_window_seconds: int = 0

    # Validation
    plan_tested: bool = False
    test_date: str = ""
    test_results: str = ""

    # Constraints
    data_loss_risk: str = "none"  # 'none', 'low', 'medium', 'high'
    service_disruption_expected: bool = False
    disruption_window_seconds: int = 0

    reasoning: str = ""
