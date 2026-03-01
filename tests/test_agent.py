from chaos_negotiator.models import DeploymentContext, DeploymentChange
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.predictors.history_store import DeploymentHistoryStore
from chaos_negotiator.predictors.ensemble import EnsembleRiskPredictor


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
    # ensemble predictor should append breakdown info
    assert "[Ensemble]" in contract.risk_summary or "[Ensemble]" in contract.reasoning


def test_agent_records_outcome(tmp_path):
    """Ensure the agent can log a deployment result into the history store."""
    context = DeploymentContext(
        deployment_id="test-004",
        service_name="svc",
        environment="staging",
        version="v0",
        changes=[
            DeploymentChange(
                file_path="x.py",
                change_type="modify",
                lines_changed=5,
                description="minor",
            )
        ],
        total_lines_changed=5,
    )

    # point the agent at a temp db so we can inspect it
    db_path = tmp_path / "hist.db"
    agent = ChaosNegotiatorAgent()
    agent.history_store = DeploymentHistoryStore(str(db_path))
    agent.risk_predictor = EnsembleRiskPredictor(history_store=agent.history_store)

    # simulate a deployment and record an outcome
    agent.process_deployment(context)
    agent.record_deployment_result(
        context,
        actual_error_rate_percent=0.02,
        actual_latency_change_percent=1.0,
        rollback_triggered=False,
    )

    # store should now contain exactly one row
    outcomes = agent.history_store.recent(10)
    assert len(outcomes) == 1
    assert outcomes[0].deployment_id == "test-004"


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
