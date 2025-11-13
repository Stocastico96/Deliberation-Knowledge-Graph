#!/usr/bin/env python3
"""
Check status of Have Your Say database and export to JSON
"""

import sqlite3
import json
from pathlib import Path

def check_database(db_path):
    """Check what's in the database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get table names
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in c.fetchall()]

    print(f"Database: {db_path}")
    print(f"Tables: {tables}")
    print()

    # Count initiatives
    if 'initiatives' in tables:
        c.execute("SELECT COUNT(*) FROM initiatives")
        init_count = c.fetchone()[0]
        print(f"Initiatives: {init_count}")

        # Get column names
        c.execute("PRAGMA table_info(initiatives)")
        columns = [row[1] for row in c.fetchall()]
        print(f"Columns: {columns}")

        # Show sample (use only 'id' which we know exists)
        c.execute("SELECT id FROM initiatives LIMIT 10")
        print("\nSample initiatives:")
        for row in c.fetchall():
            print(f"  ID: {row[0]}")

    # Count feedback
    if 'feedback' in tables:
        c.execute("SELECT COUNT(*) FROM feedback")
        feedback_count = c.fetchone()[0]
        print(f"\nFeedback: {feedback_count}")

    conn.close()

    return init_count if 'initiatives' in tables else 0, feedback_count if 'feedback' in tables else 0


def export_to_json(db_path, output_path):
    """Export database to JSON format for knowledge graph"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get all initiatives with their feedback
    c.execute("""
        SELECT i.id, i.data, GROUP_CONCAT(f.data, '|||') as feedbacks
        FROM initiatives i
        LEFT JOIN feedback f ON i.id = f.initiative_id
        GROUP BY i.id
    """)

    initiatives = []
    for row in c.fetchall():
        init_id, data_json, feedbacks_str = row

        # Parse initiative data
        init_data = json.loads(data_json) if data_json else {}

        # Parse feedbacks
        feedbacks = []
        if feedbacks_str:
            for fb_json in feedbacks_str.split('|||'):
                if fb_json:
                    try:
                        feedbacks.append(json.loads(fb_json))
                    except:
                        pass

        initiatives.append({
            'id': init_id,
            'data': init_data,
            'feedbacks': feedbacks
        })

    conn.close()

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(initiatives, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(initiatives)} initiatives to {output_path}")
    return len(initiatives)


if __name__ == "__main__":
    db_path = "eu_haveyoursay_specific.db"

    # Check status
    init_count, feedback_count = check_database(db_path)

    # Export if data exists
    if init_count > 0:
        output_json = "eu_have_your_say_export.json"
        export_to_json(db_path, output_json)
        print(f"\n✓ Ready for conversion to knowledge graph!")
    else:
        print("\n⚠️ No data in database")
