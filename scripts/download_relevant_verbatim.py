#!/usr/bin/env python3
"""
Extract relevant debate dates from XML API responses and download verbatim HTML
for AI, Deforestation, Tobacco, COVID topics
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

# Directories
XML_DIR = Path("data/EU_parliament_debates/raw_2021_2024")
OUTPUT_DIR = Path("data/EU_parliament_debates/verbatim_2021_2024")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "deliberation-ontology-research-1.0.0"
}

# Topics we're interested in
KEYWORDS = {
    'ai': ['artificial intelligence', 'AI act', 'AI regulation', 'AI white paper'],
    'deforestation': ['deforestation', 'forest degradation', 'due diligence'],
    'tobacco': ['tobacco', 'smoking', 'tobacco products'],
    'covid': ['COVID', 'coronavirus', 'pandemic', 'health certificate', 'digital certificate']
}

def extract_relevant_dates(xml_dir):
    """
    Parse all XML files and extract dates with relevant debates
    Returns: dict of {date: [topics]}
    """
    print("="*70)
    print("EXTRACTING RELEVANT DATES FROM XML FILES")
    print("="*70)

    ns = {
        'eli-dl': 'http://data.europa.eu/eli/eli-draft-legislation-ontology#',
        'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    relevant_dates = defaultdict(set)

    xml_files = sorted(xml_dir.glob("ep_speeches_*.xml"))
    print(f"\nProcessing {len(xml_files)} XML files...")

    for xml_file in xml_files:
        print(f"\n  Processing {xml_file.name}...")

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Find all activities
            activities = root.findall('.//eli-dl:Activity', ns)

            for activity in activities:
                # Get English label
                label_elem = activity.find('eli-dl:activity_label[@xml:lang="en"]', ns)
                if label_elem is None or not label_elem.text:
                    continue

                label_lower = label_elem.text.lower()

                # Get date
                date_elem = activity.find('eli-dl:activity_date', ns)
                if date_elem is None or not date_elem.text:
                    continue

                date = date_elem.text

                # Check if label matches any of our keywords
                for topic, keywords in KEYWORDS.items():
                    if any(kw.lower() in label_lower for kw in keywords):
                        relevant_dates[date].add(topic)

        except Exception as e:
            print(f"    Error parsing {xml_file.name}: {e}")

    return relevant_dates

def download_verbatim(date, topics):
    """Download verbatim HTML for a specific date"""
    year, month, day = date.split("-")

    # Determine parliamentary term based on year
    if int(year) >= 2024:
        term_num = "10"  # 10th term (2024-2029)
    elif int(year) >= 2019:
        term_num = "9"   # 9th term (2019-2024)
    else:
        term_num = "8"   # 8th term (2014-2019)

    verbatim_url = f"https://www.europarl.europa.eu/doceo/document/CRE-{term_num}-{year}-{month}-{day}_EN.html"

    output_file = OUTPUT_DIR / f"verbatim_{date}.html"
    url_file = OUTPUT_DIR / f"verbatim_{date}.txt"

    # Skip if already downloaded
    if output_file.exists():
        print(f"  ⏭️  {date}: Already downloaded")
        return True

    print(f"\n  📥 {date} ({', '.join(sorted(topics))})")
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
            return True
        else:
            print(f"     ❌ Not found (HTTP {response.status_code})")
            return False

    except Exception as e:
        print(f"     ❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("DOWNLOADING RELEVANT EP VERBATIM REPORTS (2021-2024)")
    print("="*70)
    print(f"Topics: AI, Deforestation, Tobacco, COVID")
    print(f"Output: {OUTPUT_DIR}")

    # Step 1: Extract relevant dates from XML
    relevant_dates = extract_relevant_dates(XML_DIR)

    if not relevant_dates:
        print("\n❌ No relevant dates found!")
        return

    # Print summary by topic
    print("\n" + "="*70)
    print("RELEVANT DATES FOUND")
    print("="*70)

    topic_counts = defaultdict(int)
    for date, topics in relevant_dates.items():
        for topic in topics:
            topic_counts[topic] += 1

    print("\nDates by topic:")
    for topic, count in sorted(topic_counts.items()):
        print(f"  {topic.upper()}: {count} dates")

    print(f"\nTotal unique dates: {len(relevant_dates)}")

    # Step 2: Download verbatim HTML
    print("\n" + "="*70)
    print("DOWNLOADING VERBATIM REPORTS")
    print("="*70)

    success_count = 0
    failed_dates = []

    for date in sorted(relevant_dates.keys()):
        topics = relevant_dates[date]

        if download_verbatim(date, topics):
            success_count += 1
        else:
            failed_dates.append(date)

        # Rate limiting
        time.sleep(2)

    # Final summary
    print("\n" + "="*70)
    print("DOWNLOAD COMPLETE")
    print("="*70)
    print(f"Successfully downloaded: {success_count}/{len(relevant_dates)}")

    if failed_dates:
        print(f"\nFailed dates ({len(failed_dates)}):")
        for date in failed_dates[:10]:  # Show first 10
            print(f"  - {date}")
        if len(failed_dates) > 10:
            print(f"  ... and {len(failed_dates) - 10} more")

    print(f"\n✅ Verbatim HTML files saved to: {OUTPUT_DIR}")
    print(f"\nNext steps:")
    print(f"  1. Convert HTML to JSON: python convert_verbatim_to_json.py")
    print(f"  2. Filter by topic keywords")
    print(f"  3. Match with HYS consultations")

if __name__ == '__main__':
    main()
