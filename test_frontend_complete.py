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

    print("🧪 Test completo frontend su https://svagnoni.linkeddata.es")
    print("=" * 60)

    # Test pagine principali
    print("\n📄 Pagine HTML:")
    test_url(f"{base_url}/", "Homepage")
    test_url(f"{base_url}/contributions", "Contributions")
    test_url(f"{base_url}/visualize", "Visualization")

    # Test API
    print("\n🔌 API:")
    test_url(f"{base_url}/api/stats", "Stats API")
    test_url(f"{base_url}/api/contributions", "Contributions API")
    test_url(f"{base_url}/sparql?query=SELECT%20*%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201&format=json", "SPARQL")

    # Test export
    print("\n📦 Export:")
    test_url(f"{base_url}/api/export/ttl", "Export TTL")
    test_url(f"{base_url}/api/export/json", "Export JSON")

    # Test file statici
    print("\n🎨 File statici:")
    test_url(f"{base_url}/css/styles.css", "CSS principale")
    test_url(f"{base_url}/js/main.js", "JavaScript principale")

    # Test immagini
    print("\n🖼️ Immagini:")
    test_url(f"{base_url}/DKG%20daft.png", "Immagine hero")
    test_url(f"{base_url}/what-is-the-european-parliament.png", "Immagine parlamento")

    print("\n=" * 60)
    print("🏁 Test completato!")

if __name__ == "__main__":
    main()