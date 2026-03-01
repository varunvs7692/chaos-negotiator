#!/usr/bin/env python3
"""
Quick Demo: Record Deployment Results and View History

This demonstrates the complete "Evaluate → Deploy → Record → Learn" flow.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def record_deployment_result(deployment_id: str, error_rate: float, latency_change: float, rollback: bool):
    """Record a deployment outcome."""
    print(f"📤 Recording: {deployment_id}")
    print(f"   • Error Rate: {error_rate}%")
    print(f"   • Latency Change: {latency_change}%")
    print(f"   • Rollback: {rollback}")
    
    response = requests.post(
        f"{BASE_URL}/api/deployments/record-result",
        json={
            "deployment_id": deployment_id,
            "actual_error_rate_percent": error_rate,
            "actual_latency_change_percent": latency_change,
            "rollback_triggered": rollback,
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Final Score: {data['final_score']:.1f}")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        return False


def get_deployment_history(limit: int = 10):
    """Retrieve deployment history."""
    response = requests.get(f"{BASE_URL}/api/dashboard/history?limit={limit}")
    
    if response.status_code == 200:
        data = response.json()
        return data.get("outcomes", [])
    else:
        print(f"Failed to get history: {response.status_code}")
        return []


def main():
    """Run the demo."""
    print("\n" + "🚀 CHAOS NEGOTIATOR - DEPLOYMENT HISTORY DEMO" + "\n")
    
    # Check server is running
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=2)
        if r.status_code != 200:
            print("❌ API server not responding.")
            print("   Start it with: python -m chaos_negotiator.server")
            return
    except Exception as e:
        print(f"❌ Cannot reach API server: {e}")
        print("   Make sure it's running on port 8000")
        return
    
    print("✅ API Server is running\n")
    
    # Scenario 1: Successful deployment
    print_section("SCENARIO 1: Successful Canary Deployment")
    print("Simulating: Small payload deployment with no issues\n")
    
    success = True
    for stage_num in range(1, 4):
        deployment_id = f"prod-canary-{int(time.time())}-stage{stage_num}"
        
        # Gradual traffic increase = lower error rate risk
        error_rate = 0.03 + (stage_num * 0.01)
        latency_change = 0.5 + (stage_num * 0.2)
        
        if record_deployment_result(deployment_id, error_rate, latency_change, False):
            time.sleep(0.5)
        else:
            success = False
    
    if not success:
        print("\n⚠️  Some recordings failed. Check server logs.")
        return
    
    # Scenario 2: Failed deployment that triggers rollback
    print_section("SCENARIO 2: High-Risk Deployment (Triggers Rollback)")
    print("Simulating: Database migration with hidden concurrency bug\n")
    
    deployment_id = f"prod-db-{int(time.time())}"
    record_deployment_result(deployment_id, 8.5, 45.0, True)
    
    # Scenario 3: Medium-risk stable deployment
    print_section("SCENARIO 3: Medium-Risk Stable Deployment")
    print("Simulating: API endpoint refactoring with good testing\n")
    
    deployment_id = f"prod-api-{int(time.time())}"
    record_deployment_result(deployment_id, 0.15, 3.5, False)
    
    # Display all recorded history
    print_section("RECENT DEPLOYMENT HISTORY (What Dashboard Shows)")
    
    history = get_deployment_history(limit=20)
    
    if not history:
        print("⚠️  No deployments recorded yet.")
        return
    
    print(f"📋 Total Deployments Recorded: {len(history)}\n")
    print(f"{'ID':<30} {'Final Score':<12} {'Error %':<10} {'Rollback':<10} {'Time':<20}")
    print(f"{'-'*82}")
    
    for outcome in history[:10]:
        deploy_id = outcome["deployment_id"][:28]
        final_score = outcome["final_score"]
        error_rate = outcome["actual_error_rate"]
        rollback = "YES" if outcome["rollback_triggered"] else "NO"
        timestamp = outcome["timestamp"].split("T")[1].split(".")[0]
        
        print(f"{deploy_id:<30} {final_score:<12.1f} {error_rate:<10.2f} {rollback:<10} {timestamp:<20}")
    
    print_section("✅ DEMO COMPLETE")
    print("📊 What just happened:")
    print("   1. You recorded 5 deployment outcomes")
    print("   2. Each was saved to SQLite history store")
    print("   3. The agent learned from the actual metrics")
    print("   4. Auto-tuning scheduler adjusted ML weights")
    print("   5. Dashboard populated with Recent Deployment History\n")
    
    print("🎯 Next steps:")
    print("   • Open http://localhost:8000 in your browser")
    print("   • Check 'Recent Deployment History' section")
    print("   • Should show all 5 deployments we just recorded!\n")
    print("📝 For production use:")
    print("   • Call POST /api/deployments/record-result after each deployment")
    print("   • Include real metrics from your monitoring system")
    print("   • Let the feedback loop improve predictions over time\n")


if __name__ == "__main__":
    main()
