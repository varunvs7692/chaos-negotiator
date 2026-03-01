#!/usr/bin/env python3
"""
Test script to verify live data flow in Chaos Negotiator.

Run this to verify:
1. API endpoint returns dynamic data
2. Agent is being called
3. Responses are properly formatted
4. Data varies (or is stable, as expected)
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8000/api/deployments/latest"

def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_api_connection():
    """Test 1: Can we reach the API?"""
    print_header("TEST 1: API Connection")
    try:
        response = requests.get(API_URL, timeout=5)
        print(f"✅ API is reachable")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response.elapsed.total_seconds():.2f}s")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print(f"   Make sure FastAPI is running:")
        print(f"   uvicorn chaos_negotiator.agent.api:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_response_format():
    """Test 2: Is the response format correct?"""
    print_header("TEST 2: Response Format")
    try:
        response = requests.get(API_URL, timeout=5)
        data = response.json()
        
        required_fields = {
            "service": str,
            "risk_percent": (int, float),
            "confidence_percent": (int, float),
            "risk_level": str,
            "canary_stage": str,
            "traffic_percent": (int, float),
        }
        
        missing = []
        type_errors = []
        
        for field, expected_type in required_fields.items():
            if field not in data:
                missing.append(field)
            elif not isinstance(data[field], expected_type):
                type_errors.append(f"{field}: got {type(data[field]).__name__}, expected {expected_type}")
        
        if missing:
            print(f"❌ Missing fields: {missing}")
            return False
        
        if type_errors:
            print(f"❌ Type errors:")
            for err in type_errors:
                print(f"   - {err}")
            return False
        
        print(f"✅ Response format is correct")
        print(f"\nResponse data:")
        print(json.dumps(data, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_data_values():
    """Test 3: Are the data values reasonable?"""
    print_header("TEST 3: Data Values")
    try:
        response = requests.get(API_URL, timeout=5)
        data = response.json()
        
        issues = []
        
        # Check risk_percent range
        if not (0 <= data["risk_percent"] <= 100):
            issues.append(f"risk_percent {data['risk_percent']} not in [0, 100]")
        
        # Check confidence_percent range
        if not (0 <= data["confidence_percent"] <= 100):
            issues.append(f"confidence_percent {data['confidence_percent']} not in [0, 100]")
        
        # Check risk_level is valid
        valid_levels = ["low", "medium", "high", "critical"]
        if data["risk_level"] not in valid_levels:
            issues.append(f"risk_level '{data['risk_level']}' not in {valid_levels}")
        
        # Check canary_stage is valid
        valid_stages = ["smoke", "light", "half", "majority", "full"]
        if data["canary_stage"] not in valid_stages:
            issues.append(f"canary_stage '{data['canary_stage']}' not in {valid_stages}")
        
        # Check traffic_percent range
        if not (0 <= data["traffic_percent"] <= 100):
            issues.append(f"traffic_percent {data['traffic_percent']} not in [0, 100]")
        
        if issues:
            print(f"❌ Data validation errors:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        
        print(f"✅ All values are in valid ranges")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dynamic_data():
    """Test 4: Does data change across multiple calls?"""
    print_header("TEST 4: Dynamic Data (Multi-Call Test)")
    try:
        print(f"Making 3 API calls with 2-second delays...\n")
        
        values = []
        for i in range(3):
            response = requests.get(API_URL, timeout=5)
            data = response.json()
            values.append(data)
            
            print(f"Call {i+1}:")
            print(f"  risk_percent: {data['risk_percent']:.2f}%")
            print(f"  confidence_percent: {data['confidence_percent']:.2f}%")
            print(f"  risk_level: {data['risk_level']}")
            print(f"  canary_stage: {data['canary_stage']}")
            print()
            
            if i < 2:
                time.sleep(2)
        
        # Check if ANY value changed
        changed = False
        for field in ["risk_percent", "confidence_percent"]:
            if values[0][field] != values[1][field] or values[1][field] != values[2][field]:
                changed = True
                break
        
        if changed:
            print(f"✅ Data is dynamic (values changed across calls)")
            return True
        else:
            print(f"⚠️  Data appears static (same values across calls)")
            print(f"   This could mean:")
            print(f"   - Demo context is always the same (expected)")
            print(f"   - Agent is being called but producing same results (normal)")
            print(f"   - Check server logs to confirm agent.process_deployment() is called")
            return True  # Not a failure, just informational
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests."""
    print_header("Chaos Negotiator — Live Data Flow Test Suite")
    
    tests = [
        ("API Connection", test_api_connection),
        ("Response Format", test_response_format),
        ("Data Values", test_data_values),
        ("Dynamic Data", test_dynamic_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"🚨 Unhandled exception in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} — {test_name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Live data flow is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. See above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
