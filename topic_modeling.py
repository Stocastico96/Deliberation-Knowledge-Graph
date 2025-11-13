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
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?contrib ?text ?process ?date ?platform
        WHERE {
            ?contrib a del:Contribution .
            {
                ?contrib del:text ?text .
            } UNION {
                ?contrib rdfs:comment ?text .
            }
            OPTIONAL {
                ?process del:hasContribution ?contrib .
                OPTIONAL { ?process del:platform ?platform }
            }
            OPTIONAL { ?contrib dcterms:created ?date }
            OPTIONAL { ?contrib del:timestamp ?date }

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
        """Train BERTopic model with BAAI/bge-m3 multilingual embeddings"""
        print(f"\nTraining BERTopic with {num_topics} topics (this may take a while)...")
        print("Using BAAI/bge-m3 for state-of-the-art multilingual embeddings...")

        # Use BAAI/bge-m3 - best multilingual model (100+ languages, 8192 context)
        embedding_model = SentenceTransformer("BAAI/bge-m3")

        # bge-m3 specific: use mean pooling and normalization
        embedding_model.max_seq_length = 8192  # Full context window

        # Configure UMAP with parameters to reduce language clustering
        from umap import UMAP
        umap_model = UMAP(
            n_neighbors=10,   # Fewer neighbors to focus on local semantic structure
            n_components=10,  # More dimensions to preserve semantic nuances
            min_dist=0.0,     # Allow tight clusters
            metric='cosine',
            random_state=42
        )

        # Configure HDBSCAN with parameters for better semantic clustering
        from hdbscan import HDBSCAN
        hdbscan_model = HDBSCAN(
            min_cluster_size=20,      # Even smaller clusters for more granular topics
            min_samples=3,            # Very low threshold to find more specific clusters
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )

        # Pre-generate embeddings in batches with disk caching to avoid memory issues
        import numpy as np
        import os

        embeddings_cache_file = "/tmp/bge_embeddings_cache.npy"

        if os.path.exists(embeddings_cache_file):
            print(f"Loading cached embeddings from {embeddings_cache_file}...")
            all_embeddings = np.load(embeddings_cache_file)
            print(f"Loaded {len(all_embeddings)} cached embeddings")
        else:
            print("Generating embeddings in batches with disk caching...")
            batch_size = 16  # Reduce batch size further for memory
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = embedding_model.encode(
                    batch,
                    show_progress_bar=False,
                    batch_size=batch_size,
                    normalize_embeddings=True  # Normalize for cosine similarity
                )
                all_embeddings.extend(batch_embeddings)

                # Progress indicator and periodic saving
                if (i + batch_size) % 500 == 0:
                    print(f"Processed {i + batch_size}/{len(texts)} texts...")
                    # Save intermediate results
                    np.save(embeddings_cache_file + ".tmp", np.array(all_embeddings))

            # Convert to numpy array and save
            all_embeddings = np.array(all_embeddings)
            print(f"Generated embeddings for {len(all_embeddings)} texts")
            print(f"Saving embeddings to cache: {embeddings_cache_file}")
            np.save(embeddings_cache_file, all_embeddings)
            print("Embeddings cached successfully")

        # Configure BERTopic with custom models
        # Note: nr_topics="auto" lets HDBSCAN determine optimal number first,
        # then we can optionally reduce. Set to None for no reduction.
        topic_model = BERTopic(
            embedding_model=embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            language="multilingual",
            calculate_probabilities=False,
            nr_topics=None,  # Don't force reduction, let HDBSCAN find natural clusters
            verbose=True
        )

        # Train with pre-computed embeddings
        topics, probs = topic_model.fit_transform(texts, embeddings=all_embeddings)

        print("BERTopic training complete")
        print(f"Initial topics found: {len(set(topics))}")
        print(f"After reduction to {num_topics} topics")

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
            if lda_model and dictionary:
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
        if lda_model and topic_counts:
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

    def save_models(self, lda_model: Optional[LdaModel], dictionary: Optional[corpora.Dictionary],
                   topic_model: Optional[BERTopic] = None):
        """Save trained models"""
        print("\nSaving models...")

        # Save LDA
        if lda_model and dictionary:
            lda_model.save(str(self.output_dir / "lda_model.pkl"))
            dictionary.save(str(self.output_dir / "lda_dictionary.pkl"))

        # Save BERTopic
        if topic_model:
            topic_model.save(str(self.output_dir / "bertopic_model"),
                           serialization="safetensors")

        print(f"Models saved to {self.output_dir}")

    def save_topics_json(self, topic_model: BERTopic, df: pd.DataFrame = None):
        """Save topics in JSON format for citizen interface with platform metadata"""
        print("\nGenerating topics JSON for citizen interface...")

        topic_info = topic_model.get_topic_info()

        # Get topic assignments for each document
        topics_per_doc = topic_model.topics_

        # Calculate platform distribution per topic if df provided
        platform_distributions = {}
        if df is not None and 'platform' in df.columns and len(topics_per_doc) == len(df):
            df_with_topics = df.copy()
            df_with_topics['topic'] = topics_per_doc

            for topic_id in df_with_topics['topic'].unique():
                if topic_id == -1:  # Skip outliers
                    continue

                topic_docs = df_with_topics[df_with_topics['topic'] == topic_id]
                platform_counts = topic_docs['platform'].value_counts().to_dict()

                # Remove None values and calculate percentages
                platform_counts = {k: v for k, v in platform_counts.items() if k and str(k) != 'None'}
                total = sum(platform_counts.values())

                if total > 0:
                    platform_distributions[topic_id] = {
                        'counts': platform_counts,
                        'percentages': {k: round(v/total * 100, 1) for k, v in platform_counts.items()},
                        'dominant': max(platform_counts, key=platform_counts.get)
                    }

        topics = []
        for _, row in topic_info.iterrows():
            topic_id = row['Topic']
            if topic_id == -1:  # Skip outlier topic
                continue

            count = row['Count']
            topic_words = topic_model.get_topic(topic_id)

            # Get top keywords
            keywords = [word for word, score in topic_words[:10]] if topic_words else []

            # Get representative documents (sample contributions)
            try:
                repr_docs = topic_model.get_representative_docs(topic_id)
                sample_contributions = repr_docs[:3] if repr_docs else []
            except:
                sample_contributions = []

            # Get platform info for this topic
            platform_info = platform_distributions.get(topic_id, {})
            platforms_list = list(platform_info.get('counts', {}).keys()) if platform_info else ["Multiple"]

            topic_data = {
                "id": int(topic_id),
                "name": f"Topic {topic_id}",
                "keywords": keywords,
                "contributions_count": int(count),
                "sample_contributions": sample_contributions,
                "platforms": platforms_list,
                "platform_distribution": platform_info.get('percentages', {}),
                "dominant_platform": platform_info.get('dominant', None)
            }
            topics.append(topic_data)

        # Sort by contribution count
        topics.sort(key=lambda x: x['contributions_count'], reverse=True)

        output = {
            "topics": topics,
            "total_topics": len(topics),
            "timestamp": pd.Timestamp.now().isoformat()
        }

        json_path = self.output_dir / "topics_summary.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"Topics JSON saved to {json_path}")
        print(f"Platform distribution calculated for {len(platform_distributions)} topics")

    def generate_topic_report(self, lda_model: LdaModel, topic_model: Optional[BERTopic] = None):
        """Generate human-readable topic report"""
        print("\nGenerating topic report...")

        report = []
        report.append("# Deliberation Topic Modeling Report\n")
        report.append(f"Language: {self.language}\n")
        report.append(f"Timestamp: {pd.Timestamp.now()}\n\n")

        # LDA topics
        if lda_model:
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

    # Save models FIRST (before potentially failing add_topics_to_kg)
    if lda_model or bert_model:
        modeler.save_models(lda_model, dictionary, bert_model)

    # Save topics JSON for citizen interface (with platform metadata)
    if bert_model:
        modeler.save_topics_json(bert_model, df)

    # Add topics to KG (optional, can fail without breaking everything)
    # Temporarily disabled due to indexing issues - will fix separately
    # if lda_model or bert_model:
    #     modeler.add_topics_to_kg(df, lda_model, dictionary, bert_model)

    # Generate report
    if lda_model or bert_model:
        modeler.generate_topic_report(lda_model, bert_model)

    print("\n✓ Topic modeling complete!")

if __name__ == "__main__":
    main()
