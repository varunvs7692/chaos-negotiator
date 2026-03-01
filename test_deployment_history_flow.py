#!/usr/bin/env python3
"""
Test script to verify the complete deployment history flow.

This script tests:
1. POST /api/deployments/record-result endpoint
2. Outcomes being saved to SQLite history store
3. GET /api/dashboard/history returning the saved records
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_record_result():
    """Test recording a deployment result."""
    print("\n" + "="*70)
    print("🧪 TEST 1: Record Deployment Result")
    print("="*70)
    
    payload = {
        "deployment_id": "test-deploy-" + str(int(time.time())),
        "actual_error_rate_percent": 0.08,
        "actual_latency_change_percent": 2.5,
        "rollback_triggered": False,
    }
    
    print(f"\n📤 POST /api/deployments/record-result")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/deployments/record-result",
            json=payload,
            timeout=10
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"   Deployment ID: {result.get('deployment_id')}")
            print(f"   Final Score: {result.get('final_score'):.1f}")
            print(f"   Timestamp: {result.get('timestamp')}")
            return payload["deployment_id"]
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


def test_get_history():
    """Test retrieving deployment history."""
    print("\n" + "="*70)
    print("🧪 TEST 2: Get Deployment History")
    print("="*70)
    
    print(f"\n📤 GET /api/dashboard/history")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/history?limit=10",
            timeout=10
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            outcomes = data.get("outcomes", [])
            
            print(f"✅ Success!")
            print(f"   Total Records: {total}")
            
            if outcomes:
                print(f"\n   📋 Recent Deployments:")
                for i, outcome in enumerate(outcomes[:5], 1):
                    print(f"\n   [{i}] {outcome.get('deployment_id')}")
                    print(f"       Final Score: {outcome.get('final_score'):.1f}")
                    print(f"       Error Rate: {outcome.get('actual_error_rate'):.2f}%")
                    print(f"       Latency Change: {outcome.get('actual_latency_change'):.1f}%")
                    print(f"       Rollback: {outcome.get('rollback_triggered')}")
                    print(f"       Timestamp: {outcome.get('timestamp')}")
            else:
                print(f"\n   ⚠️  No deployment records found yet")
            
            return total > 0
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_multiple_records():
    """Test recording multiple deployment results."""
    print("\n" + "="*70)
    print("🧪 TEST 3: Record Multiple Results and Verify")
    print("="*70)
    
    deployment_ids = []
    
    # Record 3 deployments
    for i in range(3):
        deployment_id = f"bulk-test-{int(time.time())}-{i}"
        payload = {
            "deployment_id": deployment_id,
            "actual_error_rate_percent": 0.05 + (i * 0.02),
            "actual_latency_change_percent": 1.0 + (i * 0.5),
            "rollback_triggered": i == 2,  # Only last one triggers rollback
        }
        
        print(f"\n[{i+1}/3] Recording {deployment_id}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/deployments/record-result",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"     ✅ Saved successfully")
                deployment_ids.append(deployment_id)
            else:
                print(f"     ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"     ❌ Exception: {e}")
        
        time.sleep(0.5)  # Small delay between records
    
    # Verify they all exist in history
    print(f"\n\n📋 Verifying {len(deployment_ids)} records in history...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/history?limit=50",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            outcomes = data.get("outcomes", [])
            stored_ids = {o.get("deployment_id") for o in outcomes}
            
            found_count = sum(1 for did in deployment_ids if did in stored_ids)
            print(f"   ✅ Found {found_count}/{len(deployment_ids)} records in history")
            
            return found_count == len(deployment_ids)
        else:
            print(f"   ❌ Failed to retrieve history: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🔍 DEPLOYMENT HISTORY FLOW TEST SUITE" + "\n")
    
    try:
        # Check if server is running
        print("⏳ Checking if API server is running...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API server not responding. Start it with:")
            print("   python -m chaos_negotiator.server")
            return
        print("✅ API server is running\n")
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("\nStart the server with:")
        print("   python -m chaos_negotiator.server")
        return
    
    results = []
    
    # Test 1: Record a single result
    deployment_id = test_record_result()
    results.append(("Record Single Result", deployment_id is not None))
    
    # Brief delay
    time.sleep(1)
    
    # Test 2: Get history
    has_history = test_get_history()
    results.append(("Get History", has_history))
    
    # Small delay
    time.sleep(1)
    
    # Test 3: Record multiple and verify
    multi_success = test_multiple_records()
    results.append(("Record Multiple", multi_success))
    
    # Summary
    print("\n\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Deployment history flow is working correctly.")
        print("\n📍 Next steps:")
        print("   1. Start the FastAPI server:")
        print("      python -m chaos_negotiator.server")
        print("   2. Open dashboard at http://localhost:8000")
        print("   3. History should start populating when you record results")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()
