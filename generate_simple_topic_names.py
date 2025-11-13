#!/usr/bin/env python3
"""
Generate simple descriptive English names for topics based on keywords
"""

import json
from pathlib import Path
from collections import Counter
import re

# Manual mappings for common patterns
TOPIC_PATTERNS = {
    # English topics
    ('games', 'digital'): 'Digital Games & Ownership',
    ('court', 'rule', 'justice'): 'US Supreme Court Cases',
    ('the', 'and', 'we', 'in'): 'General Political Discourse',
    ('ukraine', 'eu', 'accession'): 'Ukraine EU Accession',
    ('to', 'the', 'of', 'and', 'for'): 'General English Discussions',

    # Spanish topics
    ('madrid', 'que', 'los'): 'Madrid Local Administration',
    ('bici', 'carril', 'ciclistas'): 'Bicycle Lanes & Urban Mobility',
    ('perros', 'dueños', 'mascotas'): 'Pet Regulations & Dogs',
    ('propuesta', 'propuestas', 'debate'): 'Citizen Proposals & Participation',
    ('coche', 'tráfico', 'movilidad'): 'Traffic & Car Mobility',
    ('vivienda', 'alquiler', 'pisos'): 'Housing & Rent Issues',
    ('trabajo', 'empleo', 'laboral'): 'Employment & Labor Rights',
    ('cultura', 'cultural', 'arte'): 'Culture & Arts',
    ('educación', 'escuela', 'colegios'): 'Education & Schools',
    ('medio', 'ambiente', 'contaminación'): 'Environment & Pollution',
    ('sanidad', 'salud', 'hospital'): 'Healthcare & Public Health',
    ('comercio', 'tiendas', 'negocios'): 'Commerce & Local Business',
    ('seguridad', 'policía', 'delincuencia'): 'Security & Crime',
    ('parques', 'zonas', 'verdes'): 'Parks & Green Spaces',
    ('limpieza', 'basura', 'residuos'): 'Cleaning & Waste Management',

    # Catalan topics
    ('de', 'la', 'que', 'per', 'les'): 'Catalan Public Administration',
    ('barcelona', 'ciutat', 'barri'): 'Barcelona Local Issues',
}


def detect_language(keywords):
    """Detect primary language from keywords"""
    spanish_words = {'que', 'de', 'los', 'las', 'el', 'la', 'en', 'por', 'se', 'no', 'un', 'una', 'del'}
    catalan_words = {'que', 'de', 'la', 'per', 'les', 'els', 'una', 'el', 'en', 'dels'}
    english_words = {'the', 'and', 'to', 'of', 'for', 'in', 'that', 'is', 'it', 'with'}

    keywords_set = set(keywords[:10])

    spanish_count = len(keywords_set & spanish_words)
    catalan_count = len(keywords_set & catalan_words)
    english_count = len(keywords_set & english_words)

    if spanish_count >= catalan_count and spanish_count >= english_count:
        return 'Spanish'
    elif english_count > spanish_count and english_count > catalan_count:
        return 'English'
    elif catalan_count > 0:
        return 'Catalan'
    return 'Unknown'


def generate_name_from_keywords(topic_id, keywords):
    """Generate name based on keyword patterns"""

    # Check patterns
    for pattern_keys, name in TOPIC_PATTERNS.items():
        if len(set(keywords[:5]) & set(pattern_keys)) >= 2:
            return name

    # Detect language and create generic name
    lang = detect_language(keywords)

    # Get most meaningful keywords (skip common stop words)
    stop_words = {'de', 'la', 'que', 'en', 'el', 'los', 'las', 'un', 'una', 'del', 'por', 'se', 'no',
                  'the', 'and', 'to', 'of', 'for', 'in', 'that', 'is', 'it', 'with', 'a', 'an',
                  'per', 'les', 'els', 'dels'}

    meaningful = [k for k in keywords if k.lower() not in stop_words][:3]

    if meaningful:
        return f"{lang}: {' + '.join(meaningful[:2]).title()}"
    else:
        return f"{lang} Topic {topic_id}"


def main():
    # Load topics JSON
    topics_file = Path("knowledge_graph/topic_models/topics_summary.json")

    if not topics_file.exists():
        print(f"Error: {topics_file} not found")
        return

    with open(topics_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    topics = data['topics']
    print(f"Generating names for {len(topics)} topics...")

    for i, topic in enumerate(topics):
        topic_id = topic['id']
        keywords = topic.get('keywords', [])

        # Generate name
        name = generate_name_from_keywords(topic_id, keywords)
        topic['name'] = name

        print(f"Topic {topic_id}: {name}")
        print(f"  Keywords: {', '.join(keywords[:5])}")

    # Save updated JSON
    with open(topics_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Updated {len(topics)} topic names")


if __name__ == "__main__":
    main()
