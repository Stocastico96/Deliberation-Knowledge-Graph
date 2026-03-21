#!/usr/bin/env python3
"""
Genera embeddings in batch per feedback HYS e contenuti legislativi

Input: TTL file o CSV
Output: Vector embeddings salvati in batch (Qdrant, file NPZ, o JSONL)

Supporta:
- Filtro per iniziative major (is_major=1)
- Batch processing per evitare memory overflow
- Modelli configurabili (sentence-transformers)
"""

import argparse
import json
import csv
from pathlib import Path
from typing import List, Dict, Generator
import numpy as np
from datetime import datetime

# Optional: sentence-transformers (install if needed)
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")

class EmbeddingGenerator:
    """Generate and store embeddings in batches"""

    def __init__(self, model_name='all-MiniLM-L6-v2', batch_size=100):
        """
        Args:
            model_name: HuggingFace model (default: 384-dim, fast)
            batch_size: Batch size for encoding
        """
        self.batch_size = batch_size

        if HAS_SENTENCE_TRANSFORMERS:
            print(f"Loading model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            print(f"  Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        else:
            self.model = None

    def read_feedback_csv(self, csv_path: Path, filter_major=False, limit=None) -> Generator:
        """
        Read feedback from CSV in streaming mode

        Yields: (id, text, metadata) tuples
        """
        count = 0

        # If filter_major, need to load initiatives first
        major_initiatives = set()
        if filter_major:
            init_path = csv_path.parent / "initiatives.csv"
            if init_path.exists():
                with open(init_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('is_major') == '1':
                            major_initiatives.add(row['id'])
                print(f"Filtered to {len(major_initiatives)} major initiatives")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Filter by major initiatives
                if filter_major and row['initiative_id'] not in major_initiatives:
                    continue

                # Skip empty feedback
                text = row.get('feedback', '').strip()
                if not text:
                    continue

                metadata = {
                    'feedback_id': row['id'],
                    'initiative_id': row['initiative_id'],
                    'country': row.get('country', ''),
                    'user_type': row.get('user_type', ''),
                    'language': row.get('language', '')
                }

                yield (row['id'], text, metadata)

                count += 1
                if limit and count >= limit:
                    break

    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts"""
        if not self.model:
            raise RuntimeError("Model not loaded. Install sentence-transformers.")

        return self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    def process_and_save(self, csv_path: Path, output_path: Path,
                         filter_major=False, limit=None, output_format='npz'):
        """
        Process feedback and save embeddings

        Args:
            csv_path: Input CSV file
            output_path: Output file path
            filter_major: Only process major initiatives
            limit: Limit number of feedback
            output_format: 'npz', 'jsonl', or 'npy'
        """
        print(f"Processing feedback from {csv_path}...")
        print(f"Output: {output_path} ({output_format})")
        print()

        all_embeddings = []
        all_metadata = []
        batch_texts = []
        batch_ids = []
        batch_meta = []

        processed = 0
        start_time = datetime.now()

        for feedback_id, text, metadata in self.read_feedback_csv(csv_path, filter_major, limit):
            batch_texts.append(text)
            batch_ids.append(feedback_id)
            batch_meta.append(metadata)

            # Process batch when full
            if len(batch_texts) >= self.batch_size:
                embeddings = self.generate_embeddings_batch(batch_texts)

                all_embeddings.append(embeddings)
                all_metadata.extend(batch_meta)

                processed += len(batch_texts)
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = processed / elapsed if elapsed > 0 else 0

                print(f"  Processed {processed} feedback ({rate:.1f} items/sec)")

                # Clear batch
                batch_texts = []
                batch_ids = []
                batch_meta = []

        # Process remaining
        if batch_texts:
            embeddings = self.generate_embeddings_batch(batch_texts)
            all_embeddings.append(embeddings)
            all_metadata.extend(batch_meta)
            processed += len(batch_texts)

        # Combine all embeddings
        final_embeddings = np.vstack(all_embeddings)

        # Save based on format
        if output_format == 'npz':
            # Save as compressed numpy
            np.savez_compressed(
                output_path,
                embeddings=final_embeddings,
                metadata=np.array(all_metadata, dtype=object)
            )
        elif output_format == 'jsonl':
            # Save as JSONL (less efficient but readable)
            with open(output_path, 'w') as f:
                for emb, meta in zip(final_embeddings, all_metadata):
                    obj = {
                        'embedding': emb.tolist(),
                        'metadata': meta
                    }
                    f.write(json.dumps(obj) + '\n')

        elapsed = datetime.now() - start_time
        size_mb = Path(output_path).stat().st_size / 1024 / 1024

        print(f"\n{'='*60}")
        print(f"✅ Generated {processed} embeddings in {elapsed}")
        print(f"   Embedding shape: {final_embeddings.shape}")
        print(f"   File size: {size_mb:.1f} MB")
        print(f"   Output: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Generate embeddings for HYS feedback in batches'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='/tmp/hys_export/feedback.csv',
        help='Input CSV file with feedback'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='hys_embeddings.npz',
        help='Output file for embeddings'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-MiniLM-L6-v2',
        help='Sentence transformer model name'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for encoding'
    )
    parser.add_argument(
        '--filter-major',
        action='store_true',
        help='Only process major initiatives'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of feedback to process'
    )
    parser.add_argument(
        '--format',
        type=str,
        default='npz',
        choices=['npz', 'jsonl'],
        help='Output format'
    )

    args = parser.parse_args()

    if not HAS_SENTENCE_TRANSFORMERS:
        print("ERROR: sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        return 1

    generator = EmbeddingGenerator(model_name=args.model, batch_size=args.batch_size)

    generator.process_and_save(
        csv_path=Path(args.input),
        output_path=Path(args.output),
        filter_major=args.filter_major,
        limit=args.limit,
        output_format=args.format
    )

if __name__ == '__main__':
    main()
