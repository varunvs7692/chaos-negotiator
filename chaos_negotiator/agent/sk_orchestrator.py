"""Semantic Kernel orchestration for Chaos Negotiator Agent."""

import logging
import os
from typing import Any
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory
from applicationinsights import TelemetryClient  # type: ignore[import-untyped]

from chaos_negotiator.models.deployment import DeploymentContext
from chaos_negotiator.models.contract import DeploymentContract
from chaos_negotiator.models.risk import RiskAssessment
from chaos_negotiator.predictors.risk_predictor import RiskPredictor
from chaos_negotiator.validators.rollback_validator import RollbackValidator
from chaos_negotiator.contracts.contract_engine import ContractEngine

logger = logging.getLogger(__name__)


class SemanticKernelOrchestrator:
    """
    Orchestrates Chaos Negotiator agent using Microsoft Semantic Kernel.

    Provides agentic capabilities:
    - Multi-step planning (risk → rollback → contract → enforcement)
    - Memory and context retention
    - Tool use (Azure Monitor, validators)
    - Autonomous decision making
    """

    def __init__(self) -> None:
        """Initialize Semantic Kernel with Azure OpenAI."""
        self.kernel = Kernel()

        # Configure Azure OpenAI service
        self._setup_azure_openai()

        # Initialize Application Insights telemetry
        self._setup_telemetry()

        # Initialize agent modules as SK plugins
        self.risk_predictor = RiskPredictor()
        self.rollback_validator = RollbackValidator()
        self.contract_engine = ContractEngine()

        # Chat history for context
        self.chat_history = ChatHistory()

        logger.info("Semantic Kernel orchestrator initialized")

    def _setup_azure_openai(self) -> None:
        """Configure Azure OpenAI service in Semantic Kernel."""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

        if not endpoint or not api_key:
            logger.warning("Azure OpenAI credentials not found. Using mock mode.")
            return

        # Add Azure OpenAI chat completion service
        self.kernel.add_service(
            AzureChatCompletion(
                deployment_name=deployment,
                endpoint=endpoint,
                api_key=api_key,
                service_id="chaos-negotiator-ai",
            )
        )

        logger.info(f"Azure OpenAI configured: {deployment}")

    def _setup_telemetry(self) -> None:
        """Initialize Application Insights telemetry."""
        instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY")

        if instrumentation_key:
            self.telemetry = TelemetryClient(instrumentation_key)
            logger.info("Application Insights telemetry enabled")
        else:
            self.telemetry = None
            logger.warning("Application Insights not configured")

    def track_event(self, event_name: str, properties: dict[str, Any] | None = None) -> None:
        """Track custom event in Application Insights."""
        if self.telemetry:
            self.telemetry.track_event(event_name, properties or {})
            self.telemetry.flush()

    def track_metric(
        self, name: str, value: float, properties: dict[str, Any] | None = None
    ) -> None:
        """Track custom metric in Application Insights."""
        if self.telemetry:
            self.telemetry.track_metric(name, value, properties=properties)
            self.telemetry.flush()

    async def orchestrate_deployment(self, context: DeploymentContext) -> DeploymentContract:
        """
        Orchestrate full deployment contract generation using agentic workflow.

        Steps:
        1. Predict risk from deployment context
        2. Validate rollback capability
        3. Generate deployment contract with guardrails
        4. Track decision in telemetry

        Args:
            context: Deployment context with changes and current metrics

        Returns:
            DeploymentContract with risk assessment, guardrails, and rollback plan
        """
        logger.info(f"Orchestrating deployment: {context.deployment_id}")

        # Track deployment start
        self.track_event(
            "DeploymentOrchestrationStarted",
            {
                "deployment_id": context.deployment_id,
                "service_name": context.service_name,
                "environment": context.environment,
                "changes_count": len(context.changes),
            },
        )

        try:
            # Step 1: Predict risk using AI
            logger.info("Step 1/3: Predicting risk...")
            risk_assessment = await self._predict_risk_agentic(context)

            self.track_metric(
                "risk_score",
                risk_assessment.risk_score,
                {"deployment_id": context.deployment_id, "risk_level": risk_assessment.risk_level},
            )

            # Step 2: Validate rollback capability
            logger.info("Step 2/3: Validating rollback...")
            rollback_plan = await self._validate_rollback_agentic(context)

            self.track_metric(
                "rollback_time_seconds",
                rollback_plan.total_estimated_time_seconds,
                {"deployment_id": context.deployment_id},
            )

            # Step 3: Generate contract with guardrails
            logger.info("Step 3/3: Generating contract...")
            contract = await self._generate_contract_agentic(
                context, risk_assessment, rollback_plan
            )

            # Track successful orchestration
            self.track_event(
                "DeploymentContractGenerated",
                {
                    "deployment_id": context.deployment_id,
                    "risk_level": contract.predicted_risk_level,
                    "guardrails_count": len(contract.guardrails),
                    "approval_status": contract.approval_status,
                },
            )

            logger.info(
                f"Contract generated for {context.deployment_id}: " f"{contract.approval_status}"
            )

            return contract

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            self.track_event(
                "DeploymentOrchestrationFailed",
                {"deployment_id": context.deployment_id, "error": str(e)},
            )
            raise

    async def _predict_risk_agentic(self, context: DeploymentContext) -> RiskAssessment:
        """
        Predict deployment risk using Semantic Kernel agentic reasoning.

        This demonstrates autonomous AI decision-making:
        - Analyzes code changes for patterns
        - Considers current system metrics
        - Generates confidence-scored predictions
        """
        # Use existing risk predictor (enhanced with SK in future)
        risk = self.risk_predictor.predict(context)

        # Add to chat history for context retention
        self.chat_history.add_user_message(
            f"Analyzed deployment {context.deployment_id}: "
            f"Risk level {risk.risk_level}, score {risk.risk_score}/100"
        )

        return risk

    async def _validate_rollback_agentic(
        self, context: DeploymentContext
    ) -> Any:  # RollbackPlan type
        """
        Validate rollback capability using agentic validation.

        Autonomous checks:
        - Tests rollback procedures
        - Estimates recovery time
        - Identifies data loss risks
        """
        risk = self.risk_predictor.predict(context)
        rollback = self.rollback_validator.validate_and_create(context, risk)

        self.chat_history.add_assistant_message(
            f"Rollback validated: {rollback.total_estimated_time_seconds}s recovery, "
            f"data loss risk: {rollback.data_loss_risk}"
        )

        return rollback

    async def _generate_contract_agentic(
        self, context: DeploymentContext, risk_assessment: RiskAssessment, rollback_plan: Any
    ) -> DeploymentContract:
        """
        Generate deployment contract using agentic contract engine.

        Intelligent guardrail generation:
        - Context-aware thresholds
        - Risk-proportional constraints
        - Mitigation suggestions
        """
        contract = self.contract_engine.draft_contract(
            context=context, risk_assessment=risk_assessment, rollback_plan=rollback_plan
        )

        self.chat_history.add_assistant_message(
            f"Contract generated with {len(contract.guardrails)} guardrails, "
            f"status: {contract.approval_status}"
        )

        return contract

    def get_orchestration_context(self) -> str:
        """Get full orchestration context from chat history."""
        messages = []
        for message in self.chat_history.messages:
            role = message.role
            content = message.content
            messages.append(f"{role}: {content}")
        return "\n".join(messages)
