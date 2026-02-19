"""Main entry point for Chaos Negotiator."""

import json
import logging
import sys
import asyncio
from chaos_negotiator.agent import ChaosNegotiatorAgent
from chaos_negotiator.models import DeploymentContext, DeploymentChange

# Import enforcement simulator for demo
try:
    from chaos_negotiator.enforcement import run_enforcement_demo
    ENFORCEMENT_AVAILABLE = True
except ImportError:
    ENFORCEMENT_AVAILABLE = False
    logging.warning("Enforcement simulator not available")

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


def get_example_context(scenario: str = "default") -> DeploymentContext:
    """Get example deployment context for different scenarios."""
    
    scenarios = {
        "default": DeploymentContext(
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
        ),
        
        "high_risk": DeploymentContext(
            deployment_id="deploy-risky-002",
            service_name="payment-processor",
            environment="production",
            version="v3.0.0",
            changes=[
                DeploymentChange(
                    file_path="src/database/migrations/v3_schema.py",
                    change_type="add",
                    lines_changed=250,
                    risk_tags=["database", "migration", "breaking_change"],
                    description="Major database schema migration with no fallback",
                ),
                DeploymentChange(
                    file_path="src/cache/redis_client.py",
                    change_type="modify",
                    lines_changed=120,
                    risk_tags=["caching", "session_state"],
                    description="Aggressive cache TTL reduction",
                ),
            ],
            total_lines_changed=370,
            current_error_rate_percent=0.02,
            current_p95_latency_ms=120.0,
            current_p99_latency_ms=300.0,
            target_error_rate_percent=0.05,
            target_p95_latency_ms=200.0,
            target_p99_latency_ms=500.0,
            current_qps=10000.0,
            peak_qps=15000.0,
            owner_team="Payments Team",
            rollback_capability=False,  # No rollback for DB migration
        ),
        
        "low_risk": DeploymentContext(
            deployment_id="deploy-safe-003",
            service_name="logging-service",
            environment="staging",
            version="v1.5.1",
            changes=[
                DeploymentChange(
                    file_path="src/formatters/json.py",
                    change_type="modify",
                    lines_changed=12,
                    risk_tags=["logging"],
                    description="Update log message formatting",
                ),
            ],
            total_lines_changed=12,
            current_error_rate_percent=0.01,
            current_p95_latency_ms=50.0,
            current_p99_latency_ms=100.0,
            target_error_rate_percent=0.05,
            target_p95_latency_ms=100.0,
            target_p99_latency_ms=200.0,
            current_qps=2000.0,
            peak_qps=3000.0,
            owner_team="Observability Team",
            rollback_capability=True,
        ),
    }
    
    return scenarios.get(scenario, scenarios["default"])


async def run_full_demo(scenario: str = "default"):
    """Run full demo with enforcement simulation."""
    logger.info("🚀 Chaos Negotiator - Full Demo with Enforcement")
    logger.info("=" * 60)
    
    # Get context
    context = get_example_context(scenario)
    logger.info(f"Scenario: {scenario}")
    logger.info(f"Service: {context.service_name} v{context.version}")
    
    # Initialize agent with SK
    agent = ChaosNegotiatorAgent(use_semantic_kernel=True)
    
    # Process deployment with SK orchestration
    logger.info("\n📋 Step 1/2: Generating Deployment Contract")
    logger.info("=" * 60)
    contract = await agent.process_deployment_async(context)
    
    # Print contract summary
    print("\n" + contract.reasoning[:1000] + "...\n")  # Truncate for display
    
    if ENFORCEMENT_AVAILABLE:
        # Run enforcement simulation
        logger.info("\n🎯 Step 2/2: Simulating Deployment Enforcement")
        logger.info("=" * 60)
        
        # Ask which scenario to simulate
        print("\nSelect enforcement scenario:")
        print("1. Success (all guardrails met)")
        print("2. Error spike (triggers rollback)")
        print("3. Latency spike (triggers rollback)")
        
        try:
            choice = input("\nChoice (1-3, default=1): ").strip() or "1"
            enforcement_scenarios = {"1": "success", "2": "error_spike", "3": "latency_spike"}
            enforcement_scenario = enforcement_scenarios.get(choice, "success")
        except (EOFError, KeyboardInterrupt):
            enforcement_scenario = "success"
        
        result = await run_enforcement_demo(contract, enforcement_scenario)
        
        # Save results
        result_file = f"enforcement-result-{context.deployment_id}.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\n📄 Enforcement results saved to: {result_file}")
    else:
        logger.warning("Enforcement simulator not available - skipping enforcement demo")
    
    # Save contract
    contract_output = f"contract-{context.deployment_id}.json"
    with open(contract_output, "w") as f:
        json.dump(contract.model_dump(mode="json"), f, indent=2, default=str)
    logger.info(f"📄 Contract saved to: {contract_output}")


def main():
    """Main entry point."""
    logger.info("🚀 Chaos Negotiator - Deployment Contract AI Agent")
    logger.info("=" * 60)
    
    # Check for demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        scenario = sys.argv[2] if len(sys.argv) > 2 else "default"
        logger.info(f"Running full demo with scenario: {scenario}")
        asyncio.run(run_full_demo(scenario))
        return 0
    
    # Check for file input
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        # Load from file
        deployment_file = sys.argv[1]
        logger.info(f"Loading deployment context from: {deployment_file}")
        context = load_deployment_context(deployment_file)
    else:
        # Example deployment context
        context = get_example_context("default")

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

    print("\n💡 Tip: Run with --demo flag to see full enforcement simulation!")
    print("   Examples:")
    print("   python -m chaos_negotiator.main --demo default")
    print("   python -m chaos_negotiator.main --demo high_risk")
    print("   python -m chaos_negotiator.main --demo low_risk")

    return 0


if __name__ == "__main__":
    sys.exit(main())

