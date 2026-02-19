"""Rollback plan validator module."""

from chaos_negotiator.models import DeploymentContext, RollbackPlan, RollbackStep, RiskAssessment


class RollbackValidator:
    """Validates and generates rollback plans."""

    def validate_and_create(
        self, context: DeploymentContext, risk_assessment: RiskAssessment
    ) -> RollbackPlan:
        """Create a rollback plan for the deployment."""
        plan = RollbackPlan(
            plan_id=f"rollback-{context.deployment_id}",
            deployment_id=context.deployment_id,
            rollback_possible=context.rollback_capability,
        )

        if not context.rollback_capability:
            plan.reasoning = "Rollback not possible - no rollback capability configured"
            return plan

        # Check if there's actual risk to mitigate
        if risk_assessment.risk_level == "low":
            plan.rollback_possible = False
            plan.reasoning = "Low risk deployment - no rollback plan required"
            return plan

        # Build rollback steps
        plan.steps = self._generate_steps(context)
        plan.total_estimated_time_seconds = sum(
            step.estimated_duration_seconds for step in plan.steps
        )
        plan.rollback_steps_count = len(plan.steps)
        plan.rollback_window_seconds = min(max(plan.total_estimated_time_seconds * 2, 300), 1800)

        # Assess data loss risk
        plan.data_loss_risk = "none"  # Default
        for change in context.changes:
            if "delete" in change.change_type.lower():
                plan.data_loss_risk = "medium"
            if "database" in change.description.lower() or "schema" in change.description.lower():
                if plan.data_loss_risk == "none":
                    plan.data_loss_risk = "low"

        # Assess service disruption
        plan.service_disruption_expected = len(plan.steps) > 5
        if plan.service_disruption_expected:
            plan.disruption_window_seconds = sum(
                s.estimated_duration_seconds for s in plan.steps[:3]
            )

        plan.reasoning = self._generate_reasoning(plan, context)
        return plan

    def _generate_steps(self, context: DeploymentContext) -> list[RollbackStep]:
        """Generate rollback steps."""
        steps = [
            RollbackStep(
                step_number=1,
                description="Trigger rollback signal to deployment orchestrator",
                command="kubectl rollout undo deployment/user-service",
                estimated_duration_seconds=30,
                validation_method="kubernetes_status",
            ),
            RollbackStep(
                step_number=2,
                description="Wait for previous version to become healthy",
                command="kubectl rollout status deployment/user-service --timeout=5m",
                estimated_duration_seconds=60,
                validation_method="health_check",
                dependencies=[1],
            ),
            RollbackStep(
                step_number=3,
                description="Verify service endpoints are responding",
                command="healthcheck-service user-service",
                estimated_duration_seconds=15,
                validation_method="metric_monitor",
                dependencies=[2],
            ),
            RollbackStep(
                step_number=4,
                description="Clear distributed caches if applicable",
                command="cache-flush --service=user-service",
                estimated_duration_seconds=10,
                validation_method="metric_monitor",
                dependencies=[3],
            ),
        ]

        # Add database-specific steps if needed
        if any("database" in change.description.lower() for change in context.changes):
            steps.append(
                RollbackStep(
                    step_number=5,
                    description="Re-run migration rollback if needed",
                    command="flyway undo",
                    estimated_duration_seconds=120,
                    validation_method="manual",
                    dependencies=[4],
                )
            )

        return steps

    def _generate_reasoning(self, plan: RollbackPlan, context: DeploymentContext) -> str:
        """Generate human-readable reasoning."""
        lines = [
            f"Rollback Possible: {plan.rollback_possible}",
            f"Estimated Rollback Time: {plan.total_estimated_time_seconds}s",
            f"Rollback Window: {plan.rollback_window_seconds}s",
            f"Data Loss Risk: {plan.data_loss_risk}",
        ]

        if plan.steps:
            lines.append(f"Rollback Steps: {len(plan.steps)}")
            for step in plan.steps:
                lines.append(f"  - Step {step.step_number}: {step.description}")

        if plan.service_disruption_expected:
            lines.append(f"Expected Service Disruption: ~{plan.disruption_window_seconds}s")

        return "\n".join(lines)
