"""Main AI Agent for Chaos Negotiator."""

import logging
import os
from datetime import datetime
from typing import Optional
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam
from chaos_negotiator.models import (
    DeploymentContext,
    DeploymentContract,
    Guardrail,
    GuardrailRequirement,
)
from chaos_negotiator.predictors import RiskPredictor
from chaos_negotiator.validators import RollbackValidator
from chaos_negotiator.contracts import ContractEngine

# Import Semantic Kernel orchestrator
try:
    from chaos_negotiator.agent.sk_orchestrator import SemanticKernelOrchestrator

    SK_AVAILABLE = True
except ImportError:
    SK_AVAILABLE = False
    logging.warning("Semantic Kernel not available, using legacy mode")

logger = logging.getLogger(__name__)


class ChaosNegotiatorAgent:
    """
    AI Agent that negotiates deployment contracts.

    - Analyzes deployment context and changes
    - Predicts SLO impact (risk assessment)
    - Validates rollback capability
    - Drafts enforceable deployment contracts

    Uses Microsoft Semantic Kernel for agentic orchestration when available.
    """

    def __init__(self, api_key: Optional[str] = None, use_semantic_kernel: bool = True):
        """Initialize the agent with Azure OpenAI client.

        Args:
            api_key: Azure OpenAI API key (defaults to env var)
            use_semantic_kernel: Whether to use SK orchestration (default: True)
        """
        api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        # Initialize client if credentials are available
        self.client: AzureOpenAI | None
        self.model: str | None
        if api_key and endpoint:
            self.client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint)
            self.model = "gpt-4"  # Use your deployed model name from Azure OpenAI
            self.is_mock_mode = False
        else:
            # Test/mock mode for development and testing
            logger.warning(
                "Azure OpenAI credentials not configured. Running in test mode with stub responses."
            )
            self.client = None
            self.model = None
            self.is_mock_mode = True

        # Initialize Semantic Kernel orchestrator if available and requested
        self.sk_orchestrator: SemanticKernelOrchestrator | None
        if SK_AVAILABLE and use_semantic_kernel:
            try:
                self.sk_orchestrator = SemanticKernelOrchestrator()
                self.use_sk = True
                logger.info("Semantic Kernel orchestration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Semantic Kernel: {e}")
                self.sk_orchestrator = None
                self.use_sk = False
        else:
            self.sk_orchestrator = None
            self.use_sk = False
            if not SK_AVAILABLE:
                logger.info("Semantic Kernel not available, using legacy orchestration")

        # Initialize sub-engines (used by both SK and legacy modes)
        self.risk_predictor = RiskPredictor()
        self.rollback_validator = RollbackValidator()
        self.contract_engine = ContractEngine()

        self.conversation_history: list[ChatCompletionMessageParam] = []

    async def process_deployment_async(self, context: DeploymentContext) -> DeploymentContract:
        """Process deployment using Semantic Kernel orchestration (async)."""
        if self.use_sk and self.sk_orchestrator:
            logger.info("Using Semantic Kernel orchestration")
            return await self.sk_orchestrator.orchestrate_deployment(context)
        else:
            logger.info("Using legacy orchestration")
            return self.process_deployment(context)

    def process_deployment(self, context: DeploymentContext) -> DeploymentContract:
        """
        Process a deployment request and negotiate a contract (synchronous).

        Returns:
            DeploymentContract with all negotiation details
        """
        logger.info(f"Processing deployment: {context.deployment_id}")

        # Step 1: Risk assessment
        logger.info("Step 1: Analyzing deployment risk...")
        risk_assessment = self.risk_predictor.predict(context)
        logger.info(
            f"Risk Score: {risk_assessment.risk_score:.1f}, Level: {risk_assessment.risk_level}"
        )

        # Step 2: Rollback validation
        logger.info("Step 2: Validating rollback capability...")
        rollback_plan = self.rollback_validator.validate_and_create(context, risk_assessment)
        logger.info(
            f"Rollback Possible: {rollback_plan.rollback_possible}, Time: {rollback_plan.total_estimated_time_seconds}s"
        )

        # Step 3: Contract drafting
        logger.info("Step 3: Drafting deployment contract...")
        contract = self.contract_engine.draft_contract(context, risk_assessment, rollback_plan)
        logger.info(f"Contract drafted: {contract.contract_id}")

        return contract

    def negotiate_with_user(self, context: DeploymentContext) -> DeploymentContract:
        """
        Engage in interactive negotiation with the user about deployment safety.
        """
        logger.info("Starting interactive negotiation...")

        # Get initial contract
        contract = self.process_deployment(context)

        # Setup conversation
        self._setup_conversation(context, contract)

        # Interactive loop
        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["approve", "yes", "accepted"]:
                contract.status = "approved"
                contract.approved_at = datetime.utcnow()
                logger.info("Contract approved!")
                break

            if user_input.lower() in ["reject", "no", "denied"]:
                contract.status = "rejected"
                logger.info("Contract rejected.")
                break

            # Get agent response
            response = self._get_agent_response(user_input, context, contract)
            print(f"\nAgent: {response}")

        return contract

    def _setup_conversation(self, context: DeploymentContext, contract: DeploymentContract) -> None:
        """Initialize conversation with system context."""
        system_message = f"""You are Chaos Negotiator, an AI agent specializing in deployment safety.
Your role is to negotiate deployment contracts that ensure reliability goals are met.

Current Deployment Context:
- Service: {context.service_name}
- Environment: {context.environment}
- Changes: {len(context.changes)} file(s)
- Current Error Rate: {context.current_error_rate_percent}%
- Current P95 Latency: {context.current_p95_latency_ms}ms

Drafted Contract Status: {contract.status}
Risk Level: {contract.predicted_risk_level}
Risk Score: {contract.risk_score:.1f}/100

Your job is to:
1. Explain why guardrails are needed
2. Answer questions about deployment safety
3. Suggest mitigations or improvements
4. Be firm on critical safety requirements
5. Allow negotiation on medium/low risk items

Guardrails in contract:
{self._format_guardrails(contract)}

Required validators:
{self._format_validators(contract)}
"""

        self.conversation_history.append({"role": "user", "content": system_message})

    def _get_agent_response(
        self, user_message: str, context: DeploymentContext, contract: DeploymentContract
    ) -> str:
        """Get response from Claude (or stub in test mode)."""
        self.conversation_history.append({"role": "user", "content": user_message})

        # Mock mode response for testing
        if self.is_mock_mode:
            assistant_message = f"[Test Mode] I've reviewed your deployment for {context.service_name}. The contract requires all guardrails to be met before proceeding. Please ensure your deployment passes the validators."
        else:
            # Real Azure OpenAI response
            if self.client is None or self.model is None:
                raise RuntimeError("Azure OpenAI client is not configured")
            messages: list[ChatCompletionMessageParam] = [
                {
                    "role": "system",
                    "content": (
                        "You are Chaos Negotiator, a deployment safety negotiator. Be concise and "
                        "firm on critical safety items. Service: "
                        f"{context.service_name}, Risk Level: {contract.predicted_risk_level}"
                    ),
                }
            ]
            messages.extend(self.conversation_history[-10:])

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=messages,
            )

            assistant_message = response.choices[0].message.content or ""

        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def _format_guardrails(self, contract: DeploymentContract) -> str:
        """Format guardrails for display."""
        lines = []
        for g in contract.guardrails:
            if isinstance(g, GuardrailRequirement):
                lines.append(f"  - {g.guardrail_type.value}: {g.max_value}{g.unit}")
            elif isinstance(g, Guardrail):
                lines.append(f"  - {g.metric_name}: {g.comparison} {g.threshold}")
        return "\n".join(lines) or "  (none)"

    def _format_validators(self, contract: DeploymentContract) -> str:
        """Format validators for display."""
        lines = []
        for v in contract.validators:
            req = "REQUIRED" if v.required else "recommended"
            lines.append(f"  - {v.validator_type} ({req})")
        return "\n".join(lines) or "  (none)"

    def explain_contract(self, contract: DeploymentContract) -> str:
        """Generate human-readable explanation of contract."""
        return contract.reasoning
