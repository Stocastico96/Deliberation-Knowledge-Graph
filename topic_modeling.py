#!/usr/bin/env python3
"""
Topic Modeling for Deliberation Knowledge Graph
Implements LDA and BERTopic for multilingual topic extraction
"""

import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

import numpy as np
import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# Topic modeling libraries
from gensim import corpora
from gensim.models import LdaModel
from gensim.parsing.preprocessing import preprocess_string, strip_punctuation, strip_numeric
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# Preprocessing
import re
from collections import Counter

# Namespaces
DEL = Namespace("http://purl.org/ontology/deliberation#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
BASE_URI = "http://data.deliberation.org/"

class TopicModeler:
    """
    Multilingual topic modeling for deliberation data
    Supports both LDA (classical) and BERTopic (neural)
    """

    def __init__(self, kg_path: str, output_dir: str = "topic_models", language: str = "multilingual"):
        self.kg_path = kg_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.language = language

        # Load knowledge graph
        print(f"Loading knowledge graph from {kg_path}...")
        self.graph = Graph()
        self.graph.parse(kg_path, format="turtle")
        print(f"Loaded {len(self.graph)} triples")

        # Stopwords for multiple languages
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        """Load stopwords for IT, ES, CA, EN"""
        # Basic multilingual stopwords
        stopwords = {
            # English
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in', 'for',
            'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            # Italian
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'di', 'da', 'in', 'con',
            'su', 'per', 'tra', 'fra', 'e', 'ed', 'o', 'od', 'che', 'chi', 'cui', 'si',
            'non', 'più', 'anche', 'come', 'se', 'quando', 'dove', 'perché', 'quindi',
            'ma', 'però', 'ancora', 'solo', 'già', 'mai', 'sono', 'è', 'sei', 'siamo',
            'ho', 'hai', 'ha', 'abbiamo', 'hanno', 'questo', 'questa', 'questi', 'queste',
            # Spanish
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'en',
            'con', 'por', 'para', 'sin', 'sobre', 'tras', 'entre', 'y', 'o', 'u', 'que',
            'si', 'no', 'más', 'muy', 'tan', 'como', 'cuando', 'donde', 'porque', 'pero',
            'aunque', 'también', 'ya', 'solo', 'sólo', 'es', 'son', 'está', 'están',
            'he', 'has', 'ha', 'hemos', 'han', 'este', 'esta', 'estos', 'estas',
            # Catalan
            'el', 'la', 'els', 'les', 'un', 'una', 'uns', 'unes', 'de', 'del', 'dels',
            'en', 'amb', 'per', 'sense', 'sobre', 'entre', 'i', 'o', 'que', 'si', 'no',
            'més', 'molt', 'tan', 'com', 'quan', 'on', 'perquè', 'però', 'també', 'ja',
            'és', 'són', 'està', 'estan', 'aquest', 'aquesta', 'aquests', 'aquestes',
        }
        return stopwords

    def preprocess_text(self, text: str) -> List[str]:
        """Clean and tokenize text"""
        if not text or len(text.strip()) < 10:
            return []

        # Lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove special characters but keep letters with accents
        text = re.sub(r'[^a-záàâäãåçéèêëíìîïñóòôöõúùûüýÿæœ\s]', ' ', text)

        # Split into words
        words = text.split()

        # Remove stopwords and short words
        words = [w for w in words if w not in self.stopwords and len(w) > 2]

        return words

    def extract_contributions(self) -> pd.DataFrame:
        """Extract contribution texts from knowledge graph"""
        print("Extracting contributions from KG...")

        contributions = []

        query = """
        PREFIX del: <http://purl.org/ontology/deliberation#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?contrib ?text ?process ?date ?platform
        WHERE {
            ?contrib a del:Contribution .
            ?contrib del:hasText ?text .
            ?contrib del:isPartOf ?process .
            OPTIONAL { ?contrib dcterms:created ?date }
            OPTIONAL { ?process del:hasPlatform ?platform }

            FILTER(STRLEN(?text) > 50)
        }
        """

        results = self.graph.query(query)

        for row in results:
            contributions.append({
                'uri': str(row.contrib),
                'text': str(row.text),
                'process_uri': str(row.process),
                'date': str(row.date) if row.date else None,
                'platform': str(row.platform) if row.platform else None
            })

        df = pd.DataFrame(contributions)
        print(f"Extracted {len(df)} contributions")

        return df

    def train_lda(self, texts: List[List[str]], num_topics: int = 20,
                  passes: int = 10) -> Tuple[LdaModel, corpora.Dictionary]:
        """Train LDA topic model"""
        print(f"\nTraining LDA with {num_topics} topics...")

        # Create dictionary and corpus
        dictionary = corpora.Dictionary(texts)

        # Filter extremes
        dictionary.filter_extremes(no_below=5, no_above=0.5, keep_n=10000)

        # Create corpus
        corpus = [dictionary.doc2bow(text) for text in texts]

        # Train LDA
        lda_model = LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            passes=passes,
            random_state=42,
            chunksize=100,
            alpha='auto',
            per_word_topics=True
        )

        print("LDA training complete")

        return lda_model, dictionary

    def train_bertopic(self, texts: List[str], num_topics: int = 20) -> BERTopic:
        """Train BERTopic model with multilingual embeddings"""
        print(f"\nTraining BERTopic with {num_topics} topics (this may take a while)...")

        # Use multilingual sentence transformer
        embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

        # Configure BERTopic
        topic_model = BERTopic(
            embedding_model=embedding_model,
            language="multilingual",
            calculate_probabilities=False,
            nr_topics=num_topics,
            verbose=True
        )

        # Train
        topics, probs = topic_model.fit_transform(texts)

        print("BERTopic training complete")

        return topic_model

    def add_topics_to_kg(self, df: pd.DataFrame, lda_model: LdaModel,
                         dictionary: corpora.Dictionary, topic_model: BERTopic = None):
        """Add topic information to knowledge graph"""
        print("\nAdding topics to knowledge graph...")

        # Create new graph for topics
        topic_graph = Graph()
        topic_graph.bind("del", DEL)
        topic_graph.bind("dcterms", DCTERMS)

        # Track topic usage
        topic_counts = Counter()

        # Process each contribution
        for idx, row in df.iterrows():
            contrib_uri = URIRef(row['uri'])

            # Get preprocessed text
            tokens = self.preprocess_text(row['text'])

            if not tokens:
                continue

            # LDA topics
            bow = dictionary.doc2bow(tokens)
            lda_topics = lda_model.get_document_topics(bow)

            # Get top LDA topic
            if lda_topics:
                top_topic_id, top_prob = max(lda_topics, key=lambda x: x[1])

                if top_prob > 0.2:  # Threshold
                    topic_uri = URIRef(f"{BASE_URI}topic_lda_{top_topic_id}")

                    # Add topic entity
                    topic_graph.add((topic_uri, RDF.type, DEL.Topic))
                    topic_graph.add((topic_uri, RDFS.label,
                                   Literal(f"LDA Topic {top_topic_id}", lang="en")))

                    # Get top words for this topic
                    top_words = lda_model.show_topic(top_topic_id, topn=5)
                    words_str = ", ".join([w for w, _ in top_words])
                    topic_graph.add((topic_uri, DCTERMS.description,
                                   Literal(words_str, lang="en")))

                    # Link contribution to topic
                    topic_graph.add((contrib_uri, DEL.hasTopic, topic_uri))
                    topic_graph.add((topic_uri, DEL.hasWeight,
                                   Literal(float(top_prob), datatype=XSD.float)))

                    topic_counts[top_topic_id] += 1

            # BERTopic if available
            if topic_model is not None:
                bert_topic_id = topic_model.topics_[idx]

                if bert_topic_id != -1:  # -1 is outlier
                    topic_uri = URIRef(f"{BASE_URI}topic_bert_{bert_topic_id}")

                    # Add topic entity
                    topic_graph.add((topic_uri, RDF.type, DEL.Topic))

                    # Get topic info
                    topic_info = topic_model.get_topic(bert_topic_id)
                    if topic_info:
                        words_str = ", ".join([w for w, _ in topic_info[:5]])
                        topic_graph.add((topic_uri, RDFS.label,
                                       Literal(f"Topic: {words_str}", lang="en")))
                        topic_graph.add((topic_uri, DCTERMS.description,
                                       Literal(words_str, lang="en")))

                    # Link contribution to topic
                    topic_graph.add((contrib_uri, DEL.hasTopic, topic_uri))

        # Save topic statistics
        print("\nTop 10 LDA topics by frequency:")
        for topic_id, count in topic_counts.most_common(10):
            top_words = lda_model.show_topic(topic_id, topn=5)
            words = [w for w, _ in top_words]
            print(f"  Topic {topic_id}: {', '.join(words)} ({count} contributions)")

        # Merge with original graph
        output_path = Path(self.kg_path).parent / "deliberation_kg_with_topics.ttl"
        print(f"\nMerging with original graph and saving to {output_path}...")

        # Load original graph
        full_graph = Graph()
        full_graph.parse(self.kg_path, format="turtle")

        # Add topic triples
        for s, p, o in topic_graph:
            full_graph.add((s, p, o))

        # Save
        full_graph.serialize(destination=str(output_path), format="turtle")
        print(f"Saved knowledge graph with topics: {len(full_graph)} triples")

        return topic_graph

    def save_models(self, lda_model: LdaModel, dictionary: corpora.Dictionary,
                   topic_model: Optional[BERTopic] = None):
        """Save trained models"""
        print("\nSaving models...")

        # Save LDA
        lda_model.save(str(self.output_dir / "lda_model.pkl"))
        dictionary.save(str(self.output_dir / "lda_dictionary.pkl"))

        # Save BERTopic
        if topic_model:
            topic_model.save(str(self.output_dir / "bertopic_model"),
                           serialization="safetensors")

        print(f"Models saved to {self.output_dir}")

    def generate_topic_report(self, lda_model: LdaModel, topic_model: Optional[BERTopic] = None):
        """Generate human-readable topic report"""
        print("\nGenerating topic report...")

        report = []
        report.append("# Deliberation Topic Modeling Report\n")
        report.append(f"Language: {self.language}\n")
        report.append(f"Timestamp: {pd.Timestamp.now()}\n\n")

        # LDA topics
        report.append("## LDA Topics\n\n")
        for topic_id in range(lda_model.num_topics):
            top_words = lda_model.show_topic(topic_id, topn=10)
            report.append(f"### Topic {topic_id}\n")
            report.append("Words: " + ", ".join([f"{w} ({p:.3f})" for w, p in top_words]) + "\n\n")

        # BERTopic
        if topic_model:
            report.append("\n## BERTopic Topics\n\n")
            topic_info = topic_model.get_topic_info()

            for _, row in topic_info.iterrows():
                topic_id = row['Topic']
                if topic_id == -1:
                    continue

                count = row['Count']
                topic_words = topic_model.get_topic(topic_id)

                report.append(f"### Topic {topic_id} ({count} contributions)\n")
                if topic_words:
                    report.append("Words: " + ", ".join([f"{w} ({s:.3f})" for w, s in topic_words[:10]]) + "\n\n")

        # Save report
        report_path = self.output_dir / "topic_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(report)

        print(f"Report saved to {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Topic modeling for deliberation knowledge graph")
    parser.add_argument("--kg-path", type=str, required=True,
                       help="Path to knowledge graph TTL file")
    parser.add_argument("--output-dir", type=str, default="topic_models",
                       help="Output directory for models")
    parser.add_argument("--num-topics", type=int, default=20,
                       help="Number of topics to extract")
    parser.add_argument("--method", type=str, choices=["lda", "bertopic", "both"],
                       default="both", help="Topic modeling method")
    parser.add_argument("--language", type=str, default="multilingual",
                       help="Language code (multilingual, en, it, es, ca)")

    args = parser.parse_args()

    # Initialize
    modeler = TopicModeler(args.kg_path, args.output_dir, args.language)

    # Extract contributions
    df = modeler.extract_contributions()

    if len(df) == 0:
        print("No contributions found!")
        return

    # Preprocess texts
    print("\nPreprocessing texts...")
    df['tokens'] = df['text'].apply(modeler.preprocess_text)
    df = df[df['tokens'].apply(len) > 5]  # Filter short texts
    print(f"Preprocessed {len(df)} contributions")

    # Train models
    lda_model = None
    bert_model = None
    dictionary = None

    if args.method in ["lda", "both"]:
        lda_model, dictionary = modeler.train_lda(df['tokens'].tolist(), args.num_topics)

    if args.method in ["bertopic", "both"]:
        bert_model = modeler.train_bertopic(df['text'].tolist(), args.num_topics)

    # Add topics to KG
    if lda_model:
        modeler.add_topics_to_kg(df, lda_model, dictionary, bert_model)

    # Save models
    if lda_model:
        modeler.save_models(lda_model, dictionary, bert_model)

    # Generate report
    modeler.generate_topic_report(lda_model, bert_model)

    print("\n✓ Topic modeling complete!")

if __name__ == "__main__":
    main()
