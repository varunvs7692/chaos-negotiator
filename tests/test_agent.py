from chaos_negotiator.models import DeploymentContext, DeploymentChange
from chaos_negotiator.agent import ChaosNegotiatorAgent


def test_risk_prediction():
    """Test basic risk prediction."""
    context = DeploymentContext(
        deployment_id="test-001",
        service_name="test-service",
        environment="staging",
        version="v1.0.0",
        changes=[
            DeploymentChange(
                file_path="src/cache.py",
                change_type="modify",
                lines_changed=50,
                risk_tags=["caching"],
                description="Modify cache TTL logic",
            )
        ],
        total_lines_changed=50,
    )

    agent = ChaosNegotiatorAgent()
    contract = agent.process_deployment(context)

    assert contract.deployment_id == context.deployment_id
    assert contract.predicted_risk_level in ["low", "medium", "high", "critical"]
    assert contract.risk_score >= 0 and contract.risk_score <= 100
    assert len(contract.guardrails) > 0
    assert len(contract.validators) > 0


def test_contract_drafting():
    """Test contract generation."""
    context = DeploymentContext(
        deployment_id="test-002",
        service_name="user-service",
        environment="production",
        version="v2.0.0",
        changes=[
            DeploymentChange(
                file_path="src/database/schema.py",
                change_type="modify",
                lines_changed=100,
                description="Database schema migration",
            )
        ],
        total_lines_changed=100,
        rollback_capability=True,
    )

    agent = ChaosNegotiatorAgent()
    contract = agent.process_deployment(context)

    assert contract.status == "draft"
    assert contract.rollback_possible
    assert any(v.validator_type == "rollback_plan" for v in contract.validators)


def test_guardrails_based_on_risk():
    """Test that guardrails scale with risk level."""
    context = DeploymentContext(
        deployment_id="test-003",
        service_name="critical-service",
        environment="production",
        version="v1.5.0",
        changes=[
            DeploymentChange(
                file_path="src/cache.py",
                change_type="modify",
                lines_changed=200,
                description="Major caching and database changes",
            )
        ],
        total_lines_changed=200,
    )

    agent = ChaosNegotiatorAgent()
    contract = agent.process_deployment(context)

    # High risk should have stricter guardrails
    if contract.predicted_risk_level in ["high", "critical"]:
        error_rate_guardrail = next(
            (g for g in contract.guardrails if g.guardrail_type.value == "error_rate"), None
        )
        assert error_rate_guardrail is not None
        assert error_rate_guardrail.max_value <= 0.3  # Stricter threshold
