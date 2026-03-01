"""Tests for canary deployment engine."""

import pytest
from chaos_negotiator.models import DeploymentContext, DeploymentChange, RiskAssessment
from chaos_negotiator.canary import CanaryOrchestrator, CanaryPolicy


def test_canary_high_risk_low_confidence():
    """High risk with low confidence should result in slow rollout."""
    context = DeploymentContext(
        deployment_id="canary-001",
        service_name="critical-svc",
        environment="production",
        version="v1",
        changes=[
            DeploymentChange(
                file_path="cache.py",
                change_type="modify",
                lines_changed=100,
                description="Database schema migration",
            )
        ],
        total_lines_changed=100,
    )

    assessment = RiskAssessment(
        risk_level="critical",
        risk_score=75.0,
        confidence_percent=40.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    assert policy.risk_score == 75.0
    assert policy.confidence_percent == 40.0
    assert policy.error_rate_threshold == 0.2  # strict threshold for critical
    assert len(policy.stages) >= 5  # many stages for slow rollout
    assert policy.stages[0].traffic_percent == 5.0  # start very small


def test_canary_low_risk_high_confidence():
    """Low risk with high confidence should result in fast rollout."""
    context = DeploymentContext(
        deployment_id="canary-002",
        service_name="svc",
        environment="staging",
        version="v1",
        changes=[
            DeploymentChange(
                file_path="logging.py",
                change_type="modify",
                lines_changed=20,
                description="Add logging statement",
            )
        ],
        total_lines_changed=20,
    )

    assessment = RiskAssessment(
        risk_level="low",
        risk_score=15.0,
        confidence_percent=92.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    assert policy.risk_score == 15.0
    assert policy.confidence_percent == 92.0
    assert policy.error_rate_threshold == 0.5  # relaxed threshold
    assert len(policy.stages) <= 3  # few stages for fast rollout
    assert policy.stages[-1].traffic_percent == 100.0  # end at 100%


def test_canary_stage_names():
    """Verify stage names are sensible."""
    context = DeploymentContext(
        deployment_id="canary-003",
        service_name="svc",
        environment="production",
        version="v1",
        changes=[],
        total_lines_changed=10,
    )

    assessment = RiskAssessment(
        risk_level="medium",
        risk_score=40.0,
        confidence_percent=75.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    # stages should have meaningful names
    stage_names = [s.name for s in policy.stages]
    assert all(name in ["smoke", "light", "half", "majority", "full"] for name in stage_names)
    assert stage_names[0] == "smoke"  # first is always smoke


def test_canary_next_stage():
    """Test advancing through canary stages."""
    context = DeploymentContext(
        deployment_id="canary-004",
        service_name="svc",
        environment="production",
        version="v1",
        changes=[],
        total_lines_changed=10,
    )

    assessment = RiskAssessment(
        risk_level="medium",
        risk_score=40.0,
        confidence_percent=75.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    # First call: advance to next stage
    result = orchestrator.next_stage(policy)
    assert result.ready_to_promote is False
    assert result.recommended_traffic_percent > 0

    # Simulate progressing through stages
    for _ in range(len(policy.stages) - 1):
        result = orchestrator.next_stage(policy)
        policy.current_stage += 1

    # Last stage should be ready to promote
    policy.current_stage = len(policy.stages) - 1
    result = orchestrator.next_stage(policy)
    assert result.ready_to_promote is True
    assert result.recommended_traffic_percent == 100.0


def test_canary_rollback_on_high_error_rate():
    """Test rollback triggered by high error rate."""
    context = DeploymentContext(
        deployment_id="canary-005",
        service_name="svc",
        environment="production",
        version="v1",
        changes=[],
        total_lines_changed=10,
    )

    assessment = RiskAssessment(
        risk_level="medium",
        risk_score=40.0,
        confidence_percent=75.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    # Simulate metrics that exceed threshold
    metrics = {
        "error_rate_percent": 1.5,  # exceeds policy threshold of 0.5
        "latency_ms": 100.0,
    }

    result = orchestrator.next_stage(policy, current_metrics=metrics)

    assert result.ready_to_promote is False
    assert result.recommended_traffic_percent == 0.0  # rollback
    assert "Error rate" in result.reason


def test_canary_cache_latency_strict():
    """Caching changes should have stricter latency guardrails."""
    context = DeploymentContext(
        deployment_id="canary-006",
        service_name="svc",
        environment="production",
        version="v1",
        changes=[
            DeploymentChange(
                file_path="cache.py",
                change_type="modify",
                lines_changed=50,
                description="Cache optimization",
            )
        ],
        total_lines_changed=50,
    )

    assessment = RiskAssessment(
        risk_level="medium",
        risk_score=40.0,
        confidence_percent=75.0,
    )

    orchestrator = CanaryOrchestrator()
    policy = orchestrator.generate_policy(context, assessment)

    # Cache changes should have stricter latency
    assert policy.latency_threshold_ms == 200.0
