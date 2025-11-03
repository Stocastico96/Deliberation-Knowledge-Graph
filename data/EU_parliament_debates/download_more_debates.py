#!/usr/bin/env python3
"""
Download more EU Parliament debates from available plenary sessions 2024-2025
"""
import requests
import json
import os
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "deliberation-ontology-dev-1.0.0"
}

# Create directory
os.makedirs("debates_2024_2025", exist_ok=True)

def download_verbatim_report(date):
    """Download verbatim report for a specific date"""
    year, month, day = date.split("-")
    term_num = "10"  # 10th parliamentary term

    # URL for the verbatim HTML document
    verbatim_url = f"https://www.europarl.europa.eu/doceo/document/CRE-{term_num}-{year}-{month}-{day}_EN.html"
    print(f"\nDownloading: {verbatim_url}")

    try:
        response = requests.get(verbatim_url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            print(f"✓ Found verbatim for {date}")

            # Save HTML
            html_file = f"debates_2024_2025/verbatim_{date}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"  Saved: {html_file}")
            return True
        else:
            print(f"✗ Not found (Status: {response.status_code})")
            return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def main():
    # Plenary session dates from 2024-2025
    # Based on the typical EP calendar (first full week of month in Strasbourg)
    plenary_dates = [
        # October 2025
        "2025-10-20", "2025-10-21", "2025-10-22", "2025-10-23",
        "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09",
        # September 2025
        "2025-09-08", "2025-09-09", "2025-09-10", "2025-09-11",
        # July 2025
        "2025-07-07", "2025-07-08", "2025-07-09", "2025-07-10",
        # June 2025
        "2025-06-16", "2025-06-17", "2025-06-18", "2025-06-19",
        # May 2025
        "2025-05-21", "2025-05-22",
        # April 2025
        "2025-04-07", "2025-04-08", "2025-04-09", "2025-04-10",
        # 2024 dates
        "2024-12-09", "2024-12-10", "2024-12-11", "2024-12-12",
        "2024-11-25", "2024-11-26", "2024-11-27", "2024-11-28",
        "2024-10-21", "2024-10-22", "2024-10-23", "2024-10-24",
        "2024-09-16", "2024-09-17", "2024-09-18", "2024-09-19",
        "2024-07-22", "2024-07-23", "2024-07-24", "2024-07-25",
    ]

    print(f"Attempting to download {len(plenary_dates)} verbatim reports...")

    success_count = 0
    for date in plenary_dates:
        if download_verbatim_report(date):
            success_count += 1
        time.sleep(1)  # Rate limiting

    print(f"\n{'='*60}")
    print(f"Downloaded {success_count}/{len(plenary_dates)} verbatim reports")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
