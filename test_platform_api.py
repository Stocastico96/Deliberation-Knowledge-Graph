#!/usr/bin/env python3
"""
Test script to verify the online platform functionality
"""

import requests
import json
import time

def test_platform(base_url="http://localhost:8082"):
    """Test the platform endpoints"""
    print(f"🧪 Testing Deliberation Knowledge Graph Platform at {base_url}")

    tests = []

    # Test 1: Homepage
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200 and "Deliberation Knowledge Graph" in response.text:
            tests.append(("✅ Homepage", "Working"))
        else:
            tests.append(("❌ Homepage", f"Failed: {response.status_code}"))
    except Exception as e:
        tests.append(("❌ Homepage", f"Error: {e}"))

    # Test 2: Statistics API
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tests.append(("✅ Statistics API", f"Triples: {data.get('totalTriples', 0)}"))
        else:
            tests.append(("❌ Statistics API", f"Failed: {response.status_code}"))
    except Exception as e:
        tests.append(("❌ Statistics API", f"Error: {e}"))

    # Test 3: SPARQL Endpoint
    sparql_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    SELECT ?process ?name
    WHERE {
        ?process a del:DeliberationProcess ;
                 del:name ?name .
    }
    LIMIT 5
    """

    try:
        response = requests.post(
            f"{base_url}/sparql",
            headers={'Content-Type': 'application/json'},
            json={'query': sparql_query},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', {}).get('bindings', []))
            tests.append(("✅ SPARQL Endpoint", f"Found {count} processes"))
        else:
            tests.append(("❌ SPARQL Endpoint", f"Failed: {response.status_code}"))
    except Exception as e:
        tests.append(("❌ SPARQL Endpoint", f"Error: {e}"))

    # Test 4: Cross-platform connections
    cross_platform_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?name1 ?platform1 ?name2 ?platform2
    WHERE {
        ?p1 del:name ?name1 ;
            del:platform ?platform1 .
        ?p2 del:name ?name2 ;
            del:platform ?platform2 .
        ?p1 owl:sameAs ?p2 .
    }
    """

    try:
        response = requests.post(
            f"{base_url}/sparql",
            headers={'Content-Type': 'application/json'},
            json={'query': cross_platform_query},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', {}).get('bindings', []))
            tests.append(("✅ Cross-platform Links", f"Found {count} connections"))
        else:
            tests.append(("❌ Cross-platform Links", f"Failed: {response.status_code}"))
    except Exception as e:
        tests.append(("❌ Cross-platform Links", f"Error: {e}"))

    # Print results
    print("\n📊 Test Results:")
    print("-" * 50)
    for test_name, result in tests:
        print(f"{test_name}: {result}")

    # Summary
    passed = sum(1 for test_name, _ in tests if test_name.startswith("✅"))
    total = len(tests)

    print(f"\n🎯 Summary: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The platform is working correctly.")
        print(f"🌐 Access the platform at: {base_url}")
        return True
    else:
        print("⚠️ Some tests failed. Check the server logs.")
        return False

if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8082"

    print("Waiting 2 seconds for server to start...")
    time.sleep(2)

    test_platform(base_url)