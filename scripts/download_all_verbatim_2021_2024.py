#!/usr/bin/env python3
"""
Download ALL verbatim reports for all sitting dates in our XML collection (2021-2024)
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

# Directories
XML_DIR = Path("data/EU_parliament_debates/raw_2021_2024")
OUTPUT_DIR = Path("data/EU_parliament_debates/verbatim_2021_2024")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_FILE = OUTPUT_DIR / "download_checkpoint.json"

HEADERS = {
    "User-Agent": "deliberation-ontology-research-1.0.0"
}

def extract_all_dates(xml_dir):
    """Extract ALL unique sitting dates from XML files"""
    print("="*70)
    print("EXTRACTING ALL SITTING DATES FROM XML FILES")
    print("="*70)

    ns = {
        'eli-dl': 'http://data.europa.eu/eli/eli-draft-legislation-ontology#'
    }

    all_dates = set()

    xml_files = sorted(xml_dir.glob("ep_speeches_*.xml"))
    print(f"\nProcessing {len(xml_files)} XML files...")

    for xml_file in xml_files:
        print(f"  {xml_file.name}...", end=" ")

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Find all activities and extract dates
            activities = root.findall('.//eli-dl:Activity', ns)

            for activity in activities:
                date_elem = activity.find('eli-dl:activity_date', ns)
                if date_elem is not None and date_elem.text:
                    all_dates.add(date_elem.text)

            print(f"✓ ({len(all_dates)} unique dates so far)")

        except Exception as e:
            print(f"✗ Error: {e}")

    return sorted(all_dates)

def load_checkpoint():
    """Load already downloaded dates"""
    if CHECKPOINT_FILE.exists():
        import json
        with open(CHECKPOINT_FILE, 'r') as f:
            return set(json.load(f).get('downloaded_dates', []))
    return set()

def save_checkpoint(downloaded_dates):
    """Save checkpoint"""
    import json
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'downloaded_dates': sorted(list(downloaded_dates)),
            'total': len(downloaded_dates)
        }, f, indent=2)

def download_verbatim(date, downloaded_dates):
    """Download verbatim HTML for a specific date"""

    # Skip if already downloaded
    if date in downloaded_dates:
        print(f"  ⏭️  {date}: Already downloaded")
        return True

    year, month, day = date.split("-")

    # Determine parliamentary term based on year
    year_int = int(year)
    if year_int >= 2024:
        term_num = "10"  # 10th term (2024-2029)
    elif year_int >= 2019:
        term_num = "9"   # 9th term (2019-2024)
    else:
        term_num = "8"   # 8th term (2014-2019)

    verbatim_url = f"https://www.europarl.europa.eu/doceo/document/CRE-{term_num}-{year}-{month}-{day}_EN.html"

    output_file = OUTPUT_DIR / f"verbatim_{date}.html"
    url_file = OUTPUT_DIR / f"verbatim_url_{date}.txt"

    print(f"\n  📥 {date}")
    print(f"     URL: {verbatim_url}")

    try:
        response = requests.get(verbatim_url, headers=HEADERS, timeout=60)

        if response.status_code == 200:
            # Save HTML
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            # Save URL reference
            with open(url_file, "w", encoding="utf-8") as f:
                f.write(verbatim_url)

            size_kb = len(response.content) / 1024
            print(f"     ✅ Saved: {size_kb:.1f} KB")

            downloaded_dates.add(date)
            return True
        else:
            print(f"     ❌ Not found (HTTP {response.status_code})")
            return False

    except Exception as e:
        print(f"     ❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("DOWNLOADING ALL EP VERBATIM REPORTS (2021-2024)")
    print("="*70)
    print(f"Output: {OUTPUT_DIR}")

    # Step 1: Extract all unique dates
    all_dates = extract_all_dates(XML_DIR)

    print("\n" + "="*70)
    print(f"Found {len(all_dates)} unique sitting dates")
    print("="*70)

    # Show date distribution by year
    year_counts = Counter(date[:4] for date in all_dates)
    for year in sorted(year_counts.keys()):
        print(f"  {year}: {year_counts[year]} dates")

    # Step 2: Load checkpoint
    downloaded_dates = load_checkpoint()
    if downloaded_dates:
        print(f"\nResuming: {len(downloaded_dates)} already downloaded")
        remaining = [d for d in all_dates if d not in downloaded_dates]
    else:
        remaining = all_dates

    if not remaining:
        print("\n✅ All dates already downloaded!")
        return

    print(f"\nWill download: {len(remaining)} verbatim reports")
    print(f"Estimated time: ~{len(remaining) * 2 / 60:.1f} minutes")

    # Step 3: Download verbatim HTML
    print("\n" + "="*70)
    print("DOWNLOADING VERBATIM REPORTS")
    print("="*70)

    success_count = 0
    failed_count = 0

    for i, date in enumerate(remaining, 1):
        print(f"\n[{i}/{len(remaining)}]", end=" ")

        if download_verbatim(date, downloaded_dates):
            success_count += 1
        else:
            failed_count += 1

        # Save checkpoint every 10 downloads
        if i % 10 == 0:
            save_checkpoint(downloaded_dates)

        # Rate limiting
        time.sleep(2)

    # Final save
    save_checkpoint(downloaded_dates)

    # Final summary
    print("\n" + "="*70)
    print("DOWNLOAD COMPLETE")
    print("="*70)
    print(f"Total dates in XML: {len(all_dates)}")
    print(f"Successfully downloaded: {success_count}")
    print(f"Failed (404 or error): {failed_count}")
    print(f"Total downloaded now: {len(downloaded_dates)}")

    # Count files
    html_files = list(OUTPUT_DIR.glob("verbatim_*.html"))
    print(f"\nVerbatim HTML files: {len(html_files)}")

    # Total size
    import subprocess
    result = subprocess.run(['du', '-sh', str(OUTPUT_DIR)], capture_output=True, text=True)
    if result.returncode == 0:
        size = result.stdout.split()[0]
        print(f"Total size: {size}")

    print(f"\n✅ All verbatim reports saved to: {OUTPUT_DIR}")
    print(f"\nNext steps:")
    print(f"  1. Convert HTML to JSON using existing scripts")
    print(f"  2. Filter by topic keywords in speech content")
    print(f"  3. Match with HYS consultations")

if __name__ == '__main__':
    main()
