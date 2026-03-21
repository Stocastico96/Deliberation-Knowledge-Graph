#!/usr/bin/env python3
"""
Batch convert all verbatim HTML files to JSON format
"""

import os
import sys
import subprocess
from pathlib import Path

# Directories
VERBATIM_DIR = Path("data/EU_parliament_debates/verbatim_2021_2024")
JSON_DIR = Path("data/EU_parliament_debates/json_2021_2024")
JSON_DIR.mkdir(parents=True, exist_ok=True)

CONVERTER_SCRIPT = Path("data/EU_parliament_debates/convert_verbatim_to_json.py")

def main():
    print("="*70)
    print("BATCH CONVERTING VERBATIM HTML TO JSON")
    print("="*70)

    # Get all HTML files
    html_files = sorted(VERBATIM_DIR.glob("verbatim_*.html"))

    print(f"\nFound {len(html_files)} HTML files to convert")
    print(f"Output directory: {JSON_DIR}")
    print()

    success_count = 0
    failed_count = 0
    failed_files = []

    for i, html_file in enumerate(html_files, 1):
        # Extract date from filename (verbatim_YYYY-MM-DD.html)
        date = html_file.stem.replace('verbatim_', '')

        # Output JSON filename
        json_file = JSON_DIR / f"debate_{date}.json"

        # Skip if already exists
        if json_file.exists():
            print(f"[{i}/{len(html_files)}] ⏭️  {date}: Already converted")
            success_count += 1
            continue

        print(f"[{i}/{len(html_files)}] 🔄 {date}...", end=" ")

        # Run converter script
        try:
            result = subprocess.run(
                ['python3', str(CONVERTER_SCRIPT), str(html_file), str(json_file)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print("✅")
                success_count += 1
            else:
                print(f"❌ Error")
                print(f"     {result.stderr[:100]}")
                failed_count += 1
                failed_files.append(date)

        except subprocess.TimeoutExpired:
            print(f"❌ Timeout")
            failed_count += 1
            failed_files.append(date)
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            failed_count += 1
            failed_files.append(date)

    # Summary
    print("\n" + "="*70)
    print("CONVERSION COMPLETE")
    print("="*70)
    print(f"Total files: {len(html_files)}")
    print(f"Successfully converted: {success_count}")
    print(f"Failed: {failed_count}")

    if failed_files:
        print(f"\nFailed files:")
        for date in failed_files[:10]:
            print(f"  - {date}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")

    # Count output files
    json_files = list(JSON_DIR.glob("debate_*.json"))
    print(f"\nJSON files created: {len(json_files)}")

    # Total size
    result = subprocess.run(['du', '-sh', str(JSON_DIR)], capture_output=True, text=True)
    if result.returncode == 0:
        size = result.stdout.split()[0]
        print(f"Total size: {size}")

    print(f"\n✅ All debates converted to JSON in: {JSON_DIR}")

if __name__ == '__main__':
    main()
