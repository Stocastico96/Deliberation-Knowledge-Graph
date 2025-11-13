#!/usr/bin/env python3
"""
HTML scraper for EU Have Your Say when API is not available
Scrapes the public-facing pages to get initiative IDs and feedback
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import re
import sys

class HaveYourSayHTMLScraper:
    def __init__(self, db_path="eu_haveyoursay_scraped.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.base_url = "https://ec.europa.eu/info/law/better-regulation/have-your-say"
        self.init_db()

    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS initiatives
                     (id TEXT PRIMARY KEY,
                      title TEXT,
                      url TEXT,
                      status TEXT,
                      scraped_at TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      initiative_id TEXT,
                      text TEXT,
                      language TEXT,
                      user_type TEXT,
                      organization TEXT,
                      country TEXT,
                      date TEXT,
                      scraped_at TEXT)''')

        conn.commit()
        conn.close()

    def get_initiatives_list(self, start=0, max_pages=10):
        """
        Scrape the initiatives list page
        Try different URL patterns to find initiatives
        """
        print(f"Scraping initiatives list (starting from {start})...")

        all_initiatives = []

        # Pattern 1: Browse by most recent
        patterns = [
            f"{self.base_url}/initiatives?page={start}",
            f"{self.base_url}/initiatives?sort=recent&page={start}",
            f"{self.base_url}/initiatives/all?page={start}",
        ]

        for page_num in range(max_pages):
            for pattern in patterns:
                url = pattern.replace(f"page={start}", f"page={page_num}")

                try:
                    print(f"  Trying: {url}")
                    response = self.session.get(url, timeout=30)

                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find initiative links - multiple patterns
                    # Pattern: /initiatives/XXXXX-name or /initiatives/XXXXX
                    links = soup.find_all('a', href=re.compile(r'/initiatives/\d+'))

                    if not links:
                        # Try alternative selectors
                        links = soup.select('a[href*="/initiatives/"]')

                    found_count = 0
                    for link in links:
                        href = link.get('href', '')

                        # Extract initiative ID
                        match = re.search(r'/initiatives/(\d+)', href)
                        if match:
                            init_id = match.group(1)
                            title = link.get_text(strip=True)

                            if init_id not in [i['id'] for i in all_initiatives]:
                                all_initiatives.append({
                                    'id': init_id,
                                    'title': title,
                                    'url': f"{self.base_url}/initiatives/{init_id}"
                                })
                                found_count += 1

                    if found_count > 0:
                        print(f"    ✓ Found {found_count} initiatives on this page")
                        break  # Found initiatives, no need to try other patterns

                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    continue

            time.sleep(2)  # Be respectful

        print(f"\n✓ Total initiatives found: {len(all_initiatives)}")
        return all_initiatives

    def get_known_initiative_ids(self):
        """
        Return a list of known initiative IDs that we can try
        Based on the pattern that IDs are sequential numbers
        """
        # Known working IDs from our existing data
        known_ids = [
            13524, 13682, 13761, 13796, 13845, 13863, 13915, 13967, 14026, 14622,
            # Add more recent IDs (guessing based on pattern)
            14000, 14100, 14200, 14300, 14400, 14500, 14600, 14700, 14800, 14900,
            15000, 15100, 15200, 15300, 15400, 15500,
            # Earlier IDs
            13000, 13100, 13200, 13300, 13400, 13500, 13600, 13700, 13800, 13900,
        ]

        # Generate range of IDs to try
        all_ids = set(known_ids)

        # Add ranges
        for start in range(13000, 16000, 50):
            for i in range(10):
                all_ids.add(start + i)

        return sorted(list(all_ids))

    def scrape_initiative(self, initiative_id):
        """Scrape a single initiative page"""
        url = f"{self.base_url}/initiatives/{initiative_id}-*_en"  # Try English version

        # Try multiple URL patterns
        url_patterns = [
            f"{self.base_url}/initiatives/{initiative_id}_en",
            f"{self.base_url}/initiatives/{initiative_id}",
            f"https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/{initiative_id}_en",
        ]

        for url in url_patterns:
            try:
                response = self.session.get(url, timeout=30, allow_redirects=True)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extract title
                    title_elem = soup.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else f"Initiative {initiative_id}"

                    # Check if page has actual content (not error page)
                    if len(response.text) < 1000 or 'not found' in response.text.lower():
                        continue

                    print(f"  ✓ Found: {title[:50]}...")

                    # Save to database
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()

                    c.execute("""INSERT OR REPLACE INTO initiatives
                                 (id, title, url, status, scraped_at)
                                 VALUES (?, ?, ?, ?, ?)""",
                              (str(initiative_id), title, url, 'active',
                               datetime.now().isoformat()))

                    # Try to find feedback section
                    feedback_count = self.scrape_feedback(initiative_id, soup, c)

                    conn.commit()
                    conn.close()

                    return True, feedback_count

            except Exception as e:
                continue

        return False, 0

    def scrape_feedback(self, initiative_id, soup, cursor):
        """Extract feedback from initiative page"""
        feedback_count = 0

        # Look for feedback sections
        feedback_sections = soup.find_all(['div', 'article'], class_=re.compile(r'feedback|comment|contribution'))

        for section in feedback_sections:
            text_elem = section.find(['p', 'div'], class_=re.compile(r'text|content|body'))

            if text_elem:
                text = text_elem.get_text(strip=True)

                if len(text) > 50:  # Only meaningful feedback
                    # Extract metadata if available
                    meta = {}
                    for dt in section.find_all('dt'):
                        label = dt.get_text(strip=True).lower()
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            meta[label] = dd.get_text(strip=True)

                    cursor.execute("""INSERT INTO feedback
                                     (initiative_id, text, language, user_type,
                                      organization, country, date, scraped_at)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                  (str(initiative_id), text,
                                   meta.get('language', 'en'),
                                   meta.get('user type', ''),
                                   meta.get('organization', ''),
                                   meta.get('country', ''),
                                   meta.get('date', ''),
                                   datetime.now().isoformat()))
                    feedback_count += 1

        return feedback_count

    def export_stats(self):
        """Print database statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM initiatives")
        init_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM feedback")
        feedback_count = c.fetchone()[0]

        conn.close()

        print(f"\n{'='*60}")
        print(f"SCRAPING STATISTICS")
        print(f"{'='*60}")
        print(f"Initiatives scraped: {init_count}")
        print(f"Feedback collected: {feedback_count}")
        print(f"Database: {self.db_path}")
        print(f"{'='*60}")

        return init_count, feedback_count


def main():
    print(f"{'='*60}")
    print("EU Have Your Say HTML Scraper")
    print(f"{'='*60}\n")

    scraper = HaveYourSayHTMLScraper()

    # Strategy 1: Try to scrape initiatives list
    print("Strategy 1: Scraping public initiatives list...")
    initiatives = scraper.get_initiatives_list(start=0, max_pages=5)

    # Strategy 2: Try known initiative IDs
    print("\nStrategy 2: Trying known initiative IDs...")
    known_ids = scraper.get_known_initiative_ids()

    success_count = 0
    total_feedback = 0

    for i, init_id in enumerate(known_ids, 1):
        print(f"[{i}/{len(known_ids)}] Trying initiative {init_id}...")

        success, feedback_count = scraper.scrape_initiative(init_id)

        if success:
            success_count += 1
            total_feedback += feedback_count
            print(f"    Feedback: {feedback_count}")
        else:
            print(f"    ✗ Not found")

        time.sleep(1)  # Be respectful

        # Progress update every 20 initiatives
        if i % 20 == 0:
            scraper.export_stats()

    # Final statistics
    print(f"\n{'='*60}")
    print("SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Successful: {success_count} initiatives")
    print(f"Total feedback: {total_feedback}")
    scraper.export_stats()


if __name__ == "__main__":
    main()
