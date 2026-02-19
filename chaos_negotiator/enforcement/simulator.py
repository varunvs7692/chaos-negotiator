"""
Deployment Enforcement Simulator for Demo.

Simulates real-time deployment with metric collection,
guardrail enforcement, and automatic rollback.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any,List, Optional
from dataclasses import dataclass

from chaos_negotiator.models.contract import DeploymentContract, Guardrail
from chaos_negotiator.mcp.azure_mcp import AzureMCPClient

logger = logging.getLogger(__name__)


@dataclass
class SimulatedMetrics:
    """Metrics at a point in time during deployment."""
    timestamp: datetime
    error_rate_percent: float
    p95_latency_ms: float
    p99_latency_ms: float
    qps: float
    traffic_percentage: float


class EnforcementSimulator:
    """
    Simulates deployment enforcement for demo purposes.
    
    Shows:
    - Gradual traffic ramp (canary deployment)
    - Real-time metric collection
    - Guardrail checking
    - Automatic rollback on violation
    """

    def __init__(self, mcp_client: Optional[AzureMCPClient] = None):
        """Initialize simulator with optional Azure MCP client."""
        self.mcp_client = mcp_client or AzureMCPClient()
        
    async def simulate_deployment(
        self,
        contract: DeploymentContract,
        failure_scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate a deployment with enforcement.
        
        Args:
            contract: Deployment contract with guardrails
            failure_scenario: Optional scenario to trigger (None, "error_spike", "latency_spike")
            
        Returns:
            Simulation results with metrics history and final status
        """
        # Handle both legacy and new contract structures
        deployment_id = (
            contract.deployment_context.deployment_id 
            if contract.deployment_context 
            else contract.deployment_id
        )
        
        logger.info(f"Starting deployment simulation for {deployment_id}")
        logger.info(f"Failure scenario: {failure_scenario or 'none (successful)'}")
        
        traffic_phases = [5, 25, 50, 100]  # Canary traffic percentages
        
        metrics_history: List[SimulatedMetrics] = []
        violations: List[Dict[str, Any]] = []
        
        # Extract guardrail thresholds - handle both Guardrail and GuardrailRequirement
        guardrails_dict = {}
        for g in contract.guardrails:
            if hasattr(g, 'metric_name'):
                # New Guardrail format
                guardrails_dict[g.metric_name] = g
            elif hasattr(g, 'guardrail_type'):
                # Legacy GuardrailRequirement format - convert to Guardrail-like
                metric_name = f"max_{g.guardrail_type.value}_percent" if "rate" in g.guardrail_type.value else f"max_{g.guardrail_type.value}_ms"
                guardrails_dict[metric_name] = type('obj', (object,), {
                    'metric_name': metric_name,
                    'threshold': g.max_value,
                    'comparison': 'less_than'
                })()
        
        max_error_rate = (
            guardrails_dict.get("max_error_rate_percent").threshold
            if "max_error_rate_percent" in guardrails_dict
            else 0.5
        )
        max_p95_latency = (
            guardrails_dict.get("max_p95_latency_ms").threshold 
            if "max_p95_latency_ms" in guardrails_dict 
            else guardrails_dict.get("max_latency_p95_ms").threshold
            if "max_latency_p95_ms" in guardrails_dict
            else 300.0
        )
        
        # Baseline metrics (from deployment_context or use defaults)
        if contract.deployment_context:
            baseline = contract.deployment_context
            current_error_rate = baseline.current_error_rate_percent
            current_latency = baseline.current_p95_latency_ms
        else:
            # Legacy contract structure - use safe defaults
            current_error_rate = 0.05
            current_latency = 100.0
        
        for phase_idx, traffic_pct in enumerate(traffic_phases):
            logger.info(f"Phase {phase_idx + 1}: Ramping to {traffic_pct}% traffic")
            
            # Simulate metric evolution during this phase
            for check in range(3):  # 3 checks per phase
                await asyncio.sleep(0.5)  # Simulate time passing
                
                # Generate metrics with optional failure injection
                metrics = self._generate_metrics(
                    baseline_error=current_error_rate,
                    baseline_latency=current_latency,
                    traffic_pct=traffic_pct,
                    phase=phase_idx,
                    check=check,
                    failure_scenario=failure_scenario
                )
                
                metrics_history.append(metrics)
                
                logger.info(
                    f"  Check {check + 1}: Error={metrics.error_rate_percent:.3f}%, "
                    f"P95={metrics.p95_latency_ms:.1f}ms @ {traffic_pct}% traffic"
                )
                
                # Check guardrails
                violation = self._check_guardrails(
                    metrics,
                    max_error_rate,
                    max_p95_latency
                )
                
                if violation:
                    violations.append(violation)
                    logger.warning(f"⚠️  GUARDRAIL VIOLATION: {violation['metric']}")
                    logger.warning(f"   Actual: {violation['actual']}, Threshold: {violation['threshold']}")
                    
                    # Trigger rollback
                    logger.error("🔴 Triggering automatic rollback...")
                    rollback_result = await self._execute_rollback(contract)
                    
                    return {
                        "status": "rolled_back",
                        "reason": "guardrail_violation",
                        "violation": violation,
                        "metrics_history": [self._metrics_to_dict(m) for m in metrics_history],
                        "traffic_reached": traffic_pct,
                        "rollback": rollback_result,
                        "deployment_id": deployment_id
                    }
        
        # All phases completed successfully
        logger.info("✅ Deployment completed successfully - all guardrails met")
        
        return {
            "status": "success",
            "reason": "all_guardrails_met",
            "metrics_history": [self._metrics_to_dict(m) for m in metrics_history],
            "traffic_reached": 100,
            "violations": [],
            "deployment_id": deployment_id
        }

    def _generate_metrics(
        self,
        baseline_error: float,
        baseline_latency: float,
        traffic_pct: float,
        phase: int,
        check: int,
        failure_scenario: Optional[str]
    ) -> SimulatedMetrics:
        """Generate simulated metrics for a deployment phase."""
        
        # Base noise
        error_noise = random.uniform(-0.01, 0.02)
        latency_noise = random.uniform(-5, 10)
        
        # Traffic impact (higher traffic = slight degradation)
        traffic_factor = 1.0 + (traffic_pct / 500.0)  # Up to 20% increase at 100%
        
        error_rate = baseline_error + error_noise
        p95_latency = baseline_latency * traffic_factor + latency_noise
        
        # Inject failure scenarios
        if failure_scenario == "error_spike" and phase >= 2:
            # Error spike at 50%+ traffic
            error_rate += 0.3 * (traffic_pct / 100.0)
        elif failure_scenario == "latency_spike" and phase >= 2:
            # Latency spike at 50%+ traffic
            p95_latency += 100 * (traffic_pct / 100.0)
        
        return SimulatedMetrics(
            timestamp=datetime.utcnow(),
            error_rate_percent=max(0.0, error_rate),
            p95_latency_ms=max(10.0, p95_latency),
            p99_latency_ms=max(20.0, p95_latency * 2.2),
            qps=5000.0 * (traffic_pct / 100.0),
            traffic_percentage=traffic_pct
        )

    def _check_guardrails(
        self,
        metrics: SimulatedMetrics,
        max_error_rate: float,
        max_p95_latency: float
    ) -> Optional[Dict[str, Any]]:
        """Check if metrics violate guardrails."""
        
        if metrics.error_rate_percent > max_error_rate:
            return {
                "metric": "error_rate_percent",
                "actual": metrics.error_rate_percent,
                "threshold": max_error_rate,
                "timestamp": metrics.timestamp.isoformat(),
                "traffic_percentage": metrics.traffic_percentage
            }
        
        if metrics.p95_latency_ms > max_p95_latency:
            return {
                "metric": "p95_latency_ms",
                "actual": metrics.p95_latency_ms,
                "threshold": max_p95_latency,
                "timestamp": metrics.timestamp.isoformat(),
                "traffic_percentage": metrics.traffic_percentage
            }
        
        return None

    async def _execute_rollback(
        self,
        contract: DeploymentContract
    ) -> Dict[str, Any]:
        """Simulate rollback execution."""
        rollback_plan = contract.rollback_plan
        
        if not rollback_plan or not rollback_plan.rollback_possible:
            logger.warning("Rollback not possible - no rollback plan available!")
            return {
                "status": "failed",
                "time_seconds": 0,
                "steps_executed": 0,
                "data_loss_risk": "unknown",
                "error": "Rollback plan not available"
            }
        
        logger.info(f"Executing rollback procedure:")
        steps = rollback_plan.steps if rollback_plan.steps else []
        for idx, step in enumerate(steps):
            logger.info(f"  Step {idx + 1}: {step.description if hasattr(step, 'description') else step}")
            await asyncio.sleep(0.3)  # Simulate execution time
        
        estimated_time = rollback_plan.total_estimated_time_seconds
        logger.info(f"Rollback completed in ~{estimated_time} seconds")
        
        return {
            "status": "completed",
            "time_seconds": estimated_time,
            "steps_executed": len(steps),
            "data_loss_risk": rollback_plan.data_loss_risk
        }

    def _metrics_to_dict(self, metrics: SimulatedMetrics) -> Dict[str, Any]:
        """Convert SimulatedMetrics to dictionary."""
        return {
            "timestamp": metrics.timestamp.isoformat(),
            "error_rate_percent": round(metrics.error_rate_percent, 4),
            "p95_latency_ms": round(metrics.p95_latency_ms, 2),
            "p99_latency_ms": round(metrics.p99_latency_ms, 2),
            "qps": round(metrics.qps, 2),
            "traffic_percentage": metrics.traffic_percentage
        }


async def run_enforcement_demo(
    contract: DeploymentContract,
    scenario: str = "success"
) -> Dict[str, Any]:
    """
    Run enforcement demo with specified scenario.
    
    Args:
        contract: Deployment contract to enforce
        scenario: One of "success", "error_spike", "latency_spike"
        
    Returns:
        Simulation results
    """
    simulator = EnforcementSimulator()
    
    failure_map = {
        "success": None,
        "error_spike": "error_spike",
        "latency_spike": "latency_spike"
    }
    
    failure_scenario = failure_map.get(scenario)
    
    # Get deployment ID from either new or legacy contract structure
    deployment_id = (
        contract.deployment_context.deployment_id 
        if contract.deployment_context 
        else contract.deployment_id
    )
    
    print(f"\n{'='*60}")
    print(f"DEPLOYMENT ENFORCEMENT SIMULATION")
    print(f"{'='*60}")
    print(f"Deployment ID: {deployment_id}")
    print(f"Scenario: {scenario}")
    print(f"Guardrails: {len(contract.guardrails)}")
    print(f"{'='*60}\n")
    
    result = await simulator.simulate_deployment(contract, failure_scenario)
    
    print(f"\n{'='*60}")
    print(f"SIMULATION RESULT: {result['status'].upper()}")
    print(f"{'='*60}")
    print(f"Traffic reached: {result['traffic_reached']}%")
    print(f"Metrics collected: {len(result['metrics_history'])} data points")
    
    if result['status'] == 'rolled_back':
        print(f"\n🔴 ROLLBACK TRIGGERED")
        print(f"Reason: {result['violation']['metric']} exceeded threshold")
        print(f"Actual: {result['violation']['actual']:.3f}")
        print(f"Threshold: {result['violation']['threshold']:.3f}")
        print(f"Rollback time: ~{result['rollback']['time_seconds']}s")
    else:
        print(f"\n✅ DEPLOYMENT SUCCESSFUL")
        print(f"All guardrails met throughout deployment")
    
    print(f"{'='*60}\n")
    
    return result
