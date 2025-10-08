#!/usr/bin/env python3

import requests
import sys

def test_url(url, description):
    try:
        response = requests.get(url, timeout=10)
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {description}: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text[:100]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ {description}: ERROR - {str(e)}")
        return False

def main():
    base_url = "https://svagnoni.linkeddata.es"

    print("🧪 Test completo route /dkg/ su https://svagnoni.linkeddata.es")
    print("=" * 70)

    # Test redirect root
    print("\n🔄 Redirect:")
    test_url(f"{base_url}/", "Root redirect to /dkg")

    # Test pagine DKG
    print("\n📄 Pagine DKG:")
    test_url(f"{base_url}/dkg", "Homepage DKG")
    test_url(f"{base_url}/dkg/contributions", "Contributions DKG")
    test_url(f"{base_url}/dkg/visualize", "Visualization DKG")
    test_url(f"{base_url}/dkg/sparql", "SPARQL Interface DKG")

    # Test API DKG
    print("\n🔌 API DKG:")
    test_url(f"{base_url}/dkg/api/stats", "Stats API DKG")
    test_url(f"{base_url}/dkg/api/contributions", "Contributions API DKG")

    # Test export DKG
    print("\n📦 Export DKG:")
    test_url(f"{base_url}/dkg/api/export/ttl", "Export TTL DKG")
    test_url(f"{base_url}/dkg/api/export/json", "Export JSON DKG")

    # Test SPARQL endpoint DKG
    print("\n🔍 SPARQL DKG:")
    test_url(f"{base_url}/dkg/sparql?query=SELECT%20*%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201&format=json", "SPARQL Query DKG")

    # Test API originali (per compatibilità)
    print("\n🔌 API Originali (compatibility):")
    test_url(f"{base_url}/api/stats", "Stats API Original")
    test_url(f"{base_url}/sparql?query=SELECT%20*%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201&format=json", "SPARQL Original")

    print("\n=" * 70)
    print("🏁 Test /dkg/ completato!")
    print("\n📋 URL Principali:")
    print(f"   🏠 Homepage: {base_url}/dkg")
    print(f"   👥 Contributions: {base_url}/dkg/contributions")
    print(f"   📊 Visualization: {base_url}/dkg/visualize")
    print(f"   🔍 SPARQL: {base_url}/dkg/sparql")
    print(f"   📈 Stats API: {base_url}/dkg/api/stats")
    print(f"   📂 Export TTL: {base_url}/dkg/api/export/ttl")

if __name__ == "__main__":
    main()