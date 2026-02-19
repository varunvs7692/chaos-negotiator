"""Risk predictor module."""

from typing import Any

from chaos_negotiator.models import DeploymentContext, RiskAssessment, RiskFactor


class RiskPredictor:
    """Predicts SLO impact and deployment risk."""

    def __init__(self) -> None:
        self.risk_patterns = self._init_patterns()

    def _init_patterns(self) -> dict[str, dict[str, Any]]:
        """Initialize known risk patterns."""
        return {
            "caching": {
                "keywords": ["cache", "ttl", "redis", "memcached"],
                "risk_factor": RiskFactor.CACHING_CHANGES,
                "latency_increase": 5.0,  # percent
            },
            "database": {
                "keywords": ["schema", "migration", "database", "sql"],
                "risk_factor": RiskFactor.DATABASE_SCHEMA,
                "latency_increase": 15.0,
                "error_increase": 2.0,
            },
            "api": {
                "keywords": ["api", "contract", "endpoint", "request", "response"],
                "risk_factor": RiskFactor.API_CONTRACT,
                "latency_increase": 8.0,
                "error_increase": 1.5,
            },
            "traffic": {
                "keywords": ["load", "traffic", "rampup", "connection"],
                "risk_factor": RiskFactor.TRAFFIC_PATTERN,
                "latency_increase": 20.0,
            },
        }

    def predict(self, context: DeploymentContext) -> RiskAssessment:
        """Predict risk for a deployment."""
        risk_assessment = RiskAssessment(
            risk_level="low",
            risk_score=0.0,
            identified_factors=[],
            predicted_error_rate_increase_percent=0.0,
            predicted_p95_latency_increase_percent=0.0,
        )

        # Analyze changes
        for change in context.changes:
            description_lower = change.description.lower()
            for pattern_name, pattern in self.risk_patterns.items():
                for keyword in pattern["keywords"]:
                    if keyword in description_lower:
                        risk_assessment.identified_factors.append(pattern["risk_factor"])
                        risk_assessment.predicted_p95_latency_increase_percent += pattern.get(
                            "latency_increase", 0
                        )
                        risk_assessment.predicted_error_rate_increase_percent += pattern.get(
                            "error_increase", 0
                        )

        # Calculate risk score (0-100)
        base_score: float = len(context.changes) * 2.0  # 2 points per change
        base_score += len(risk_assessment.identified_factors) * 15
        base_score += min(context.total_lines_changed / 10, 20)  # Up to 20 points for size

        risk_assessment.risk_score = min(base_score, 100.0)

        # Determine risk level
        if risk_assessment.risk_score >= 70:
            risk_assessment.risk_level = "critical"
        elif risk_assessment.risk_score >= 50:
            risk_assessment.risk_level = "high"
        elif risk_assessment.risk_score >= 30:
            risk_assessment.risk_level = "medium"
        else:
            risk_assessment.risk_level = "low"

        # Calculate affected users
        traffic_ratio = context.current_qps / max(context.peak_qps, 1)
        estimated_affected = int(context.current_qps * 100 * traffic_ratio)
        risk_assessment.affected_users_estimated = estimated_affected

        # Set confidence based on factor count
        risk_assessment.confidence_percent = min(
            50 + len(risk_assessment.identified_factors) * 10, 95
        )

        # Generate reasoning
        risk_assessment.reasoning = self._generate_reasoning(risk_assessment, context)

        return risk_assessment

    def _generate_reasoning(self, assessment: RiskAssessment, context: DeploymentContext) -> str:
        """Generate human-readable reasoning."""
        lines = [
            f"Risk Level: {assessment.risk_level.upper()} (Score: {assessment.risk_score:.1f}/100)"
        ]

        if assessment.identified_factors:
            lines.append(
                f"Risk Factors: {', '.join(str(f.value) for f in assessment.identified_factors)}"
            )

        if assessment.predicted_p95_latency_increase_percent > 0:
            lines.append(
                f"Predicted P95 Latency Increase: +{assessment.predicted_p95_latency_increase_percent:.1f}%"
            )

        if assessment.predicted_error_rate_increase_percent > 0:
            lines.append(
                f"Predicted Error Rate Increase: +{assessment.predicted_error_rate_increase_percent:.1f}%"
            )

        if assessment.affected_users_estimated > 0:
            lines.append(f"Estimated Affected Users: {assessment.affected_users_estimated:,}")

        lines.append(f"Analysis Confidence: {assessment.confidence_percent:.0f}%")

        return "\n".join(lines)
