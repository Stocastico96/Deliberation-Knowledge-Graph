#!/usr/bin/env python3
"""
Collegamento Ares reference → CELEX identifier

Dato un numero Ares (es. Ares(2023)1234567), cerca il documento CELEX collegato
tramite EUR-Lex search API o SPARQL endpoint.

Output: JSON cache con mapping Ares → CELEX
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict
import requests
from urllib.parse import quote

# EUR-Lex endpoints
EURLEX_SEARCH_BASE = "https://eur-lex.europa.eu/search.html"
EURLEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"

class AresCelexLinker:
    """Links Ares references to CELEX identifiers"""

    def __init__(self, cache_file='ares_celex_cache.json', wait_time=1.0):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.wait_time = wait_time

    def _load_cache(self) -> Dict:
        """Load existing cache"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def extract_ares_number(self, reference: str) -> Optional[str]:
        """
        Extract Ares number from various formats

        Examples:
        - Ares(2023)1234567 → Ares(2023)1234567
        - ARES(2023)1234567 → Ares(2023)1234567
        """
        match = re.search(r'[Aa]res\((\d{4})\)(\d+)', reference)
        if match:
            year, number = match.groups()
            return f"Ares({year}){number}"
        return None

    def search_eurlex_html(self, ares_ref: str) -> Optional[Dict]:
        """
        Search EUR-Lex via HTML search (fallback method)

        Returns dict with CELEX if found
        """
        try:
            # EUR-Lex search URL with Ares reference
            search_query = quote(ares_ref)
            url = f"{EURLEX_SEARCH_BASE}?qid=&text={search_query}&scope=EURLEX&type=quick"

            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                # Parse HTML for CELEX numbers (very basic extraction)
                # Look for CELEX pattern: 32023R1234, 52023PC0456, etc.
                celex_pattern = r'[3-5]\d{4}[A-Z]{1,2}\d{4,6}'
                matches = re.findall(celex_pattern, response.text)

                if matches:
                    # Return first match (most relevant)
                    return {
                        'ares': ares_ref,
                        'celex': matches[0],
                        'method': 'html_search',
                        'all_matches': matches[:5]  # Top 5
                    }

            return None

        except Exception as e:
            print(f"Error searching EUR-Lex HTML: {e}")
            return None

    def search_eurlex_sparql(self, ares_ref: str) -> Optional[Dict]:
        """
        Search EUR-Lex via SPARQL endpoint

        More reliable but may have rate limits
        """
        query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT ?celex ?title WHERE {{
          ?work cdm:resource_legal_id_ares ?ares ;
                cdm:resource_legal_id_celex ?celex ;
                cdm:work_has_expression ?expr .
          ?expr cdm:expression_title ?title .

          FILTER(CONTAINS(STR(?ares), "{ares_ref}"))
        }}
        LIMIT 10
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
                    celex = bindings[0]['celex']['value']
                    title = bindings[0].get('title', {}).get('value', '')

                    return {
                        'ares': ares_ref,
                        'celex': celex,
                        'title': title,
                        'method': 'sparql',
                        'all_results': [b['celex']['value'] for b in bindings]
                    }

            return None

        except Exception as e:
            print(f"Error with SPARQL query: {e}")
            return None

    def link_ares_to_celex(self, reference: str, force=False) -> Optional[Dict]:
        """
        Main method to link Ares to CELEX

        Args:
            reference: Ares reference (any format)
            force: Bypass cache

        Returns:
            Dict with mapping info or None
        """
        ares_ref = self.extract_ares_number(reference)
        if not ares_ref:
            return None

        # Check cache
        if not force and ares_ref in self.cache:
            return self.cache[ares_ref]

        print(f"Searching CELEX for {ares_ref}...")

        # Try SPARQL first (more reliable)
        result = self.search_eurlex_sparql(ares_ref)

        # Fallback to HTML search
        if not result:
            time.sleep(self.wait_time)
            result = self.search_eurlex_html(ares_ref)

        # Cache result (even if None)
        if result:
            self.cache[ares_ref] = result
            self._save_cache()
            print(f"  → Found CELEX: {result['celex']}")
        else:
            self.cache[ares_ref] = {'ares': ares_ref, 'celex': None, 'error': 'not_found'}
            self._save_cache()
            print(f"  → No CELEX found")

        return result

def main():
    parser = argparse.ArgumentParser(
        description='Link Ares references to CELEX identifiers'
    )
    parser.add_argument(
        'ares_references',
        nargs='*',
        help='Ares references to look up (e.g., Ares(2023)1234567)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='File with Ares references (one per line)'
    )
    parser.add_argument(
        '--cache',
        type=str,
        default='ares_celex_cache.json',
        help='Cache file path'
    )
    parser.add_argument(
        '--wait',
        type=float,
        default=1.0,
        help='Wait time between requests (seconds)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force refresh (ignore cache)'
    )

    args = parser.parse_args()

    linker = AresCelexLinker(cache_file=args.cache, wait_time=args.wait)

    # Collect references
    references = list(args.ares_references)

    if args.file:
        with open(args.file, 'r') as f:
            references.extend([line.strip() for line in f if line.strip()])

    if not references:
        print("No Ares references provided. Use --help for usage.")
        return

    print(f"Processing {len(references)} Ares references...\n")

    results = []
    for ref in references:
        result = linker.link_ares_to_celex(ref, force=args.force)
        if result:
            results.append(result)
        time.sleep(args.wait)

    # Summary
    print(f"\n{'='*60}")
    print(f"Processed: {len(references)}")
    print(f"Found CELEX: {len([r for r in results if r.get('celex')])}")
    print(f"Cache file: {linker.cache_file}")

if __name__ == '__main__':
    main()
