#!/usr/bin/env python3
"""
Complete Have Your Say Scraper
Scrapes feedback pages, downloads attachments, extracts text from PDFs with OCR fallback
Following the methodology from the research paper
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
import hashlib
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
import sys

# For PDF extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")

try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Warning: OCR not available. Install with: pip install pytesseract pillow")


class HaveYourSayCompleteScraper:
    def __init__(self, db_path="haveyoursay_complete.db", attachments_dir="attachments"):
        self.db_path = db_path
        self.attachments_dir = Path(attachments_dir)
        self.attachments_dir.mkdir(exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; Research/Academic) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        self.init_db()

    def init_db(self):
        """Initialize database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiative_id TEXT NOT NULL,
            feedback_ref TEXT UNIQUE,
            url TEXT,
            title TEXT,
            author TEXT,
            stakeholder_cat TEXT,
            declared_lang TEXT,
            detected_lang TEXT,
            submitted_at TEXT,
            html TEXT,
            extracted_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS attachment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_ref TEXT,
            url TEXT,
            filename TEXT,
            mime TEXT,
            sha256 TEXT,
            local_path TEXT,
            text_extracted TEXT,
            extraction_method TEXT,
            FOREIGN KEY (feedback_ref) REFERENCES feedback(feedback_ref) ON DELETE CASCADE
        )''')

        c.execute('''CREATE INDEX IF NOT EXISTS idx_feedback_ref ON feedback(feedback_ref)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_initiative ON feedback(initiative_id)''')

        conn.commit()
        conn.close()

    def get_feedback_list_pages(self, initiative_url):
        """Get all feedback list pages for an initiative"""
        # Try common patterns for feedback pages
        feedback_urls = [
            f"{initiative_url}/feedback",
            f"{initiative_url}/public-consultation",
            f"{initiative_url}/feedback_en",
            f"{initiative_url}/public-consultation_en"
        ]

        for url in feedback_urls:
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    print(f"✓ Found feedback page: {url}")
                    return self.paginate_feedback_list(url)
            except:
                continue

        return []

    def paginate_feedback_list(self, base_url):
        """Follow pagination to get all feedback links"""
        all_feedback_links = []
        page = 0

        while True:
            # Try different pagination patterns
            url_patterns = [
                f"{base_url}?page={page}",
                f"{base_url}&page={page}",
                base_url  # Some use JS pagination
            ]

            html = None
            for url in url_patterns:
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        html = response.text
                        break
                except:
                    continue

            if not html:
                break

            soup = BeautifulSoup(html, 'html.parser')

            # Extract feedback links (pattern: /F\d+_[a-z]{2})
            feedback_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if re.search(r'/F\d+_[a-z]{2}$', href) or re.search(r'feedback.*\d+', href):
                    full_url = urljoin(base_url, href)
                    feedback_links.append(full_url)

            if not feedback_links:
                break

            all_feedback_links.extend(feedback_links)
            print(f"  Page {page}: Found {len(feedback_links)} feedback items")

            # Check for next page
            next_link = soup.find('a', text=re.compile(r'next|›|»', re.I))
            if not next_link:
                break

            page += 1
            time.sleep(1)  # Be respectful

        return list(set(all_feedback_links))  # Remove duplicates

    def extract_feedback_metadata(self, soup, url):
        """Extract metadata from feedback page"""
        meta = {
            'url': url,
            'feedback_ref': None,
            'title': None,
            'author': None,
            'stakeholder_cat': None,
            'declared_lang': None,
            'submitted_at': None
        }

        # Extract feedback reference from URL
        ref_match = re.search(r'/(F\d+)_', url)
        if ref_match:
            meta['feedback_ref'] = ref_match.group(1)

        # Try to find title
        title_tags = soup.find_all(['h1', 'h2', 'h3'])
        for tag in title_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 10:
                meta['title'] = text
                break

        # Look for metadata in page
        for dt in soup.find_all('dt'):
            label = dt.get_text(strip=True).lower()
            dd = dt.find_next_sibling('dd')
            if not dd:
                continue

            value = dd.get_text(strip=True)

            if 'author' in label or 'name' in label:
                meta['author'] = value
            elif 'stakeholder' in label or 'category' in label or 'type' in label:
                meta['stakeholder_cat'] = value
            elif 'language' in label:
                meta['declared_lang'] = value
            elif 'date' in label or 'submitted' in label:
                meta['submitted_at'] = value

        return meta

    def extract_text_from_html(self, soup):
        """Extract clean text from HTML"""
        # Remove script, style, nav elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()

        # Get text from main content
        main = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|feedback'))
        if main:
            text = main.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # Clean up
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

    def find_attachments(self, soup, base_url):
        """Find all attachment links"""
        attachments = []

        # Look for download links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True).lower()

            # Check if it's an attachment
            is_attachment = False
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                is_attachment = True
            elif any(word in text for word in ['download', 'attachment', 'document', 'file']):
                is_attachment = True

            if is_attachment:
                full_url = urljoin(base_url, href)
                filename = Path(urlparse(full_url).path).name or 'attachment'

                attachments.append({
                    'url': full_url,
                    'filename': filename,
                    'link_text': text
                })

        return attachments

    def download_attachment(self, url, feedback_ref):
        """Download attachment and return local path"""
        try:
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Get filename
            filename = Path(urlparse(url).path).name
            if not filename or filename == '':
                filename = f"{feedback_ref}_attachment"

            # Create subdirectory for this feedback
            feedback_dir = self.attachments_dir / feedback_ref
            feedback_dir.mkdir(exist_ok=True)

            local_path = feedback_dir / filename

            # Download
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Calculate hash
            sha256 = hashlib.sha256()
            with open(local_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)

            return {
                'local_path': str(local_path),
                'sha256': sha256.hexdigest(),
                'mime': response.headers.get('Content-Type', 'application/octet-stream')
            }

        except Exception as e:
            print(f"    ✗ Error downloading {url}: {e}")
            return None

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF with OCR fallback"""
        text = ""
        method = None

        # Try pdfplumber first
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

                if text.strip():
                    method = "pdfplumber"
                    return text, method
            except Exception as e:
                print(f"      pdfplumber failed: {e}")

        # Fallback to OCR if available
        if HAS_OCR and not text.strip():
            try:
                # Convert PDF to images and OCR
                import pdf2image
                images = pdf2image.convert_from_path(pdf_path)

                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    text += page_text + "\n"

                if text.strip():
                    method = "tesseract_ocr"
                    return text, method
            except Exception as e:
                print(f"      OCR failed: {e}")

        return text, method

    def scrape_feedback(self, feedback_url, initiative_id):
        """Scrape a single feedback page"""
        print(f"  Scraping: {feedback_url}")

        try:
            response = self.session.get(feedback_url, timeout=30)
            response.raise_for_status()
            html = response.text

            soup = BeautifulSoup(html, 'html.parser')

            # Extract metadata
            meta = self.extract_feedback_metadata(soup, feedback_url)
            meta['initiative_id'] = initiative_id
            meta['html'] = html

            # Extract text
            text = self.extract_text_from_html(soup)
            meta['extracted_text'] = text

            # Save to database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute('''INSERT OR REPLACE INTO feedback
                         (initiative_id, feedback_ref, url, title, author, stakeholder_cat,
                          declared_lang, submitted_at, html, extracted_text)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (meta['initiative_id'], meta['feedback_ref'], meta['url'], meta['title'],
                       meta['author'], meta['stakeholder_cat'], meta['declared_lang'],
                       meta['submitted_at'], meta['html'], meta['extracted_text']))

            feedback_ref = meta['feedback_ref']

            # Find and download attachments
            attachments = self.find_attachments(soup, feedback_url)
            print(f"    Found {len(attachments)} attachments")

            for att in attachments:
                print(f"    Downloading: {att['filename']}")
                download_info = self.download_attachment(att['url'], feedback_ref)

                if download_info:
                    # Try to extract text if PDF
                    att_text = ""
                    att_method = None

                    if att['filename'].lower().endswith('.pdf'):
                        print(f"      Extracting text from PDF...")
                        att_text, att_method = self.extract_text_from_pdf(download_info['local_path'])
                        if att_text:
                            print(f"      ✓ Extracted {len(att_text)} chars using {att_method}")

                    # Save attachment info
                    c.execute('''INSERT INTO attachment
                                 (feedback_ref, url, filename, mime, sha256, local_path,
                                  text_extracted, extraction_method)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                              (feedback_ref, att['url'], att['filename'], download_info['mime'],
                               download_info['sha256'], download_info['local_path'],
                               att_text, att_method))

            conn.commit()
            conn.close()

            print(f"    ✓ Saved feedback {feedback_ref}")
            return True

        except Exception as e:
            print(f"    ✗ Error: {e}")
            return False

    def scrape_initiative(self, initiative_url, initiative_id):
        """Scrape all feedback for an initiative"""
        print(f"\nScraping initiative: {initiative_url}")

        # Get all feedback links
        feedback_links = self.get_feedback_list_pages(initiative_url)
        print(f"Found {len(feedback_links)} feedback items")

        # Scrape each feedback
        success_count = 0
        for i, link in enumerate(feedback_links, 1):
            print(f"\n[{i}/{len(feedback_links)}]")
            if self.scrape_feedback(link, initiative_id):
                success_count += 1
            time.sleep(2)  # Be respectful to the server

        print(f"\n{'='*60}")
        print(f"Completed: {success_count}/{len(feedback_links)} feedback items")
        print(f"{'='*60}")

        return success_count


def main():
    if len(sys.argv) < 2:
        print("Usage: python haveyoursay_complete_scraper.py <initiative_url> [initiative_id]")
        print("\nExample:")
        print("  python haveyoursay_complete_scraper.py https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/14622-Digital-Fairness-Act_en 14622")
        sys.exit(1)

    initiative_url = sys.argv[1]
    initiative_id = sys.argv[2] if len(sys.argv) > 2 else re.search(r'/(\d+)', initiative_url).group(1)

    print(f"{'='*60}")
    print("Have Your Say Complete Scraper")
    print(f"{'='*60}")
    print(f"Initiative URL: {initiative_url}")
    print(f"Initiative ID: {initiative_id}")
    print(f"{'='*60}")

    scraper = HaveYourSayCompleteScraper()
    scraper.scrape_initiative(initiative_url, initiative_id)


if __name__ == "__main__":
    main()