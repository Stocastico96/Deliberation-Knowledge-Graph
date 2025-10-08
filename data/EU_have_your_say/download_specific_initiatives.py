#!/usr/bin/env python3
"""
Download specific EU Have Your Say initiatives using the current API
"""

import requests
import json
import csv
import time
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

class HaveYourSayDownloader:
    def __init__(self, db_path="eu_haveyoursay_specific.db"):
        self.api_base = "https://ec.europa.eu/info/law/better-regulation/brpapi"
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        self.init_db()

    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS initiatives
                     (id INTEGER PRIMARY KEY,
                      data TEXT,
                      timestamp TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      publication_id INTEGER,
                      initiative_id INTEGER,
                      data TEXT,
                      timestamp TEXT)''')

        conn.commit()
        conn.close()

    def get_initiative(self, initiative_id):
        """Get initiative data from API"""
        url = f"{self.api_base}/groupInitiatives/{initiative_id}"
        print(f"Fetching initiative {initiative_id}...")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            print(f"  ✓ Got initiative data")
            return data
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return None

    def get_feedback(self, publication_id, page=0, size=100):
        """Get feedback for a publication"""
        # Use correct API endpoint (not brpapi)
        url = "https://ec.europa.eu/info/law/better-regulation/api/allFeedback"
        params = {
            'publicationId': publication_id,
            'page': page,
            'size': size
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  ✗ Error getting feedback: {e}")
            return None

    def get_all_feedback(self, publication_id):
        """Get all feedback for a publication with pagination"""
        all_feedback = []
        page = 0

        while True:
            data = self.get_feedback(publication_id, page=page)
            if not data:
                break

            content = data.get('content', [])
            if not content:
                break

            all_feedback.extend(content)

            # Check if there are more pages
            if data.get('last', True):
                break

            page += 1
            time.sleep(0.5)

        return all_feedback

    def download_initiative(self, initiative_id):
        """Download initiative and all its feedback"""
        # Get initiative data
        initiative_data = self.get_initiative(initiative_id)
        if not initiative_data:
            return False

        # Save to database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("INSERT OR REPLACE INTO initiatives VALUES (?, ?, ?)",
                  (initiative_id, json.dumps(initiative_data), datetime.now().isoformat()))

        # Get publications from initiative
        publications = initiative_data.get('publications', [])

        print(f"  Found {len(publications)} publications")

        # Download feedback for each publication
        total_feedback = 0
        for pub in publications:
            pub_id = pub.get('id')
            if not pub_id:
                continue

            print(f"  Getting feedback for publication {pub_id}...")
            feedback = self.get_all_feedback(pub_id)

            print(f"    ✓ Got {len(feedback)} feedback items")
            total_feedback += len(feedback)

            # Save feedback to database
            for fb in feedback:
                c.execute("INSERT INTO feedback (publication_id, initiative_id, data, timestamp) VALUES (?, ?, ?, ?)",
                          (pub_id, initiative_id, json.dumps(fb), datetime.now().isoformat()))

            time.sleep(1)

        conn.commit()
        conn.close()

        print(f"  ✓ Total feedback collected: {total_feedback}")
        return True

    def export_to_csv(self, output_dir="csv_export"):
        """Export database to CSV files"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        conn = sqlite3.connect(self.db_path)

        # Export initiatives
        print("\nExporting initiatives...")
        initiatives = []
        for row in conn.execute("SELECT id, data FROM initiatives"):
            init_id, data_json = row
            data = json.loads(data_json)

            initiatives.append({
                'id': init_id,
                'reference': data.get('reference', ''),
                'shortTitle': data.get('shortTitle', ''),
                'dossierSummary': data.get('dossierSummary', ''),
                'publications_count': len(data.get('publications', []))
            })

        if initiatives:
            with open(output_dir / "initiatives.csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'reference', 'shortTitle', 'dossierSummary', 'publications_count'])
                writer.writeheader()
                writer.writerows(initiatives)
            print(f"  ✓ Exported {len(initiatives)} initiatives")

        # Export feedback
        print("Exporting feedback...")
        feedback_list = []
        for row in conn.execute("SELECT publication_id, initiative_id, data FROM feedback"):
            pub_id, init_id, data_json = row
            data = json.loads(data_json)

            feedback_list.append({
                'id': data.get('id', ''),
                'publication_id': pub_id,
                'initiative_id': init_id,
                'dateFeedback': data.get('dateFeedback', ''),
                'language': data.get('language', ''),
                'country': data.get('country', ''),
                'userType': data.get('userType', ''),
                'companySize': data.get('companySize', ''),
                'organization': data.get('organization', ''),
                'firstName': data.get('firstName', ''),
                'surname': data.get('surname', ''),
                'feedback': data.get('feedback', '')[:500] if data.get('feedback') else ''  # Truncate for CSV
            })

        if feedback_list:
            with open(output_dir / "feedback.csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=feedback_list[0].keys())
                writer.writeheader()
                writer.writerows(feedback_list)
            print(f"  ✓ Exported {len(feedback_list)} feedback items")

        conn.close()
        print(f"\nCSV files saved to: {output_dir.absolute()}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_specific_initiatives.py <initiative_id1> [initiative_id2] ...")
        print("\nExample:")
        print("  python download_specific_initiatives.py 14622 13682 13761")
        sys.exit(1)

    initiative_ids = [int(id) for id in sys.argv[1:]]

    print(f"{'='*60}")
    print(f"EU Have Your Say Downloader")
    print(f"{'='*60}")
    print(f"Initiatives to download: {len(initiative_ids)}")
    print(f"{'='*60}\n")

    downloader = HaveYourSayDownloader()

    results = []
    for i, init_id in enumerate(initiative_ids, 1):
        print(f"[{i}/{len(initiative_ids)}] Processing initiative {init_id}")
        success = downloader.download_initiative(init_id)
        results.append({'id': init_id, 'success': success})
        time.sleep(2)

    print(f"\n{'='*60}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"Successful: {sum(1 for r in results if r['success'])}/{len(results)}")
    print(f"Database: {downloader.db_path}")

    # Export to CSV
    print(f"\n{'='*60}")
    downloader.export_to_csv()
    print(f"{'='*60}")


if __name__ == "__main__":
    main()