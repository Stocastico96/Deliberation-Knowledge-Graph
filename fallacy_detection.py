#!/usr/bin/env python3
"""
Fallacy Detection using OpenRouter LLM
Identifies logical fallacies in deliberation contributions
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict
import requests
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
BASE_URI = "https://w3id.org/deliberation/resource/"

# Fallacy types based on standard logical fallacy taxonomy
FALLACY_TYPES = {
    'ad_hominem': 'Ad Hominem - Attacking the person instead of the argument',
    'straw_man': 'Straw Man - Misrepresenting an argument to make it easier to attack',
    'false_dilemma': 'False Dilemma - Presenting only two options when more exist',
    'slippery_slope': 'Slippery Slope - Claiming a small action will lead to extreme consequences',
    'circular_reasoning': 'Circular Reasoning - Using the conclusion as a premise',
    'appeal_to_authority': 'Appeal to Authority - Relying on authority instead of evidence',
    'appeal_to_emotion': 'Appeal to Emotion - Using emotions instead of logic',
    'hasty_generalization': 'Hasty Generalization - Drawing conclusions from insufficient evidence',
    'red_herring': 'Red Herring - Introducing irrelevant information to distract',
    'false_cause': 'False Cause - Assuming causation from correlation',
    'tu_quoque': 'Tu Quoque - "You too" fallacy, deflecting criticism',
    'bandwagon': 'Bandwagon - Appealing to popularity',
    'no_true_scotsman': 'No True Scotsman - Modifying definition to exclude counterexamples'
}

class FallacyDetector:
    def __init__(self, kg_path: str, openrouter_api_key: str = None):
        """Initialize fallacy detector"""
        self.kg_path = Path(kg_path)
        self.kg = None

        # OpenRouter API setup
        self.api_key = openrouter_api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key not found")

        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "deepseek/deepseek-chat"  # Free model on OpenRouter

    def load_knowledge_graph(self):
        """Load knowledge graph"""
        logger.info(f"Loading knowledge graph from {self.kg_path}...")
        self.kg = Graph()
        self.kg.bind("del", DEL)
        self.kg.bind("rdfs", RDFS)
        self.kg.parse(self.kg_path, format="turtle")
        logger.info(f"Loaded {len(self.kg)} triples")

    def detect_fallacies_llm(self, text: str, language: str = "en") -> List[Dict]:
        """Use LLM to detect fallacies in text"""

        fallacy_list = "\n".join([f"- {k}: {v}" for k, v in FALLACY_TYPES.items()])

        prompt = f"""Analyze the following text for logical fallacies.

Text (in {language}): "{text}"

Identify any logical fallacies from this list:
{fallacy_list}

Return ONLY a JSON array with detected fallacies. Each fallacy should have:
- type: the fallacy type key (e.g., "ad_hominem")
- explanation: brief explanation (max 100 characters)

If no fallacies found, return an empty array [].

Example response: [{{"type": "ad_hominem", "explanation": "Attacks person's character instead of argument"}}]

JSON response:"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for more consistent results
            "max_tokens": 500
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Extract JSON from response
            if content.startswith('['):
                fallacies = json.loads(content)
            else:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    fallacies = json.loads(json_match.group())
                else:
                    fallacies = []

            return fallacies

        except Exception as e:
            logger.error(f"Error detecting fallacies: {e}")
            return []

    def analyze_contributions(self, sample_size: int = 100):
        """Analyze a sample of contributions for fallacies"""
        logger.info(f"Analyzing contributions for fallacies (sample: {sample_size})...")

        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT DISTINCT ?contribution ?text ?process
        WHERE {
            ?contribution a del:Contribution .
            ?contribution del:text ?text .
            ?process del:hasContribution ?contribution .
            FILTER(STRLEN(?text) > 100)
            FILTER(STRLEN(?text) < 1000)
        }
        LIMIT """ + str(sample_size)

        results = self.kg.query(query)
        fallacies_found = 0

        for row in tqdm(list(results)):
            contrib_uri = str(row.contribution)
            text = str(row.text)
            process_uri = str(row.process)

            # Detect language (simple heuristic)
            language = "es" if any(word in text.lower() for word in ["el", "la", "los", "las", "de", "del"]) else "en"

            # Detect fallacies
            detected = self.detect_fallacies_llm(text, language)

            if detected:
                logger.info(f"Found {len(detected)} fallacies in {contrib_uri}")

                for i, fallacy in enumerate(detected):
                    fallacy_uri = URIRef(f"{BASE_URI}fallacy_{contrib_uri.split('/')[-1]}_{i}")

                    # Add fallacy to KG
                    self.kg.add((fallacy_uri, RDF.type, DEL.Fallacy))
                    self.kg.add((fallacy_uri, DEL.fallacyType, Literal(fallacy['type'])))
                    self.kg.add((fallacy_uri, DEL.explanation, Literal(fallacy['explanation'])))
                    self.kg.add((fallacy_uri, DEL.inContribution, URIRef(contrib_uri)))
                    self.kg.add((fallacy_uri, DEL.inProcess, URIRef(process_uri)))

                    fallacies_found += 1

        logger.info(f"Analysis complete. Found {fallacies_found} fallacies total")

    def save_knowledge_graph(self, output_path: str = None):
        """Save updated knowledge graph"""
        if output_path is None:
            output_path = self.kg_path

        logger.info(f"Saving knowledge graph to {output_path}...")
        self.kg.serialize(destination=str(output_path), format="turtle")
        logger.info(f"Saved {len(self.kg)} triples")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fallacy Detection for Deliberation KG")
    parser.add_argument('--kg-path', required=True, help='Path to knowledge graph TTL file')
    parser.add_argument('--output-path', help='Output path (default: same as input)')
    parser.add_argument('--sample-size', type=int, default=100,
                       help='Number of contributions to analyze (default: 100)')
    parser.add_argument('--api-key', help='OpenRouter API key (or use OPENROUTER_API_KEY env var)')

    args = parser.parse_args()

    detector = FallacyDetector(args.kg_path, args.api_key)
    detector.load_knowledge_graph()
    detector.analyze_contributions(args.sample_size)
    detector.save_knowledge_graph(args.output_path)

    print("\n✅ Fallacy detection complete!")


if __name__ == '__main__':
    main()
