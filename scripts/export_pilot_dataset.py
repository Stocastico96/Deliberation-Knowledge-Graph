#!/usr/bin/env python3
"""
Export final dataset for pilot study: 3 cases (COVID, AI, Deforestation)
Format: JSON per case + RDF for knowledge graph integration
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import Counter

# Paths
HYS_DB = Path("/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db")
EP_JSON_DIR = Path("data/EU_parliament_debates/json_2021_2024")
OUTPUT_DIR = Path("data/pilot_study_dataset")
MATCHING_FILE = Path("data/hys_ep_matching.json")

# Cases configuration
CASES = {
    'case_1_covid': {
        'name': 'COVID Certificate Extension',
        'hys_refs': ['COM(2022)50', 'COM(2022)55'],
        'keywords': ['covid', 'coronavirus', 'health certificate', 'digital certificate', 'green certificate'],
        'topic': 'COVID'
    },
    'case_2_ai': {
        'name': 'Artificial Intelligence Act',
        'hys_refs': ['AIConsult2020', 'Ares(2020)3896535'],
        'keywords': ['artificial intelligence', 'AI act', 'AI regulation'],
        'topic': 'AI'
    },
    'case_3_deforestation': {
        'name': 'Deforestation Regulation',
        'hys_refs': ['Ares(2018)6516782'],
        'keywords': ['deforestation', 'forest degradation', 'due diligence'],
        'topic': 'Deforestation'
    }
}

def extract_hys_feedback(hys_refs):
    """Extract feedback from HYS database for given references"""
    conn = sqlite3.connect(HYS_DB)
    cursor = conn.cursor()

    feedback_list = []
    consultation_info = {}

    for ref in hys_refs:
        # Get initiative info
        cursor.execute("SELECT data FROM initiatives WHERE json_extract(data, '$.reference') = ?", (ref,))
        init_row = cursor.fetchone()

        if init_row:
            init_data = json.loads(init_row[0])
            consultation_info[ref] = {
                'reference': ref,
                'title': init_data.get('shortTitle', init_data.get('title', '')),
                'stage': init_data.get('stage', ''),
                'status': init_data.get('receivingFeedbackStatus', '')
            }

        # Get feedback
        cursor.execute("SELECT data FROM feedback WHERE json_extract(data, '$.referenceInitiative') = ?", (ref,))

        for row in cursor.fetchall():
            fb_data = json.loads(row[0])
            feedback_list.append({
                'consultation_ref': ref,
                'id': fb_data.get('id'),
                'date': fb_data.get('dateFeedback'),
                'language': fb_data.get('language'),
                'user_type': fb_data.get('publication', '').replace('PUBLISHED_', ''),
                'country': fb_data.get('country', ''),
                'organization': fb_data.get('organization', ''),
                'text': fb_data.get('feedbackTextUserLanguage', ''),
                'status': fb_data.get('status', '')
            })

    conn.close()
    return consultation_info, feedback_list

def filter_ep_debates(keywords):
    """Filter EP debates containing topic keywords"""
    json_files = sorted(EP_JSON_DIR.glob("debate_*.json"))

    relevant_debates = []

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            debate = json.load(f)

        debate_date = debate.get('del:identifier', '').replace('ep_debate_', '')

        # Check if debate contains topic
        matching_speeches = []

        for contrib in debate.get('del:hasContribution', []):
            text = contrib.get('del:text', '').lower()

            if any(kw.lower() in text for kw in keywords):
                # Get speaker info
                speaker_id = contrib.get('del:madeBy', {}).get('@id', '')
                speaker_name = None

                # Find speaker name in participants
                for participant in debate.get('del:hasParticipant', []):
                    if participant.get('del:identifier') == speaker_id:
                        speaker_name = participant.get('del:name', '')
                        break

                matching_speeches.append({
                    'id': contrib.get('del:identifier'),
                    'speaker': speaker_name or speaker_id,
                    'text': contrib.get('del:text', ''),
                    'timestamp': contrib.get('del:timestamp'),
                    'topic_ref': contrib.get('del:hasTopic', {}).get('@id', '')
                })

        if matching_speeches:
            relevant_debates.append({
                'date': debate_date,
                'date_formatted': f"{debate_date[:4]}-{debate_date[4:6]}-{debate_date[6:8]}",
                'name': debate.get('del:name'),
                'identifier': debate.get('del:identifier'),
                'start_date': debate.get('del:startDate'),
                'speeches': matching_speeches,
                'speech_count': len(matching_speeches)
            })

    return sorted(relevant_debates, key=lambda x: x['date'])

def export_case(case_id, config):
    """Export data for one case"""
    print(f"\n{'='*70}")
    print(f"Exporting: {config['name']}")
    print(f"{'='*70}")

    case_dir = OUTPUT_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract HYS feedback
    print(f"  Extracting HYS feedback...")
    consultation_info, feedback_list = extract_hys_feedback(config['hys_refs'])

    print(f"    Found {len(feedback_list)} feedback items")

    # Stats
    hys_stats = {
        'total': len(feedback_list),
        'by_language': Counter(fb['language'] for fb in feedback_list),
        'by_user_type': Counter(fb['user_type'] for fb in feedback_list),
        'by_country': Counter(fb['country'] for fb in feedback_list if fb['country']),
        'date_range': {
            'min': min((fb['date'] for fb in feedback_list if fb['date']), default=None),
            'max': max((fb['date'] for fb in feedback_list if fb['date']), default=None)
        }
    }

    hys_data = {
        'consultations': consultation_info,
        'feedback': feedback_list,
        'stats': hys_stats
    }

    with open(case_dir / 'hys_feedback.json', 'w', encoding='utf-8') as f:
        json.dump(hys_data, f, indent=2, ensure_ascii=False)

    # 2. Filter EP debates
    print(f"  Filtering EP debates...")
    ep_debates = filter_ep_debates(config['keywords'])

    print(f"    Found {len(ep_debates)} debates with {sum(d['speech_count'] for d in ep_debates)} speeches")

    # Stats
    ep_stats = {
        'total_debates': len(ep_debates),
        'total_speeches': sum(d['speech_count'] for d in ep_debates),
        'date_range': {
            'min': ep_debates[0]['date_formatted'] if ep_debates else None,
            'max': ep_debates[-1]['date_formatted'] if ep_debates else None
        }
    }

    ep_data = {
        'debates': ep_debates,
        'stats': ep_stats
    }

    with open(case_dir / 'ep_debates.json', 'w', encoding='utf-8') as f:
        json.dump(ep_data, f, indent=2, ensure_ascii=False)

    # 3. Metadata
    metadata = {
        'case_id': case_id,
        'case_name': config['name'],
        'topic': config['topic'],
        'hys': {
            'references': config['hys_refs'],
            'total_feedback': hys_stats['total'],
            'date_range': hys_stats['date_range']
        },
        'ep': {
            'total_debates': ep_stats['total_debates'],
            'total_speeches': ep_stats['total_speeches'],
            'date_range': ep_stats['date_range']
        },
        'exported_at': datetime.now().isoformat()
    }

    with open(case_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 4. README
    readme = f"""# {config['name']}

## Overview

- **Topic**: {config['topic']}
- **Case ID**: {case_id}

## Data Summary

### Have Your Say (HYS) Consultations

- **Total feedback**: {hys_stats['total']:,}
- **Date range**: {hys_stats['date_range']['min']} to {hys_stats['date_range']['max']}
- **Languages**: {len(hys_stats['by_language'])} languages
- **Top languages**: {', '.join(f"{lang} ({count})" for lang, count in hys_stats['by_language'].most_common(3))}
- **User types**: {', '.join(f"{ut} ({count})" for ut, count in hys_stats['by_user_type'].most_common())}

### European Parliament Debates

- **Total debates**: {ep_stats['total_debates']}
- **Total speeches**: {ep_stats['total_speeches']}
- **Date range**: {ep_stats['date_range']['min']} to {ep_stats['date_range']['max']}

## Files

- `hys_feedback.json` - All feedback from HYS consultations
- `ep_debates.json` - Filtered EP debates with relevant speeches
- `metadata.json` - Case metadata and statistics
- `README.md` - This file

## Usage

```python
import json

# Load HYS feedback
with open('hys_feedback.json', 'r') as f:
    hys_data = json.load(f)

# Load EP debates
with open('ep_debates.json', 'r') as f:
    ep_data = json.load(f)

# Access feedback
for feedback in hys_data['feedback']:
    print(feedback['text'])

# Access speeches
for debate in ep_data['debates']:
    for speech in debate['speeches']:
        print(speech['speaker'], speech['text'])
```

## Next Steps

1. Topic modeling with BERTopic
2. Stance detection
3. Temporal analysis
4. Actor analysis
5. Calculate Deliberative Distance Index (DDI)
"""

    with open(case_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme)

    print(f"  ✅ Exported to: {case_dir}")

    return metadata

def main():
    print("="*70)
    print("EXPORTING PILOT STUDY DATASET")
    print("="*70)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Export each case
    all_metadata = {}

    for case_id, config in CASES.items():
        metadata = export_case(case_id, config)
        all_metadata[case_id] = metadata

    # Create summary
    summary = {
        'pilot_study': 'HYS-EP Comparison',
        'cases': all_metadata,
        'exported_at': datetime.now().isoformat(),
        'total_hys_feedback': sum(m['hys']['total_feedback'] for m in all_metadata.values()),
        'total_ep_speeches': sum(m['ep']['total_speeches'] for m in all_metadata.values())
    }

    with open(OUTPUT_DIR / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Create main README
    main_readme = f"""# Pilot Study Dataset: HYS-EP Deliberation Comparison

## Overview

This dataset contains matched data from EU **Have Your Say (HYS)** consultations and **European Parliament (EP)** debates for comparative deliberation analysis.

**Period**: 2021-2025
**Cases**: 3 (COVID, AI, Deforestation)
**Total HYS feedback**: {summary['total_hys_feedback']:,}
**Total EP speeches**: {summary['total_ep_speeches']:,}

## Cases

"""

    for case_id, metadata in all_metadata.items():
        main_readme += f"""
### {metadata['case_id']}: {metadata['case_name']}

- **HYS**: {metadata['hys']['total_feedback']:,} feedback
- **EP**: {metadata['ep']['total_speeches']} speeches in {metadata['ep']['total_debates']} debates
- **Folder**: `{case_id}/`

"""

    main_readme += """
## Structure

```
pilot_study_dataset/
├── case_1_covid/
│   ├── hys_feedback.json
│   ├── ep_debates.json
│   ├── metadata.json
│   └── README.md
├── case_2_ai/
│   ├── hys_feedback.json
│   ├── ep_debates.json
│   ├── metadata.json
│   └── README.md
├── case_3_deforestation/
│   ├── hys_feedback.json
│   ├── ep_debates.json
│   ├── metadata.json
│   └── README.md
├── summary.json
└── README.md (this file)
```

## Usage

See individual case README files for details.

## Next Steps for Analysis

1. **Topic Modeling**: Use BERTopic to extract topics from HYS feedback and EP speeches
2. **Stance Detection**: Compare positions/arguments across forums
3. **Temporal Analysis**: Track topic evolution over time
4. **Actor Analysis**: Compare who participates in HYS vs EP
5. **Deliberative Distance Index**: Calculate multi-dimensional distance metrics

## References

- Di Porto et al. (2024). Mining EU consultations through AI. *Artificial Intelligence and Law*.
- Deliberation Knowledge Graph: https://w3id.org/deliberation/ontology

## License

Data sourced from:
- HYS: https://ec.europa.eu/info/law/better-regulation/have-your-say
- EP: https://www.europarl.europa.eu/plenary/en/debates-video.html

"""

    with open(OUTPUT_DIR / 'README.md', 'w', encoding='utf-8') as f:
        f.write(main_readme)

    # Final summary
    print("\n" + "="*70)
    print("EXPORT COMPLETE")
    print("="*70)
    print(f"\nTotal HYS feedback: {summary['total_hys_feedback']:,}")
    print(f"Total EP speeches: {summary['total_ep_speeches']:,}")
    print(f"\nDataset location: {OUTPUT_DIR}")
    print("\n✅ Ready for analysis!")

if __name__ == '__main__':
    main()
