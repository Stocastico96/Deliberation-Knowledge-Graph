#!/usr/bin/env python3

import requests
import json
import sys
import time

def check_local_server():
    """Check if the local Flask server is running"""
    try:
        response = requests.get('http://localhost:8085/api/stats', timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Local server is running")
            print(f"   📊 {stats.get('totalTriples', 0)} triples")
            print(f"   👥 {stats.get('totalParticipants', 0)} participants")
            print(f"   📝 {stats.get('totalContributions', 0)} contributions")
            print(f"   🏛️  {stats.get('totalProcesses', 0)} processes")
            return True
        else:
            print(f"❌ Local server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Local server not accessible: {e}")
        return False

def check_domain_accessibility():
    """Check if the domain is accessible"""
    domain = "https://svagnoni.linkeddata.es"

    print(f"\n🌐 Checking domain accessibility: {domain}")

    try:
        response = requests.get(domain, timeout=10, allow_redirects=True)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ Domain is accessible")

            # Check if it's our application
            if "Deliberation Knowledge Graph" in response.text:
                print("✅ Our application is running on the domain")
                return True
            else:
                print("⚠️  Domain is accessible but not serving our application")
                return False
        else:
            print(f"❌ Domain returned status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Domain not accessible: {e}")
        return False

def check_api_endpoints():
    """Check if API endpoints are working"""
    domain = "https://svagnoni.linkeddata.es"
    endpoints = [
        "/api/stats",
        "/sparql"
    ]

    print(f"\n🔍 Checking API endpoints on {domain}")

    all_working = True
    for endpoint in endpoints:
        try:
            if endpoint == "/sparql":
                # Test SPARQL with a simple query
                response = requests.post(
                    f"{domain}{endpoint}",
                    data={'query': 'SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }'},
                    timeout=10
                )
            else:
                response = requests.get(f"{domain}{endpoint}", timeout=10)

            if response.status_code == 200:
                print(f"   ✅ {endpoint} - Working")
            else:
                print(f"   ❌ {endpoint} - Status {response.status_code}")
                all_working = False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ {endpoint} - Error: {e}")
            all_working = False

    return all_working

def main():
    print("========================================================")
    print("🏛️  DELIBERATION KNOWLEDGE GRAPH - DEPLOYMENT CHECK")
    print("========================================================")

    # Check local server
    local_ok = check_local_server()

    if not local_ok:
        print("\n❌ Local server is not running. Please start it first:")
        print("   ./deploy_linkeddata.sh")
        sys.exit(1)

    # Check domain
    domain_ok = check_domain_accessibility()

    if domain_ok:
        # Check API endpoints
        api_ok = check_api_endpoints()

        if api_ok:
            print("\n🎉 DEPLOYMENT SUCCESSFUL!")
            print("🌐 Your Deliberation Knowledge Graph is online at:")
            print("   https://svagnoni.linkeddata.es/")
            print("\n📍 Available pages:")
            print("   • Main interface:  https://svagnoni.linkeddata.es/")
            print("   • Visualization:   https://svagnoni.linkeddata.es/visualize")
            print("   • Contributions:   https://svagnoni.linkeddata.es/contributions")
            print("   • SPARQL endpoint: https://svagnoni.linkeddata.es/sparql")
        else:
            print("\n⚠️  Domain is accessible but some API endpoints are not working")
            print("   Check your web server proxy configuration")
    else:
        print("\n⚠️  Local server is running but domain is not accessible")
        print("   Possible issues:")
        print("   • Web server (Apache/Nginx) not configured")
        print("   • Proxy configuration missing")
        print("   • SSL certificates not set up")
        print("   • Firewall blocking connections")

        print("\n📋 Next steps:")
        print("   1. Configure your web server using the provided config:")
        print("      - Apache: apache-vhost-config.conf")
        print("      - Nginx:  nginx-site-config.conf")
        print("   2. Restart your web server")
        print("   3. Run this check again")

if __name__ == '__main__':
    main()