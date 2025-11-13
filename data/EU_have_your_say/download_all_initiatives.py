#!/usr/bin/env python3
"""
Download ALL EU Have Your Say initiatives using the API
Scans all available initiatives and downloads them with their feedback
"""

import requests
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

class HaveYourSayFullDownloader:
    def __init__(self, db_path="eu_haveyoursay_complete.db"):
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
                      reference TEXT,
                      title TEXT,
                      data TEXT,
                      timestamp TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      publication_id INTEGER,
                      initiative_id INTEGER,
                      data TEXT,
                      timestamp TEXT)''')

        c.execute('''CREATE INDEX IF NOT EXISTS idx_initiative_id ON feedback(initiative_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_publication_id ON feedback(publication_id)''')

        conn.commit()
        conn.close()

    def search_all_initiatives(self, page=0, size=100):
        """Search for all initiatives with pagination"""
        url = f"{self.api_base}/groupInitiatives"
        params = {
            'page': page,
            'size': size,
            'sort': 'id,desc'  # Get newest first
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  ✗ Error searching initiatives: {e}")
            return None

    def get_all_initiative_ids(self):
        """Get all initiative IDs from the API"""
        print("Scanning all available initiatives...")
        all_ids = []
        page = 0

        while True:
            print(f"  Fetching page {page}...")
            data = self.search_all_initiatives(page=page, size=100)

            if not data:
                break

            content = data.get('content', [])
            if not content:
                break

            # Extract IDs
            for item in content:
                init_id = item.get('id')
                if init_id:
                    all_ids.append({
                        'id': init_id,
                        'reference': item.get('reference', ''),
                        'title': item.get('shortTitle', '')
                    })

            print(f"    Found {len(content)} initiatives on this page")

            # Check if there are more pages
            if data.get('last', True):
                break

            page += 1
            time.sleep(0.5)  # Be respectful

        print(f"\n✓ Total initiatives found: {len(all_ids)}")
        return all_ids

    def get_initiative(self, initiative_id):
        """Get initiative data from API"""
        url = f"{self.api_base}/groupInitiatives/{initiative_id}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  ✗ Error fetching initiative {initiative_id}: {e}")
            return None

    def get_feedback(self, publication_id, page=0, size=100):
        """Get feedback for a publication"""
        url = f"{self.api_base}/feedback"
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
            print(f"    ✗ Error getting feedback: {e}")
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
            time.sleep(0.3)

        return all_feedback

    def download_initiative(self, initiative_id, reference='', title=''):
        """Download initiative and all its feedback"""
        print(f"  [{reference}] {title[:50]}...")

        # Check if already downloaded
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id FROM initiatives WHERE id = ?", (initiative_id,))
        if c.fetchone():
            print(f"    ⊙ Already downloaded, skipping")
            conn.close()
            return True

        # Get initiative data
        initiative_data = self.get_initiative(initiative_id)
        if not initiative_data:
            conn.close()
            return False

        # Save to database
        c.execute("INSERT OR REPLACE INTO initiatives VALUES (?, ?, ?, ?, ?)",
                  (initiative_id, reference, title, json.dumps(initiative_data),
                   datetime.now().isoformat()))

        # Get publications from initiative
        publications = initiative_data.get('publications', [])
        print(f"    Publications: {len(publications)}")

        # Download feedback for each publication
        total_feedback = 0
        for pub in publications:
            pub_id = pub.get('id')
            if not pub_id:
                continue

            feedback = self.get_all_feedback(pub_id)
            total_feedback += len(feedback)

            # Save feedback to database
            for fb in feedback:
                c.execute("INSERT INTO feedback (publication_id, initiative_id, data, timestamp) VALUES (?, ?, ?, ?)",
                          (pub_id, initiative_id, json.dumps(fb), datetime.now().isoformat()))

            time.sleep(0.5)

        conn.commit()
        conn.close()

        print(f"    ✓ Feedback: {total_feedback}")
        return True

    def export_stats(self):
        """Print statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM initiatives")
        init_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM feedback")
        feedback_count = c.fetchone()[0]

        conn.close()

        print(f"\n{'='*60}")
        print(f"DATABASE STATISTICS")
        print(f"{'='*60}")
        print(f"Total initiatives: {init_count}")
        print(f"Total feedback: {feedback_count}")
        print(f"Database: {self.db_path}")
        print(f"{'='*60}")


def main():
    print(f"{'='*60}")
    print(f"EU Have Your Say - FULL DOWNLOAD")
    print(f"{'='*60}\n")

    downloader = HaveYourSayFullDownloader()

    # Step 1: Get all initiative IDs
    all_initiatives = downloader.get_all_initiative_ids()

    if not all_initiatives:
        print("No initiatives found!")
        sys.exit(1)

    # Step 2: Download each initiative
    print(f"\n{'='*60}")
    print(f"DOWNLOADING {len(all_initiatives)} INITIATIVES")
    print(f"{'='*60}\n")

    success_count = 0
    for i, init in enumerate(all_initiatives, 1):
        print(f"[{i}/{len(all_initiatives)}] Initiative {init['id']}")
        if downloader.download_initiative(init['id'], init['reference'], init['title']):
            success_count += 1
        time.sleep(1)  # Be respectful to the server

        # Print progress every 50 initiatives
        if i % 50 == 0:
            print(f"\n--- Progress: {i}/{len(all_initiatives)} ({i*100//len(all_initiatives)}%) ---\n")
            downloader.export_stats()

    # Final statistics
    print(f"\n{'='*60}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"Successful: {success_count}/{len(all_initiatives)}")
    downloader.export_stats()


if __name__ == "__main__":
    main()
