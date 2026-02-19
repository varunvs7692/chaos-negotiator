"""Main entry point for Chaos Negotiator."""

import json
import logging
import sys
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentContext, DeploymentChange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_deployment_context(filepath: str) -> DeploymentContext:
    """Load deployment context from JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)

    # Handle nested DeploymentChange objects
    changes = []
    for change_data in data.get("changes", []):
        changes.append(DeploymentChange(**change_data))

    data["changes"] = changes
    return DeploymentContext(**data)


def main():
    """Main entry point."""
    logger.info("🚀 Chaos Negotiator - Deployment Contract AI Agent")
    logger.info("=" * 60)

    if len(sys.argv) > 1:
        # Load from file
        deployment_file = sys.argv[1]
        logger.info(f"Loading deployment context from: {deployment_file}")
        context = load_deployment_context(deployment_file)
    else:
        # Example deployment context
        context = DeploymentContext(
            deployment_id="deploy-example-001",
            service_name="user-service",
            environment="production",
            version="v2.1.0",
            changes=[
                DeploymentChange(
                    file_path="src/cache/manager.py",
                    change_type="modify",
                    lines_changed=45,
                    risk_tags=["caching", "performance"],
                    description="Optimize cache TTL strategy for frequently accessed user profiles",
                ),
                DeploymentChange(
                    file_path="src/api/handlers.py",
                    change_type="modify",
                    lines_changed=78,
                    risk_tags=["api", "latency"],
                    description="Update API response serialization for lower latency",
                ),
            ],
            total_lines_changed=123,
            current_error_rate_percent=0.05,
            current_p95_latency_ms=180.0,
            current_p99_latency_ms=450.0,
            target_error_rate_percent=0.1,
            target_p95_latency_ms=250.0,
            target_p99_latency_ms=800.0,
            current_qps=5000.0,
            peak_qps=8000.0,
            owner_team="Platform Team",
            rollback_capability=True,
        )

    # Initialize agent
    agent = ChaosNegotiatorAgent()

    # Process deployment
    logger.info(f"Analyzing deployment: {context.service_name} v{context.version}")
    contract = agent.process_deployment(context)

    # Print contract
    try:
        print("\n" + contract.reasoning)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback for systems with encoding issues
        print("\n[Contract Generated - see contract JSON file for details]")

    # Ask for approval
    print("\n" + "=" * 60)
    print("Contract Status: DRAFT")
    print("=" * 60)

    # Save contract
    contract_output = f"contract-{context.deployment_id}.json"
    with open(contract_output, "w") as f:
        json.dump(contract.model_dump(mode="json"), f, indent=2, default=str)
    logger.info(f"Contract saved to: {contract_output}")

    # Simulate approval
    try:
        print("\n[!] This deployment must satisfy ALL guardrails in the contract.")
        approval = input("Do you accept this contract? (yes/no): ").strip().lower()

        if approval in ["yes", "y"]:
            contract.status = "approved"
            print("[OK] Contract APPROVED! Deployment can proceed with safeguards active.")
        else:
            contract.status = "rejected"
            print("[REJECTED] Contract REJECTED. Please address concerns and try again.")
            print("\nSuggested improvements:")
            for fix in contract.suggested_fixes:
                print(f"  - {fix}")
    except (EOFError, UnicodeEncodeError):
        # Handle non-interactive terminals or encoding issues
        logger.info("Running in non-interactive mode - skipping approval prompt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
