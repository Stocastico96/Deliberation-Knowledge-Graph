#!/usr/bin/env python3
"""
Append remaining 300K feedbacks to HYS RDF file
Without loading into memory - direct Turtle writing
"""

import sqlite3
import json
from datetime import datetime
from tqdm import tqdm
from html import escape

# Configuration
db_path = '/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db'
output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/hys_data.ttl'
BASE_URI = 'http://data.cogenta.org/deliberation/'

# Already processed 700,000 feedbacks
START_OFFSET = 700000
TOTAL_FEEDBACKS = 999999

def escape_turtle_string(s):
    """Escape string for Turtle format"""
    if not s:
        return ""
    # Escape backslashes first, then quotes
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return s

def write_feedback_triples(f, fb_id, pub_id, fb_data):
    """Write RDF triples for a feedback directly to file"""
    feedback_uri = f"<{BASE_URI}hys_feedback_{fb_id}>"
    pub_uri = f"<{BASE_URI}hys_publication_{pub_id}>"

    # Type and publication link
    f.write(f"{feedback_uri} a <http://data.cogenta.org/ontology/Contribution> .\n")
    f.write(f"{pub_uri} <http://data.cogenta.org/ontology/hasContribution> {feedback_uri} .\n")

    # Feedback content
    if fb_data.get('feedback'):
        content = escape_turtle_string(fb_data['feedback'])
        lang = fb_data.get('language', 'en').lower()
        f.write(f'{feedback_uri} <http://data.cogenta.org/ontology/content> "{content}"@{lang} .\n')

    # Date
    if fb_data.get('dateFeedback'):
        try:
            dt = datetime.strptime(fb_data['dateFeedback'], '%Y/%m/%d %H:%M:%S')
            date_str = dt.date().isoformat()
            f.write(f'{feedback_uri} <http://purl.org/dc/terms/date> "{date_str}"^^<http://www.w3.org/2001/XMLSchema#date> .\n')
        except:
            pass

    # Organization
    if fb_data.get('organization'):
        org = escape_turtle_string(fb_data['organization'])
        f.write(f'{feedback_uri} <http://data.cogenta.org/ontology/organization> "{org}" .\n')

    # Author name
    if fb_data.get('firstName') and fb_data.get('surname'):
        author = escape_turtle_string(f"{fb_data['firstName']} {fb_data['surname']}")
        f.write(f'{feedback_uri} <http://data.cogenta.org/ontology/author> "{author}" .\n')

    # User type
    if fb_data.get('userType'):
        user_type = escape_turtle_string(fb_data['userType'])
        f.write(f'{feedback_uri} <http://data.cogenta.org/ontology/userType> "{user_type}" .\n')

    # Country
    if fb_data.get('country'):
        country = escape_turtle_string(fb_data['country'])
        f.write(f'{feedback_uri} <http://data.cogenta.org/ontology/country> "{country}" .\n')

    # Language
    if fb_data.get('language'):
        language = escape_turtle_string(fb_data['language'])
        f.write(f'{feedback_uri} <http://purl.org/dc/terms/language> "{language}" .\n')

    f.write('\n')  # Empty line between feedbacks

def main():
    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    remaining = TOTAL_FEEDBACKS - START_OFFSET
    print(f"Appending {remaining:,} remaining feedbacks to {output_file}")
    print(f"Starting from offset {START_OFFSET:,}")

    batch_size = 10000
    offset = START_OFFSET

    # Open file in append mode
    with open(output_file, 'a', encoding='utf-8') as f:
        while offset < TOTAL_FEEDBACKS:
            feedbacks = c.execute(
                'SELECT id, publication_id, data FROM feedback LIMIT ? OFFSET ?',
                (batch_size, offset)
            ).fetchall()

            if not feedbacks:
                break

            for fb_id, pub_id, fb_data_str in tqdm(feedbacks, desc=f"Batch {(offset-START_OFFSET)//batch_size + 1}"):
                fb_data = json.loads(fb_data_str)
                write_feedback_triples(f, fb_id, pub_id, fb_data)

            offset += batch_size

            # Progress report
            if (offset - START_OFFSET) % 50000 == 0:
                processed = offset - START_OFFSET
                print(f"\n✓ {processed:,} feedbacks appended")

    conn.close()

    print(f"\n✓ Append complete!")
    print(f"  Total feedbacks added: {TOTAL_FEEDBACKS - START_OFFSET:,}")
    print(f"  Output file: {output_file}")

if __name__ == '__main__':
    main()
