#!/usr/bin/env python3
"""
Argument Mapping for Deliberation Knowledge Graph
Extracts argument structures (Claims, Premises, Conclusions) from contributions
Uses dependency parsing and simple heuristics
"""

import logging
from pathlib import Path
from typing import List, Dict, Tuple
import spacy
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from tqdm import tqdm
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
ARG = Namespace("https://w3id.org/argument/ontology#")
BASE_URI = "https://w3id.org/deliberation/resource/"

# Argument indicator keywords (multilingual)
PREMISE_INDICATORS = {
    'en': ['because', 'since', 'for', 'given that', 'as', 'seeing that'],
    'es': ['porque', 'ya que', 'puesto que', 'dado que', 'como', 'visto que'],
    'it': ['perché', 'poiché', 'dato che', 'siccome', 'visto che'],
    'ca': ['perquè', 'ja que', 'atès que', 'com que']
}

CONCLUSION_INDICATORS = {
    'en': ['therefore', 'thus', 'hence', 'so', 'consequently', 'as a result'],
    'es': ['por lo tanto', 'así que', 'por tanto', 'en consecuencia', 'por ello'],
    'it': ['quindi', 'perciò', 'dunque', 'di conseguenza', 'pertanto'],
    'ca': ['per tant', 'així que', 'doncs', 'en conseqüència']
}

OBJECTION_INDICATORS = {
    'en': ['however', 'but', 'although', 'yet', 'nevertheless', 'on the other hand'],
    'es': ['sin embargo', 'pero', 'aunque', 'no obstante', 'por otro lado'],
    'it': ['tuttavia', 'ma', 'però', 'sebbene', 'nondimeno'],
    'ca': ['però', 'tanmateix', 'tot i que', 'no obstant']
}

class ArgumentMapper:
    def __init__(self, kg_path: str):
        """Initialize argument mapper"""
        self.kg_path = Path(kg_path)
        self.kg = None

        # Load spaCy models for different languages
        self.nlp_models = {}
        try:
            logger.info("Loading spaCy models...")
            self.nlp_models['en'] = spacy.load('en_core_web_sm')
            logger.info("Loaded English model")
        except:
            logger.warning("English model not found. Install with: python -m spacy download en_core_web_sm")

        try:
            self.nlp_models['es'] = spacy.load('es_core_news_sm')
            logger.info("Loaded Spanish model")
        except:
            logger.warning("Spanish model not found. Install with: python -m spacy download es_core_news_sm")

    def load_knowledge_graph(self):
        """Load knowledge graph"""
        logger.info(f"Loading knowledge graph from {self.kg_path}...")
        self.kg = Graph()
        self.kg.bind("del", DEL)
        self.kg.bind("arg", ARG)
        self.kg.bind("rdfs", RDFS)
        self.kg.parse(self.kg_path, format="turtle")
        logger.info(f"Loaded {len(self.kg)} triples")

    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        text_lower = text.lower()
        es_words = sum(1 for w in ['de', 'la', 'el', 'que', 'y', 'es'] if w in text_lower.split())
        en_words = sum(1 for w in ['the', 'and', 'is', 'of', 'to', 'a'] if w in text_lower.split())

        if es_words > en_words:
            return 'es'
        return 'en'

    def split_into_claims(self, text: str, lang: str) -> List[str]:
        """Split text into individual claims/statements"""
        # Use spaCy sentence segmentation if available
        if lang in self.nlp_models:
            doc = self.nlp_models[lang](text)
            return [sent.text.strip() for sent in doc.sents]

        # Fallback: split by punctuation
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def extract_argument_structure(self, text: str, lang: str = 'en') -> Dict:
        """Extract argument structure from text"""
        structure = {
            'claims': [],
            'premises': [],
            'conclusions': [],
            'objections': []
        }

        claims = self.split_into_claims(text, lang)

        premise_keywords = PREMISE_INDICATORS.get(lang, PREMISE_INDICATORS['en'])
        conclusion_keywords = CONCLUSION_INDICATORS.get(lang, CONCLUSION_INDICATORS['en'])
        objection_keywords = OBJECTION_INDICATORS.get(lang, OBJECTION_INDICATORS['en'])

        for claim in claims:
            claim_lower = claim.lower()

            # Check for premise indicators
            if any(keyword in claim_lower for keyword in premise_keywords):
                structure['premises'].append(claim)

            # Check for conclusion indicators
            elif any(keyword in claim_lower for keyword in conclusion_keywords):
                structure['conclusions'].append(claim)

            # Check for objection indicators
            elif any(keyword in claim_lower for keyword in objection_keywords):
                structure['objections'].append(claim)

            # Otherwise, it's a general claim
            else:
                structure['claims'].append(claim)

        return structure

    def analyze_contributions(self, sample_size: int = 1000):
        """Analyze contributions for argument structures"""
        logger.info(f"Analyzing contributions for arguments (sample: {sample_size})...")

        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT DISTINCT ?contribution ?text ?process
        WHERE {
            ?contribution a del:Contribution .
            ?contribution del:text ?text .
            ?process del:hasContribution ?contribution .
            FILTER(STRLEN(?text) > 50)
        }
        LIMIT """ + str(sample_size)

        results = self.kg.query(query)
        arguments_found = 0

        for row in tqdm(list(results)):
            contrib_uri = str(row.contribution)
            text = str(row.text)
            process_uri = str(row.process)

            # Detect language
            lang = self.detect_language(text)

            # Extract argument structure
            structure = self.extract_argument_structure(text, lang)

            # Only add if we found some argumentative structure
            if structure['premises'] or structure['conclusions']:
                # Create argument resource
                arg_uri = URIRef(f"{BASE_URI}argument_{contrib_uri.split('/')[-1]}")

                self.kg.add((arg_uri, RDF.type, ARG.Argument))
                self.kg.add((arg_uri, ARG.fromContribution, URIRef(contrib_uri)))
                self.kg.add((arg_uri, ARG.inProcess, URIRef(process_uri)))

                # Add premises
                for i, premise in enumerate(structure['premises']):
                    premise_uri = URIRef(f"{arg_uri}_premise_{i}")
                    self.kg.add((premise_uri, RDF.type, ARG.Premise))
                    self.kg.add((premise_uri, RDFS.label, Literal(premise, lang=lang)))
                    self.kg.add((arg_uri, ARG.hasPremise, premise_uri))

                # Add conclusions
                for i, conclusion in enumerate(structure['conclusions']):
                    conclusion_uri = URIRef(f"{arg_uri}_conclusion_{i}")
                    self.kg.add((conclusion_uri, RDF.type, ARG.Conclusion))
                    self.kg.add((conclusion_uri, RDFS.label, Literal(conclusion, lang=lang)))
                    self.kg.add((arg_uri, ARG.hasConclusion, conclusion_uri))

                # Add objections
                for i, objection in enumerate(structure['objections']):
                    objection_uri = URIRef(f"{arg_uri}_objection_{i}")
                    self.kg.add((objection_uri, RDF.type, ARG.Objection))
                    self.kg.add((objection_uri, RDFS.label, Literal(objection, lang=lang)))
                    self.kg.add((arg_uri, ARG.hasObjection, objection_uri))

                # Add claims
                for i, claim in enumerate(structure['claims']):
                    claim_uri = URIRef(f"{arg_uri}_claim_{i}")
                    self.kg.add((claim_uri, RDF.type, ARG.Claim))
                    self.kg.add((claim_uri, RDFS.label, Literal(claim, lang=lang)))
                    self.kg.add((arg_uri, ARG.hasClaim, claim_uri))

                arguments_found += 1

        logger.info(f"Analysis complete. Found {arguments_found} argumentative structures")

    def save_knowledge_graph(self, output_path: str = None):
        """Save updated knowledge graph"""
        if output_path is None:
            output_path = self.kg_path

        logger.info(f"Saving knowledge graph to {output_path}...")
        self.kg.serialize(destination=str(output_path), format="turtle")
        logger.info(f"Saved {len(self.kg)} triples")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Argument Mapping for Deliberation KG")
    parser.add_argument('--kg-path', required=True, help='Path to knowledge graph TTL file')
    parser.add_argument('--output-path', help='Output path (default: same as input)')
    parser.add_argument('--sample-size', type=int, default=1000,
                       help='Number of contributions to analyze (default: 1000)')

    args = parser.parse_args()

    mapper = ArgumentMapper(args.kg_path)
    mapper.load_knowledge_graph()
    mapper.analyze_contributions(args.sample_size)
    mapper.save_knowledge_graph(args.output_path)

    print("\n✅ Argument mapping complete!")


if __name__ == '__main__':
    main()
