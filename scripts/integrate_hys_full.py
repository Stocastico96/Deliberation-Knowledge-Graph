#!/usr/bin/env python3
"""
Script per export completo dati HYS dal database SQLite a CSV

Genera CSV completi di:
- initiatives.csv
- feedback.csv
- publications.csv
- attachments.csv

Input: /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db
Output: directory configurabile (default: /tmp/hys_export/)
"""

import argparse
import sys
import os
import json
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

def parse_json_field(data_str):
    """Parse JSON field from database"""
    try:
        return json.loads(data_str) if data_str else {}
    except:
        return {}

def export_initiatives(db_path, output_dir, verbose=False):
    """Export initiatives table to CSV"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, data, timestamp FROM initiatives ORDER BY id")

    output_file = output_dir / "initiatives.csv"

    # Define CSV columns based on JSON structure
    fieldnames = [
        'id', 'reference', 'short_title', 'dossier_summary',
        'dg', 'unit', 'committee', 'expert_group',
        'foreseen_act_type', 'receiving_feedback_status', 'stage',
        'is_major', 'is_evaluation', 'published_date',
        'feedback_deadline', 'timestamp'
    ]

    count = 0
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in cursor.fetchall():
            init_id, data_str, timestamp = row
            data = parse_json_field(data_str)

            csv_row = {
                'id': init_id,
                'reference': data.get('reference', ''),
                'short_title': data.get('shortTitle', ''),
                'dossier_summary': data.get('dossierSummary', ''),
                'dg': data.get('dg', ''),
                'unit': data.get('unit', ''),
                'committee': data.get('committee', ''),
                'expert_group': data.get('expertGroup', ''),
                'foreseen_act_type': data.get('foreseenActType', ''),
                'receiving_feedback_status': data.get('receivingFeedbackStatus', ''),
                'stage': data.get('stage', ''),
                'is_major': '1' if data.get('isMajor') else '0',
                'is_evaluation': '1' if data.get('isEvaluation') else '0',
                'published_date': data.get('publishedDate', ''),
                'feedback_deadline': data.get('feedbackDeadline', ''),
                'timestamp': timestamp
            }

            writer.writerow(csv_row)
            count += 1

            if verbose and count % 500 == 0:
                print(f"  Exported {count} initiatives...")

    conn.close()
    print(f"✅ Exported {count} initiatives to {output_file}")
    return count

def export_feedback(db_path, output_dir, verbose=False, limit=None):
    """Export feedback table to CSV"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, build reference -> initiative_id mapping
    if verbose:
        print("  Building initiative reference mapping...")

    ref_cursor = conn.cursor()
    ref_cursor.execute("SELECT id, data FROM initiatives")
    reference_to_id = {}
    for init_row in ref_cursor.fetchall():
        init_id, init_data_str = init_row
        init_data = parse_json_field(init_data_str)
        ref = init_data.get('reference', '')
        if ref:
            reference_to_id[ref] = init_id

    if verbose:
        print(f"  Mapped {len(reference_to_id)} initiative references")

    query = "SELECT id, publication_id, data, timestamp FROM feedback ORDER BY id"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)

    output_file = output_dir / "feedback.csv"

    # Define CSV columns based on JSON structure
    fieldnames = [
        'id', 'initiative_id', 'reference_initiative', 'publication_id', 'feedback',
        'language', 'country', 'user_type', 'organization',
        'company_size', 'first_name', 'surname',
        'date_feedback', 'timestamp'
    ]

    count = 0
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in cursor.fetchall():
            feedback_id, publication_id, data_str, timestamp = row
            data = parse_json_field(data_str)

            # Get initiative_id from reference mapping
            reference = data.get('referenceInitiative', '')
            initiative_id = reference_to_id.get(reference, '')

            csv_row = {
                'id': feedback_id,
                'initiative_id': initiative_id,
                'reference_initiative': reference,
                'publication_id': publication_id,
                'feedback': data.get('feedback', ''),
                'language': data.get('language', ''),
                'country': data.get('country', ''),
                'user_type': data.get('userType', ''),
                'organization': data.get('organization', ''),
                'company_size': data.get('companySize', ''),
                'first_name': data.get('firstName', ''),
                'surname': data.get('surname', ''),
                'date_feedback': data.get('dateFeedback', ''),
                'timestamp': timestamp
            }

            writer.writerow(csv_row)
            count += 1

            if verbose and count % 10000 == 0:
                print(f"  Exported {count} feedback...")

    conn.close()
    print(f"✅ Exported {count} feedback to {output_file}")
    return count

def export_publications(db_path, output_dir, verbose=False):
    """
    Export publications (if exists as separate table or embedded in initiatives)
    For now, create minimal publications.csv placeholder
    """
    output_file = output_dir / "publications.csv"

    # Minimal structure
    fieldnames = ['id', 'initiative_id', 'type', 'language', 'title']

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    print(f"✅ Created placeholder publications.csv at {output_file}")
    return 0

def export_attachments(db_path, output_dir, verbose=False):
    """
    Export attachments (if exists)
    For now, create minimal attachments.csv placeholder
    """
    output_file = output_dir / "attachments.csv"

    # Minimal structure
    fieldnames = ['id', 'publication_id', 'feedback_id', 'url', 'filename', 'language']

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    print(f"✅ Created placeholder attachments.csv at {output_file}")
    return 0

def main():
    parser = argparse.ArgumentParser(
        description='Export HYS database to CSV files for DKG integration'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db',
        help='Path to HYS SQLite database'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='/tmp/hys_export',
        help='Output directory for CSV files'
    )
    parser.add_argument(
        '--limit-feedback',
        type=int,
        default=None,
        help='Limit number of feedback to export (for testing)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Check database exists
    if not Path(args.db).exists():
        print(f"❌ Error: Database not found at {args.db}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== HYS Database Export ===")
    print(f"Database: {args.db}")
    print(f"Output: {output_dir}")
    print()

    # Export all tables
    start_time = datetime.now()

    print("1. Exporting initiatives...")
    init_count = export_initiatives(args.db, output_dir, args.verbose)

    print("\n2. Exporting feedback...")
    feedback_count = export_feedback(
        args.db, output_dir,
        verbose=args.verbose,
        limit=args.limit_feedback
    )

    print("\n3. Exporting publications...")
    pub_count = export_publications(args.db, output_dir, args.verbose)

    print("\n4. Exporting attachments...")
    att_count = export_attachments(args.db, output_dir, args.verbose)

    # Summary
    elapsed = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Export completed in {elapsed}")
    print(f"\nSummary:")
    print(f"  - Initiatives: {init_count:,}")
    print(f"  - Feedback: {feedback_count:,}")
    print(f"  - Publications: {pub_count:,}")
    print(f"  - Attachments: {att_count:,}")
    print(f"\nFiles saved to: {output_dir}")

if __name__ == '__main__':
    main()
