#!/usr/bin/env python3
"""
Match HYS consultations with EP debates by topic and time period
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
HYS_DB = Path("/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db")
JSON_DIR = Path("data/EU_parliament_debates/json_2021_2024")
OUTPUT_FILE = Path("data/hys_ep_matching.json")

# Topic keywords for matching
TOPICS = {
    'AI': {
        'hys_refs': ['AIConsult2020', 'Ares(2020)3896535'],
        'keywords': ['artificial intelligence', 'AI act', 'AI regulation']
    },
    'Deforestation': {
        'hys_refs': ['Ares(2018)6516782', 'Ares(2020)583731', 'Ares(2020)5920982'],
        'keywords': ['deforestation', 'forest degradation', 'due diligence']
    },
    'Tobacco': {
        'hys_refs': ['tobaccoproducts2021', 'Ares(2020)5391856'],
        'keywords': ['tobacco', 'smoking', 'tobacco products']
    },
    'COVID': {
        'hys_refs': ['COM(2022)50', 'COM(2022)55'],  # COVID Certificate Extension + prolongation
        'keywords': ['covid', 'coronavirus', 'health certificate', 'digital certificate', 'green certificate']
    }
}

def get_hys_consultation_info(hys_ref):
    """Get consultation info from HYS database"""
    conn = sqlite3.connect(HYS_DB)
    cursor = conn.cursor()

    # Try to find initiative
    cursor.execute("SELECT data FROM initiatives WHERE json_extract(data, '$.reference') = ?", (hys_ref,))
    row = cursor.fetchone()

    info = {
        'reference': hys_ref,
        'title': None,
        'start_date': None,
        'end_date': None,
        'feedback_count': 0
    }

    if row:
        data = json.loads(row[0])
        info['title'] = data.get('shortTitle', data.get('title', ''))
        # Get dates if available
        # (HYS DB structure varies, adapt as needed)

    # Count feedback
    cursor.execute("SELECT COUNT(*) FROM feedback WHERE json_extract(data, '$.referenceInitiative') = ?", (hys_ref,))
    count = cursor.fetchone()
    if count:
        info['feedback_count'] = count[0]

    conn.close()
    return info

def find_relevant_debates(topic, keywords):
    """Find EP debates containing topic keywords"""
    json_files = sorted(JSON_DIR.glob("debate_*.json"))

    relevant_debates = []

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            debate = json.load(f)

        debate_date = debate.get('del:identifier', '').replace('ep_debate_', '')

        # Parse date
        try:
            date_obj = datetime.strptime(debate_date, '%Y%m%d')
        except:
            continue

        # Check if debate contains topic
        found_in_topics = False
        found_in_speeches = False
        matching_speeches = []

        # Check topic titles
        for topic_obj in debate.get('del:hasTopic', []):
            topic_name = topic_obj.get('del:name', '').lower()
            if any(kw.lower() in topic_name for kw in keywords):
                found_in_topics = True

        # Check speeches
        for contrib in debate.get('del:hasContribution', []):
            text = contrib.get('del:text', '').lower()
            if any(kw.lower() in text for kw in keywords):
                found_in_speeches = True
                matching_speeches.append({
                    'id': contrib.get('del:identifier'),
                    'speaker': contrib.get('del:madeBy', {}).get('@id', ''),
                    'text_preview': contrib.get('del:text', '')[:200]
                })

        if found_in_topics or found_in_speeches:
            relevant_debates.append({
                'date': debate_date,
                'date_formatted': date_obj.strftime('%Y-%m-%d'),
                'name': debate.get('del:name'),
                'found_in_topics': found_in_topics,
                'found_in_speeches': found_in_speeches,
                'speech_count': len(matching_speeches),
                'sample_speeches': matching_speeches[:3]  # First 3 as sample
            })

    return sorted(relevant_debates, key=lambda x: x['date'])

def main():
    print("="*70)
    print("MATCHING HYS CONSULTATIONS WITH EP DEBATES")
    print("="*70)

    results = {}

    for topic, config in TOPICS.items():
        print(f"\n{topic}:")
        print(f"  {'='*66}")

        # Get HYS info
        hys_consultations = []
        for ref in config['hys_refs']:
            info = get_hys_consultation_info(ref)
            if info['feedback_count'] > 0:  # Only include if has feedback
                hys_consultations.append(info)
                print(f"  HYS: {ref} ({info['feedback_count']} feedback)")

        # Find EP debates
        ep_debates = find_relevant_debates(topic, config['keywords'])
        print(f"  EP Debates: {len(ep_debates)} found")

        if ep_debates:
            print(f"  Date range: {ep_debates[0]['date_formatted']} to {ep_debates[-1]['date_formatted']}")
            total_speeches = sum(d['speech_count'] for d in ep_debates)
            print(f"  Total matching speeches: {total_speeches}")

        results[topic] = {
            'hys_consultations': hys_consultations,
            'ep_debates': ep_debates,
            'summary': {
                'hys_count': len(hys_consultations),
                'hys_total_feedback': sum(c['feedback_count'] for c in hys_consultations),
                'ep_debate_count': len(ep_debates),
                'ep_speech_count': sum(d['speech_count'] for d in ep_debates)
            }
        }

    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print("MATCHING SUMMARY")
    print("="*70)

    for topic, data in results.items():
        s = data['summary']
        print(f"\n{topic}:")
        print(f"  HYS: {s['hys_count']} consultations, {s['hys_total_feedback']:,} feedback")
        print(f"  EP:  {s['ep_debate_count']} debates, {s['ep_speech_count']} speeches")

        # Assess viability for pilot study
        if s['hys_total_feedback'] >= 100 and s['ep_speech_count'] >= 20:
            print(f"  ✅ VIABLE for pilot study")
        elif s['hys_total_feedback'] >= 100 or s['ep_speech_count'] >= 20:
            print(f"  ⚠️  MARGINAL - may work")
        else:
            print(f"  ❌ INSUFFICIENT data")

    print(f"\n📄 Full results saved to: {OUTPUT_FILE}")

    # Recommend 3 cases
    print("\n" + "="*70)
    print("RECOMMENDED 3 CASES FOR PILOT STUDY")
    print("="*70)

    viable = [(topic, data['summary']) for topic, data in results.items()
              if data['summary']['hys_total_feedback'] >= 100 and data['summary']['ep_speech_count'] >= 20]

    viable.sort(key=lambda x: (x[1]['hys_total_feedback'], x[1]['ep_speech_count']), reverse=True)

    for i, (topic, summary) in enumerate(viable[:3], 1):
        print(f"\n{i}. {topic}")
        print(f"   HYS: {summary['hys_total_feedback']:,} feedback")
        print(f"   EP:  {summary['ep_speech_count']} speeches in {summary['ep_debate_count']} debates")

if __name__ == '__main__':
    main()
