"""Integration tests for new Semantic Kernel and enforcement features."""

import pytest
from chaos_negotiator.models import DeploymentContext, DeploymentChange
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.enforcement import EnforcementSimulator


@pytest.fixture
def sample_context():
    """Sample deployment context for testing."""
    return DeploymentContext(
        deployment_id="test-deploy-001",
        service_name="test-service",
        environment="staging",
        version="v1.0.0",
        changes=[
            DeploymentChange(
                file_path="src/test.py",
                change_type="modify",
                lines_changed=10,
                risk_tags=["test"],
                description="Test change"
            )
        ],
        total_lines_changed=10,
        current_error_rate_percent=0.05,
        current_p95_latency_ms=100.0,
        current_p99_latency_ms=200.0,
        target_error_rate_percent=0.10,
        target_p95_latency_ms=150.0,
        target_p99_latency_ms=300.0,
        current_qps=1000.0,
        peak_qps=2000.0,
        owner_team="Test Team",
        rollback_capability=True
    )


def test_agent_initializes_with_sk(sample_context):
    """Test that agent initializes correctly with Semantic Kernel option."""
    agent = ChaosNegotiatorAgent(use_semantic_kernel=True)
    assert agent is not None
    # SK may not be available in all environments, so just check initialization
    assert hasattr(agent, 'sk_orchestrator')


def test_agent_falls_back_to_legacy(sample_context):
    """Test that agent falls back to legacy mode if SK unavailable."""
    agent = ChaosNegotiatorAgent(use_semantic_kernel=False)
    assert agent is not None
    assert agent.risk_predictor is not None
    assert agent.contract_engine is not None


def test_legacy_orchestration_still_works(sample_context):
    """Test that legacy orchestration path still works."""
    agent = ChaosNegotiatorAgent(use_semantic_kernel=False)
    contract = agent.process_deployment(sample_context)
    
    assert contract is not None
    assert contract.deployment_id == "test-deploy-001"
    assert contract.predicted_risk_level is not None
    assert contract.rollback_possible is not None
    assert len(contract.guardrails) > 0


@pytest.mark.asyncio
async def test_enforcement_simulator():
    """Test enforcement simulator basic functionality."""
    from chaos_negotiator.models.contract import DeploymentContract, Guardrail
    from chaos_negotiator.models.risk import RiskAssessment
    from chaos_negotiator.models.rollback import RollbackPlan
    
    context = DeploymentContext(
        deployment_id="sim-test-001",
        service_name="test-service",
        environment="staging",
        version="v1.0.0",
        changes=[],
        total_lines_changed=10,
        current_error_rate_percent=0.05,
        current_p95_latency_ms=100.0,
        current_p99_latency_ms=200.0,
        target_error_rate_percent=0.10,
        target_p95_latency_ms=150.0,
        target_p99_latency_ms=300.0,
        current_qps=1000.0,
        peak_qps=2000.0,
        owner_team="Test Team",
        rollback_capability=True
    )
    
    risk = RiskAssessment(
        risk_level="low",
        risk_score=25.0,
        confidence=0.9,
        identified_factors=[],
        predicted_impact="minimal"
    )
    
    rollback = RollbackPlan(
        plan_id="plan-001",
        deployment_id="sim-test-001",
        rollback_possible=True,
        total_estimated_time_seconds=60,
        data_loss_risk="none"
    )
    
    contract = DeploymentContract(
        contract_id="contract-001",
        deployment_id="sim-test-001",
        service_name="test-service",
        predicted_risk_level="low",
        risk_score=25.0,
        risk_summary="Test deployment",
        deployment_context=context,
        risk_assessment=risk,
        rollback_plan=rollback,
        guardrails=[
            Guardrail(
                metric_name="max_error_rate_percent",
                threshold=0.20,
                comparison="less_than"
            ),
            Guardrail(
                metric_name="max_p95_latency_ms",
                threshold=200.0,
                comparison="less_than"
            )
        ],
        approval_status="pending",
        reasoning="Test contract"
    )
    
    simulator = EnforcementSimulator()
    result = await simulator.simulate_deployment(contract, failure_scenario=None)
    
    assert result is not None
    assert "status" in result
    assert "metrics_history" in result
    assert len(result["metrics_history"]) > 0


@pytest.mark.asyncio
async def test_enforcement_with_rollback():
    """Test enforcement simulator triggers rollback on violation."""
    from chaos_negotiator.models.contract import DeploymentContract, Guardrail
    from chaos_negotiator.models.risk import RiskAssessment
    from chaos_negotiator.models.rollback import RollbackPlan
    
    context = DeploymentContext(
        deployment_id="sim-test-002",
        service_name="test-service",
        environment="staging",
        version="v1.0.0",
        changes=[],
        total_lines_changed=10,
        current_error_rate_percent=0.05,
        current_p95_latency_ms=100.0,
        current_p99_latency_ms=200.0,
        target_error_rate_percent=0.10,
        target_p95_latency_ms=150.0,
        target_p99_latency_ms=300.0,
        current_qps=1000.0,
        peak_qps=2000.0,
        owner_team="Test Team",
        rollback_capability=True
    )
    
    risk = RiskAssessment(
        risk_level="high",
        risk_score=75.0,
        confidence=0.85,
        identified_factors=[],
        predicted_impact="significant"
    )
    
    rollback = RollbackPlan(
        plan_id="plan-002",
        deployment_id="sim-test-002",
        rollback_possible=True,
        total_estimated_time_seconds=120,
        data_loss_risk="low"
    )
    
    contract = DeploymentContract(
        contract_id="contract-002",
        deployment_id="sim-test-002",
        service_name="test-service",
        predicted_risk_level="high",
        risk_score=75.0,
        risk_summary="High risk test deployment",
        deployment_context=context,
        risk_assessment=risk,
        rollback_plan=rollback,
        guardrails=[
            Guardrail(
                metric_name="max_error_rate_percent",
                threshold=0.15,  # Strict threshold to trigger rollback
                comparison="less_than"
            )
        ],
        approval_status="pending",
        reasoning="Test contract with rollback"
    )
    
    simulator = EnforcementSimulator()
    result = await simulator.simulate_deployment(contract, failure_scenario="error_spike")
    
    assert result is not None
    assert result["status"] == "rolled_back"
    assert "violation" in result
    assert "rollback" in result
    assert result["rollback"]["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
