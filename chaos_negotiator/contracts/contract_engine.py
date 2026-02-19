"""Contract engine - auto-drafts and negotiates deployment contracts."""

from chaos_negotiator.models import (
    DeploymentContext,
    DeploymentContract,
    Guardrail,
    GuardrailRequirement,
    GuardrailType,
    ValidatorRequirement,
    RiskAssessment,
    RollbackPlan,
)


class ContractEngine:
    """Engine that drafts and manages deployment contracts."""

    def draft_contract(
        self,
        context: DeploymentContext,
        risk_assessment: RiskAssessment,
        rollback_plan: RollbackPlan,
    ) -> DeploymentContract:
        """Draft a deployment contract."""
        contract = DeploymentContract(
            contract_id=f"contract-{context.deployment_id}",
            deployment_id=context.deployment_id,
            service_name=context.service_name,
            predicted_risk_level=risk_assessment.risk_level,
            risk_score=risk_assessment.risk_score,
            risk_summary=risk_assessment.reasoning or risk_assessment.risk_level,
            rollback_possible=rollback_plan.rollback_possible,
            rollback_window_seconds=rollback_plan.rollback_window_seconds,
            rollback_steps_count=rollback_plan.rollback_steps_count,
        )

        # Build guardrails based on risk level
        contract.guardrails = self._build_guardrails(context, risk_assessment)

        # Build validator requirements
        contract.validators = self._build_validators(context, risk_assessment, rollback_plan)

        # Suggest fixes if needed
        contract.suggested_fixes = self._suggest_fixes(context, risk_assessment, rollback_plan)

        # Generate detailed reasoning
        contract.reasoning = self._generate_reasoning(contract, risk_assessment, rollback_plan)

        return contract

    def _build_guardrails(
        self, context: DeploymentContext, risk: RiskAssessment
    ) -> list[GuardrailRequirement | Guardrail]:
        """Build guardrails based on risk assessment."""
        guardrails: list[GuardrailRequirement | Guardrail] = []

        # Error rate guardrail (stricter for higher risk)
        if risk.risk_level == "critical":
            error_rate_threshold = 0.2  # 0.2%
        elif risk.risk_level == "high":
            error_rate_threshold = 0.3  # 0.3%
        else:
            error_rate_threshold = 0.5  # 0.5%

        guardrails.append(
            GuardrailRequirement(
                guardrail_type=GuardrailType.ERROR_RATE,
                max_value=error_rate_threshold,
                unit="%",
                description=f"Error rate must stay below {error_rate_threshold}%",
                enforcement_window_seconds=300,
            )
        )

        # Latency guardrails
        base_p95 = context.target_p95_latency_ms
        canary_increase_percent = min(risk.predicted_p95_latency_increase_percent, 50)
        p95_threshold = base_p95 * (1 + canary_increase_percent / 100)

        guardrails.append(
            GuardrailRequirement(
                guardrail_type=GuardrailType.LATENCY_P95,
                max_value=p95_threshold,
                unit="ms",
                description=f"P95 latency must stay below {p95_threshold:.0f}ms",
                enforcement_window_seconds=300,
            )
        )

        p99_threshold = context.target_p99_latency_ms * 1.25
        guardrails.append(
            GuardrailRequirement(
                guardrail_type=GuardrailType.LATENCY_P99,
                max_value=p99_threshold,
                unit="ms",
                description=f"P99 latency must stay below {p99_threshold:.0f}ms",
                enforcement_window_seconds=300,
            )
        )

        # Traffic ramp guardrail for high-risk changes
        if risk.risk_level in ["critical", "high"]:
            guardrails.append(
                GuardrailRequirement(
                    guardrail_type=GuardrailType.TRAFFIC_RAMP,
                    max_value=10.0,  # Start at 10%
                    unit="%",
                    description="Canary traffic cap at 10% for initial phase",
                    enforcement_window_seconds=600,
                )
            )

        return guardrails

    def _build_validators(
        self,
        context: DeploymentContext,
        risk: RiskAssessment,
        rollback_plan: RollbackPlan,
    ) -> list[ValidatorRequirement]:
        """Build validator requirements."""
        validators = []

        # Always require tests
        validators.append(
            ValidatorRequirement(
                validator_type="test",
                required=True,
                description="Unit and integration tests must pass",
            )
        )

        # Canary for high/critical risk
        if risk.risk_level in ["critical", "high"]:
            validators.append(
                ValidatorRequirement(
                    validator_type="canary",
                    required=True,
                    description="Canary deployment required (start at 5-10% traffic)",
                    estimated_duration_seconds=600,
                )
            )

        # Rollback plan requirement for medium+ risk
        if risk.risk_level in ["critical", "high", "medium"]:
            if rollback_plan.rollback_possible:
                validators.append(
                    ValidatorRequirement(
                        validator_type="rollback_plan",
                        required=True,
                        description="Tested rollback procedure required",
                    )
                )
            else:
                validators.append(
                    ValidatorRequirement(
                        validator_type="rollback_plan",
                        required=False,
                        description="Rollback plan not available - suggest implementing",
                    )
                )

        # Feature flag for database changes
        if any("database" in c.description.lower() for c in context.changes):
            validators.append(
                ValidatorRequirement(
                    validator_type="feature_flag",
                    required=True,
                    description="Database changes require feature flag for safe rollback",
                )
            )

        return validators

    def _suggest_fixes(
        self,
        context: DeploymentContext,
        risk: RiskAssessment,
        rollback_plan: RollbackPlan,
    ) -> list[str]:
        """Suggest fixes to improve deployment safety."""
        suggestions = []

        if risk.risk_level == "critical":
            suggestions.append("High risk deployment - consider breaking changes into smaller PRs")
            suggestions.append("Add feature flags to make changes independently togglable")

        if not rollback_plan.rollback_possible and risk.risk_level != "low":
            suggestions.append(
                "Implement automated rollback capability using deployment orchestration"
            )
            suggestions.append("Add database migration versioning for safe schema rollovers")

        if any("dependencies" in c.description.lower() for c in context.changes):
            suggestions.append("Dependency updates detected - ensure backward compatibility")
            suggestions.append("Run security scan on new dependency versions")

        if risk.confidence_percent < 60:
            suggestions.append(
                "Low confidence in risk prediction - add more context in PR description"
            )

        return suggestions

    def _generate_reasoning(
        self,
        contract: DeploymentContract,
        risk: RiskAssessment,
        rollback_plan: RollbackPlan,
    ) -> str:
        """Generate detailed contract reasoning."""
        lines = [
            "=" * 60,
            "DEPLOYMENT CONTRACT",
            "=" * 60,
            "",
            "RISK ASSESSMENT:",
            f"  Level: {risk.risk_level.upper()}",
            f"  Score: {risk.risk_score:.1f}/100",
            f"  Confidence: {risk.confidence_percent:.0f}%",
            "",
            "GUARDRAILS (SLO PROTECTION):",
        ]

        for guardrail in contract.guardrails:
            if isinstance(guardrail, GuardrailRequirement):
                lines.append(
                    f"  - {guardrail.guardrail_type.value}: < {guardrail.max_value} {guardrail.unit}"
                )
            else:
                lines.append(
                    f"  - {guardrail.metric_name}: {guardrail.comparison} {guardrail.threshold}"
                )

        lines.append("")
        lines.append("VALIDATORS (PROOF REQUIRED):")
        for validator in contract.validators:
            req_str = "REQUIRED" if validator.required else "RECOMMENDED"
            lines.append(f"  - {validator.validator_type}: {req_str}")
            lines.append(f"    {validator.description}")

        lines.append("")
        lines.append("ROLLBACK CAPABILITY:")
        lines.append(f"  Possible: {rollback_plan.rollback_possible}")
        lines.append(f"  Window: {rollback_plan.rollback_window_seconds}s")
        lines.append(f"  Steps: {rollback_plan.rollback_steps_count}")

        if contract.suggested_fixes:
            lines.append("")
            lines.append("SUGGESTED IMPROVEMENTS:")
            for fix in contract.suggested_fixes:
                lines.append(f"  - {fix}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
