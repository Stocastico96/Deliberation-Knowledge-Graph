#!/usr/bin/env python3
"""
Find relevant legislation and debates for pilot study.

Strategy:
1. Search EUR-Lex for completed legislation by topic keywords
2. Extract CELEX, procedure reference, dates
3. Query EP API for debates using procedure reference
4. Match back to HYS consultations via Ares references

Output: Mapping of CELEX → EP debates → HYS consultations
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

# EUR-Lex SPARQL endpoint
EURLEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
EP_API_BASE = "https://data.europarl.europa.eu/api/v2"

class LegislationFinder:
    """Find relevant EU legislation and associated debates"""

    def __init__(self, wait_time=1.0):
        self.wait_time = wait_time
        self.results = []

    def search_eurlex_by_keyword(self, keyword: str, year_from: int = 2020,
                                  year_to: int = 2024, limit: int = 10) -> List[Dict]:
        """
        Search EUR-Lex for legislation containing keyword

        Returns list of acts with CELEX, title, date, type
        """
        query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?celex ?title ?date ?type ?procedure WHERE {{
          ?work cdm:resource_legal_id_celex ?celex ;
                cdm:work_has_expression ?expr ;
                cdm:work_date_document ?date ;
                cdm:resource_legal_type ?type .

          ?expr cdm:expression_title ?title .

          OPTIONAL {{ ?work cdm:resource_legal_id_sector ?procedure }}

          FILTER(CONTAINS(LCASE(?title), LCASE("{keyword}")))
          FILTER(?date >= "{year_from}-01-01"^^xsd:date && ?date <= "{year_to}-12-31"^^xsd:date)
          FILTER(LANG(?title) = "en")

          # Focus on Regulations, Directives, Decisions
          FILTER(REGEX(STR(?type), "(REG|DIR|DEC)"))
        }}
        ORDER BY DESC(?date)
        LIMIT {limit}
        """

        try:
            print(f"\nSearching EUR-Lex for '{keyword}' ({year_from}-{year_to})...")

            response = requests.post(
                EURLEX_SPARQL,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=60
            )

            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                return []

            results = response.json()
            bindings = results.get('results', {}).get('bindings', [])

            legislation = []
            for binding in bindings:
                celex = binding['celex']['value']
                title = binding['title']['value']
                date = binding['date']['value']
                leg_type = binding.get('type', {}).get('value', '')
                procedure = binding.get('procedure', {}).get('value', '')

                legislation.append({
                    'celex': celex,
                    'title': title,
                    'date': date,
                    'type': leg_type,
                    'procedure': procedure,
                    'keyword': keyword
                })

            print(f"  Found {len(legislation)} acts")
            return legislation

        except Exception as e:
            print(f"Error querying EUR-Lex: {e}")
            return []

    def get_ep_procedure_from_celex(self, celex: str) -> Optional[str]:
        """
        Extract EP procedure reference from CELEX

        CELEX format: 32024R1689 → Year 2024, Regulation
        Try to find COD procedure in EUR-Lex
        """
        query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

        SELECT DISTINCT ?procedure WHERE {{
          ?work cdm:resource_legal_id_celex "{celex}" ;
                cdm:work_is_about_concept_procedure-reference ?proc .
          ?proc skos:notation ?procedure .
        }}
        LIMIT 1
        """

        try:
            response = requests.post(
                EURLEX_SPARQL,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get('results', {}).get('bindings', [])
                if bindings:
                    return bindings[0]['procedure']['value']

            return None

        except Exception as e:
            print(f"Error getting procedure: {e}")
            return None

    def count_ep_speeches_by_procedure(self, procedure_ref: str) -> int:
        """
        Count EP speeches for a given procedure reference

        Example: COD/2021/0106 (AI Act)
        """
        url = f"{EP_API_BASE}/speeches"
        params = {
            "filter": f"procedure-reference:eq:{procedure_ref}",
            "page-size": 1
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                # Parse XML to count total results
                root = ET.fromstring(response.content)
                ns = {'eli-dl': 'http://data.europa.eu/eli/eli-draft-legislation-ontology#'}
                activities = root.findall('.//eli-dl:Activity', ns)

                # Note: this is just first page, actual count might be higher
                return len(activities)

            return 0

        except Exception as e:
            print(f"Error counting speeches: {e}")
            return 0

    def find_legislation_for_topics(self, topics: List[str]) -> List[Dict]:
        """
        Main method: find legislation for multiple topics
        """
        all_results = []

        for topic in topics:
            print(f"\n{'='*70}")
            print(f"Topic: {topic}")
            print(f"{'='*70}")

            legislation = self.search_eurlex_by_keyword(topic, year_from=2020, year_to=2024, limit=5)

            for act in legislation:
                celex = act['celex']

                # Try to get EP procedure
                print(f"\n  Checking {celex}: {act['title'][:60]}...")
                procedure = self.get_ep_procedure_from_celex(celex)

                if procedure:
                    print(f"    Procedure: {procedure}")

                    # Count speeches
                    time.sleep(self.wait_time)
                    speech_count = self.count_ep_speeches_by_procedure(procedure)
                    print(f"    EP Speeches: {speech_count}+")

                    act['ep_procedure'] = procedure
                    act['ep_speeches_count'] = speech_count
                else:
                    print(f"    No EP procedure found")
                    act['ep_procedure'] = None
                    act['ep_speeches_count'] = 0

                all_results.append(act)
                time.sleep(self.wait_time)

        return all_results


def main():
    """Run legislation finder for our pilot study topics"""

    # Topics based on our HYS consultations analysis
    topics = [
        "artificial intelligence",
        "deforestation",
        "tobacco",
        "COVID certificate"
    ]

    finder = LegislationFinder(wait_time=2.0)

    print("="*70)
    print("FINDING RELEVANT LEGISLATION FOR PILOT STUDY")
    print("="*70)
    print(f"Topics: {', '.join(topics)}")
    print(f"Period: 2020-2024")
    print()

    results = finder.find_legislation_for_topics(topics)

    # Save results
    output_file = '/tmp/legislation_mapping.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total acts found: {len(results)}")
    print(f"Acts with EP procedures: {len([r for r in results if r.get('ep_procedure')])}")
    print(f"Acts with EP speeches: {len([r for r in results if r.get('ep_speeches_count', 0) > 0])}")
    print(f"\nResults saved to: {output_file}")

    # Print top candidates
    print("\n" + "="*70)
    print("TOP CANDIDATES (with EP debates)")
    print("="*70)

    candidates = [r for r in results if r.get('ep_speeches_count', 0) > 0]
    candidates.sort(key=lambda x: x.get('ep_speeches_count', 0), reverse=True)

    for i, act in enumerate(candidates[:10], 1):
        print(f"\n{i}. {act['title'][:70]}")
        print(f"   CELEX: {act['celex']}")
        print(f"   Procedure: {act.get('ep_procedure', 'N/A')}")
        print(f"   Speeches: {act.get('ep_speeches_count', 0)}+")
        print(f"   Date: {act['date']}")
        print(f"   Keyword: {act['keyword']}")


if __name__ == '__main__':
    main()
