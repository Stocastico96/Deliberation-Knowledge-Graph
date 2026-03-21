#!/usr/bin/env python3
"""
Scarica atti legislativi UE da EUR-Lex dato CELEX

Input: lista di CELEX identifiers
Output: File XML/HTML strutturati in data/eurlex/acts/
"""

import argparse
import json
import time
from pathlib import Path
import requests
from typing import Optional, Dict

EURLEX_BASE = "https://eur-lex.europa.eu/legal-content"

class LegislationFetcher:
    """Fetch EU legislation from EUR-Lex"""

    def __init__(self, output_dir='data/eurlex/acts', wait_time=1.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wait_time = wait_time

    def fetch_document(self, celex: str, format='xml') -> Optional[Dict]:
        """
        Fetch document from EUR-Lex

        Args:
            celex: CELEX identifier (e.g., 32023R1234)
            format: 'xml', 'html', or 'pdf'

        Returns:
            Dict with metadata and content
        """
        # Construct URL
        # Format: https://eur-lex.europa.eu/legal-content/AUTO/?uri=CELEX:32023R1234&format=XML
        url = f"{EURLEX_BASE}/AUTO/?uri=CELEX:{celex}"

        # Add format
        if format == 'xml':
            url += "&format=XML"
        elif format == 'html':
            url += "&format=HTML"

        print(f"Fetching {celex} ({format})...")

        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                # Save to file
                ext = 'xml' if format == 'xml' else 'html'
                output_file = self.output_dir / f"{celex}.{ext}"

                with open(output_file, 'wb') as f:
                    f.write(response.content)

                # Metadata
                metadata = {
                    'celex': celex,
                    'format': format,
                    'file': str(output_file),
                    'size': len(response.content),
                    'status': 'success'
                }

                # Save metadata
                meta_file = self.output_dir / f"{celex}.json"
                with open(meta_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

                print(f"  → Saved to {output_file} ({len(response.content)} bytes)")
                return metadata

            else:
                print(f"  → Error: HTTP {response.status_code}")
                return {'celex': celex, 'status': 'error', 'code': response.status_code}

        except Exception as e:
            print(f"  → Error: {e}")
            return {'celex': celex, 'status': 'error', 'message': str(e)}

    def fetch_multiple(self, celex_list, format='xml'):
        """Fetch multiple documents"""
        results = []

        for celex in celex_list:
            result = self.fetch_document(celex, format=format)
            if result:
                results.append(result)
            time.sleep(self.wait_time)

        return results

def main():
    parser = argparse.ArgumentParser(
        description='Fetch EU legislation from EUR-Lex'
    )
    parser.add_argument(
        'celex',
        nargs='*',
        help='CELEX identifiers to fetch'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='File with CELEX identifiers (one per line)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/eurlex/acts',
        help='Output directory'
    )
    parser.add_argument(
        '--format',
        type=str,
        default='xml',
        choices=['xml', 'html'],
        help='Document format'
    )
    parser.add_argument(
        '--wait',
        type=float,
        default=1.0,
        help='Wait time between requests'
    )

    args = parser.parse_args()

    # Collect CELEX identifiers
    celex_list = list(args.celex)

    if args.file:
        with open(args.file, 'r') as f:
            celex_list.extend([line.strip() for line in f if line.strip()])

    if not celex_list:
        print("No CELEX identifiers provided. Use --help for usage.")
        return

    fetcher = LegislationFetcher(output_dir=args.output, wait_time=args.wait)

    print(f"Fetching {len(celex_list)} documents...\n")
    results = fetcher.fetch_multiple(celex_list, format=args.format)

    # Summary
    success = len([r for r in results if r.get('status') == 'success'])
    print(f"\n{'='*60}")
    print(f"Total: {len(results)}")
    print(f"Success: {success}")
    print(f"Failed: {len(results) - success}")
    print(f"Output: {fetcher.output_dir}")

if __name__ == '__main__':
    main()
