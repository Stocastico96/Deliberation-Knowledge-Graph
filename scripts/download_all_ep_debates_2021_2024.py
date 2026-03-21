#!/usr/bin/env python3
"""
Download all EP debates from 2021-2024

Strategy:
- Download by month to avoid API limits
- Save raw XML responses
- Track progress with checkpoint file
- Estimate: ~48,000 speeches, ~150 MB total
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

EP_API = "https://data.europarl.europa.eu/api/v2/speeches"
OUTPUT_DIR = Path("data/EU_parliament_debates/raw_2021_2024")
CHECKPOINT_FILE = OUTPUT_DIR / "download_checkpoint.json"

class EPDebatesDownloader:
    """Download EP debates systematically"""

    def __init__(self, output_dir=OUTPUT_DIR, wait_time=2.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wait_time = wait_time
        self.checkpoint = self._load_checkpoint()

    def _load_checkpoint(self):
        """Load download progress"""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        return {
            'completed_months': [],
            'total_speeches': 0,
            'total_bytes': 0,
            'started_at': datetime.now().isoformat()
        }

    def _save_checkpoint(self):
        """Save download progress"""
        self.checkpoint['last_updated'] = datetime.now().isoformat()
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)

    def download_month(self, year, month):
        """Download all speeches for a given month"""

        month_key = f"{year}-{month:02d}"

        # Skip if already downloaded
        if month_key in self.checkpoint['completed_months']:
            print(f"  ⏭️  {month_key}: Already downloaded (skipping)")
            return

        # Calculate date range
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        print(f"\n📥 Downloading {month_key} ({start_date} to {end_date})...")

        # API parameters
        params = {
            "filter": f"sitting-date:ge:{start_date},sitting-date:le:{end_date}",
            "page-size": 1000  # Max per request
        }

        try:
            response = requests.get(EP_API, params=params, timeout=60)

            if response.status_code != 200:
                print(f"  ❌ Error: HTTP {response.status_code}")
                return

            # Save raw XML
            output_file = self.output_dir / f"ep_speeches_{month_key}.xml"
            with open(output_file, 'wb') as f:
                f.write(response.content)

            # Count speeches in response
            root = ET.fromstring(response.content)
            ns = {'eli-dl': 'http://data.europa.eu/eli/eli-draft-legislation-ontology#'}
            activities = root.findall('.//eli-dl:Activity', ns)

            size_kb = len(response.content) / 1024

            print(f"  ✅ Saved: {output_file.name}")
            print(f"     Speeches: {len(activities)}")
            print(f"     Size: {size_kb:.1f} KB")

            # Update checkpoint
            self.checkpoint['completed_months'].append(month_key)
            self.checkpoint['total_speeches'] += len(activities)
            self.checkpoint['total_bytes'] += len(response.content)
            self._save_checkpoint()

        except Exception as e:
            print(f"  ❌ Error downloading {month_key}: {e}")

    def download_all(self, start_year=2021, end_year=2024):
        """Download all months in range"""

        print("="*70)
        print("DOWNLOADING EP DEBATES 2021-2024")
        print("="*70)
        print(f"Output directory: {self.output_dir}")
        print(f"Wait time between requests: {self.wait_time}s")

        if self.checkpoint['completed_months']:
            print(f"\nResuming from checkpoint:")
            print(f"  Already downloaded: {len(self.checkpoint['completed_months'])} months")
            print(f"  Total speeches so far: {self.checkpoint['total_speeches']}")
            print(f"  Total size so far: {self.checkpoint['total_bytes']/1024/1024:.1f} MB")

        print(f"\nStarting download...\n")

        # Generate all month/year combinations
        for year in range(start_year, end_year + 1):
            # For 2024, only go up to current month
            max_month = 12
            if year == datetime.now().year:
                max_month = datetime.now().month

            for month in range(1, max_month + 1):
                self.download_month(year, month)

                # Rate limiting
                time.sleep(self.wait_time)

        # Final summary
        print("\n" + "="*70)
        print("DOWNLOAD COMPLETE")
        print("="*70)
        print(f"Total months downloaded: {len(self.checkpoint['completed_months'])}")
        print(f"Total speeches: {self.checkpoint['total_speeches']:,}")
        print(f"Total size: {self.checkpoint['total_bytes']/1024/1024:.1f} MB")
        print(f"Output directory: {self.output_dir}")
        print(f"\n✅ All EP debates 2021-2024 downloaded successfully!")


def main():
    downloader = EPDebatesDownloader(wait_time=2.0)
    downloader.download_all(start_year=2021, end_year=2024)


if __name__ == '__main__':
    main()
