"""Canary orchestration engine."""

from __future__ import annotations

from chaos_negotiator.canary.models import CanaryPolicy, CanaryStage, CanaryResult
from chaos_negotiator.models import DeploymentContext, RiskAssessment


class CanaryOrchestrator:
    """Orchestrates canary rollout strategy based on risk and confidence.

    The core insight: high-confidence predictions allow faster rollouts,
    while low-confidence ones require slower, more cautious progression.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        pass

    def generate_policy(
        self, context: DeploymentContext, assessment: RiskAssessment
    ) -> CanaryPolicy:
        """Generate a canary rollout policy from risk and confidence.

        Args:
            context: deployment context
            assessment: risk assessment with confidence

        Returns:
            CanaryPolicy with tailored stages
        """
        risk = assessment.risk_score
        confidence = assessment.confidence_percent

        # Stage design: risk determines caution, confidence determines speed
        policy = CanaryPolicy(
            deployment_id=context.deployment_id,
            risk_score=risk,
            confidence_percent=confidence,
        )

        # Error rate guardrail: stricter for higher risk
        if risk >= 70:
            policy.error_rate_threshold = 0.2
        elif risk >= 50:
            policy.error_rate_threshold = 0.3
        else:
            policy.error_rate_threshold = 0.5

        # Latency guardrail: stricter for caching/perf-sensitive changes
        if any("cache" in c.description.lower() for c in context.changes):
            policy.latency_threshold_ms = 200.0
        else:
            policy.latency_threshold_ms = 500.0

        # Generate stages: confidence allows faster progression
        stages = self._generate_stages(risk, confidence)
        policy.stages = stages

        return policy

    def _generate_stages(self, risk: float, confidence: float) -> list[CanaryStage]:
        """Generate rollout stages tuned to risk and confidence.

        High confidence + low risk → fast rollout (fewer stages).
        Low confidence + high risk → slow rollout (many stages).
        """
        stages: list[CanaryStage] = []

        # Base stage durations (in seconds)
        base_duration = 300  # 5 minutes

        # Adjust duration based on risk and confidence
        if risk >= 70:
            # Critical: slow and careful
            duration_multiplier = 2.0
            traffic_increments = [5, 10, 25, 50, 100]
        elif risk >= 50:
            # High: moderately cautious
            if confidence >= 80:
                # High confidence → slightly faster
                duration_multiplier = 1.2
                traffic_increments = [10, 25, 50, 100]
            else:
                # Low confidence → slower
                duration_multiplier = 1.8
                traffic_increments = [5, 15, 30, 60, 100]
        else:
            # Medium/Low risk
            if confidence >= 85:
                # Very confident → fast
                duration_multiplier = 0.8
                traffic_increments = [25, 50, 100]
            elif confidence >= 70:
                # Moderately confident → normal
                duration_multiplier = 1.0
                traffic_increments = [10, 25, 50, 100]
            else:
                # Low confidence → slow
                duration_multiplier = 1.5
                traffic_increments = [5, 15, 35, 70, 100]

        duration = int(base_duration * duration_multiplier)

        for idx, traffic in enumerate(traffic_increments):
            stage_name = self._name_stage(traffic)
            stages.append(
                CanaryStage(
                    stage_number=idx,
                    traffic_percent=float(traffic),
                    duration_seconds=duration,
                    name=stage_name,
                )
            )

        return stages

    def _name_stage(self, traffic_percent: float) -> str:
        """Human‑readable stage name."""
        if traffic_percent <= 10:
            return "smoke"
        elif traffic_percent <= 25:
            return "light"
        elif traffic_percent <= 50:
            return "half"
        elif traffic_percent <= 75:
            return "majority"
        else:
            return "full"

    def next_stage(
        self,
        policy: CanaryPolicy,
        current_metrics: dict | None = None,
    ) -> CanaryResult:
        """Recommend the next stage or promotion.

        Args:
            policy: current canary policy
            current_metrics: optional actual metrics (error_rate, latency)

        Returns:
            CanaryResult with recommendation
        """
        if policy.completed:
            return CanaryResult(
                deployment_id=policy.deployment_id,
                recommended_traffic_percent=100.0,
                reason="Canary already completed; ready for 100% rollout.",
                ready_to_promote=True,
            )

        # Check if we should rollback
        if current_metrics and policy.rollback_on_violation:
            error_rate = current_metrics.get("error_rate_percent", 0.0)
            latency = current_metrics.get("latency_ms", 0.0)

            if error_rate > policy.error_rate_threshold:
                return CanaryResult(
                    deployment_id=policy.deployment_id,
                    recommended_traffic_percent=0.0,
                    reason=f"Error rate {error_rate:.2f}% exceeds threshold {policy.error_rate_threshold:.2f}%",
                    ready_to_promote=False,
                )

            if latency > policy.latency_threshold_ms:
                return CanaryResult(
                    deployment_id=policy.deployment_id,
                    recommended_traffic_percent=0.0,
                    reason=f"Latency {latency:.0f}ms exceeds threshold {policy.latency_threshold_ms:.0f}ms",
                    ready_to_promote=False,
                )

        # Advance to next stage
        if policy.current_stage < len(policy.stages) - 1:
            next_stage = policy.stages[policy.current_stage + 1]
            reason = f"Advancing to stage {next_stage.stage_number} ({next_stage.name}): {next_stage.traffic_percent:.0f}% traffic"
            return CanaryResult(
                deployment_id=policy.deployment_id,
                recommended_traffic_percent=next_stage.traffic_percent,
                reason=reason,
                ready_to_promote=False,
            )

        # All stages complete
        policy.completed = True
        return CanaryResult(
            deployment_id=policy.deployment_id,
            recommended_traffic_percent=100.0,
            reason="All canary stages passed; ready for full rollout.",
            ready_to_promote=True,
        )
