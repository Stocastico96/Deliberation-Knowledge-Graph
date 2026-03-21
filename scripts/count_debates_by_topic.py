#!/usr/bin/env python3
"""
Count debates by topic from converted JSON files
"""

import json
from pathlib import Path
from collections import defaultdict

JSON_DIR = Path("data/EU_parliament_debates/json_2021_2024")

# Topic keywords
KEYWORDS = {
    'AI': ['artificial intelligence', 'AI act', 'AI regulation', 'artificial neural'],
    'Deforestation': ['deforestation', 'forest degradation', 'due diligence', 'forest'],
    'Tobacco': ['tobacco', 'smoking', 'tobacco products', 'nicotine'],
    'COVID': ['covid', 'coronavirus', 'pandemic', 'health certificate', 'digital certificate', 'green pass']
}

def main():
    print("="*70)
    print("COUNTING DEBATES BY TOPIC")
    print("="*70)

    json_files = sorted(JSON_DIR.glob("debate_*.json"))
    print(f"\nAnalyzing {len(json_files)} JSON files...\n")

    # Track topics found in each debate
    topic_debates = defaultdict(list)
    topic_speech_count = defaultdict(int)

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            debate = json.load(f)

        debate_date = debate.get('del:identifier', '').replace('ep_debate_', '')
        topics_found = set()

        # Check topics
        for topic_obj in debate.get('del:hasTopic', []):
            topic_name = topic_obj.get('del:name', '').lower()

            # Match against keywords
            for topic, keywords in KEYWORDS.items():
                if any(kw.lower() in topic_name for kw in keywords):
                    topics_found.add(topic)

        # Check contributions (speeches)
        for contrib in debate.get('del:hasContribution', []):
            text = contrib.get('del:text', '').lower()

            for topic, keywords in KEYWORDS.items():
                if any(kw.lower() in text for kw in keywords):
                    topics_found.add(topic)
                    topic_speech_count[topic] += 1

        # Record which topics were found in this debate
        for topic in topics_found:
            topic_debates[topic].append(debate_date)

    # Print results
    print("="*70)
    print("RESULTS")
    print("="*70)

    for topic in ['AI', 'Deforestation', 'Tobacco', 'COVID']:
        debates = topic_debates.get(topic, [])
        speeches = topic_speech_count.get(topic, 0)

        print(f"\n{topic}:")
        print(f"  Debates (sessions with topic): {len(debates)}")
        print(f"  Total speeches mentioning topic: {speeches}")

        if debates:
            print(f"  Date range: {min(debates)} to {max(debates)}")
            print(f"  Sample dates: {', '.join(sorted(debates)[:5])}")

    print("\n" + "="*70)

if __name__ == '__main__':
    main()
