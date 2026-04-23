#!/usr/bin/env python3
"""
Step 1: Phase-stratified BERTopic modeling.
Runs BERTopic on Phase A (EP pre-consult), Phase B (HYS), Phase C (EP post-consult)
for each case. Uses a single multilingual sentence-transformer for embedding consistency.
Saves: topic assignments JSON, topic keywords JSON, embeddings NPY, model pickle.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from collections import defaultdict

# ── Config ─────────────────────────────────────────────────────────────────────

DATA_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")
OUT_DIR  = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

CASES = ["case_1_covid", "case_2_dsa", "case_3_pesticides"]

# min_topic_size per case (smaller for sparse HYS)
MIN_TOPIC_SIZE = {
    "case_1_covid":      10,
    "case_2_dsa":         5,   # only 245 HYS items
    "case_3_pesticides": 15,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_phase_texts(case_dir: Path) -> dict:
    """Load texts for each phase. Returns {phase: [(id, text), ...]}"""
    phases = {}

    # Phase B — HYS feedback
    hys_path = case_dir / "hys_feedback.json"
    with open(hys_path) as f:
        hys = json.load(f)
    phases["B"] = [
        (str(item.get("id", i)), item["text"])
        for i, item in enumerate(hys.get("feedback", []))
        if item.get("text") and len(item["text"].strip()) > 30
    ]

    # Phase A — EP pre-consultation
    pa_path = case_dir / "ep_phase_a.json"
    with open(pa_path) as f:
        pa = json.load(f)
    phases["A"] = [
        (f"A_{i}", item["text"])
        for i, item in enumerate(pa)
        if item.get("text") and len(item["text"].strip()) > 50
    ]

    # Phase C — EP post-consultation
    pc_path = case_dir / "ep_phase_c.json"
    with open(pc_path) as f:
        pc = json.load(f)
    phases["C"] = [
        (f"C_{i}", item["text"])
        for i, item in enumerate(pc)
        if item.get("text") and len(item["text"].strip()) > 50
    ]

    return phases


def run_bertopic(texts: list, min_topic_size: int, embedding_model):
    """Fit BERTopic on a list of texts. Returns (model, topics, probs, embeddings)."""
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN

    if len(texts) < min_topic_size * 2:
        print(f"    [SKIP] only {len(texts)} texts — below threshold")
        return None, None, None, None

    umap_model = UMAP(
        n_neighbors=min(15, len(texts) - 1),
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_topic_size,
        min_samples=max(1, min_topic_size // 2),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        top_n_words=10,
        verbose=True,
    )

    embeddings = embedding_model.encode(texts, show_progress_bar=True, batch_size=64)
    topics, probs = topic_model.fit_transform(texts, embeddings=embeddings)

    return topic_model, topics, probs, embeddings


def summarize_topics(model, topics) -> dict:
    """Return {topic_id: {label, words, count}}."""
    if model is None:
        return {}
    result = {}
    topic_ids = sorted(set(topics))
    counts = defaultdict(int)
    for t in topics:
        counts[t] += 1
    for tid in topic_ids:
        if tid == -1:
            continue
        words = [w for w, _ in model.get_topic(tid)]
        result[str(tid)] = {
            "label":   "_".join(words[:4]),
            "words":   words,
            "count":   counts[tid],
        }
    result["_outlier_count"] = counts[-1]
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    case_dir = DATA_DIR / case_id
    out_dir  = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    from sentence_transformers import SentenceTransformer
    emb_model = SentenceTransformer(EMBEDDING_MODEL)

    phases = load_phase_texts(case_dir)
    min_ts = MIN_TOPIC_SIZE[case_id]

    case_summary = {}

    for phase in ["A", "B", "C"]:
        items = phases[phase]
        print(f"\n  Phase {phase}: {len(items)} texts")

        if not items:
            print(f"    [SKIP] no data for Phase {phase}")
            case_summary[phase] = {"n_texts": 0, "n_topics": 0}
            continue

        ids, texts = zip(*items)

        model, topic_ids, probs, embeddings = run_bertopic(
            list(texts), min_ts, emb_model
        )

        if model is None:
            case_summary[phase] = {"n_texts": len(texts), "n_topics": 0}
            continue

        topic_info = summarize_topics(model, topic_ids)
        n_topics = len([k for k in topic_info if k != "_outlier_count"])

        print(f"    → {n_topics} topics found (outliers: {topic_info.get('_outlier_count', 0)})")

        # Save assignments
        assignments = [
            {"id": doc_id, "topic": int(t), "prob": float(p) if p is not None else None}
            for doc_id, t, p in zip(ids, topic_ids, (probs if probs is not None else [None]*len(topic_ids)))
        ]
        with open(out_dir / f"phase_{phase}_assignments.json", "w") as f:
            json.dump(assignments, f, indent=2)

        with open(out_dir / f"phase_{phase}_topics.json", "w") as f:
            json.dump(topic_info, f, ensure_ascii=False, indent=2)

        np.save(out_dir / f"phase_{phase}_embeddings.npy", embeddings)

        with open(out_dir / f"phase_{phase}_model.pkl", "wb") as f:
            pickle.dump(model, f)

        case_summary[phase] = {
            "n_texts":    len(texts),
            "n_topics":   n_topics,
            "outliers":   int(topic_info.get("_outlier_count", 0)),
        }

    with open(out_dir / "topic_summary.json", "w") as f:
        json.dump(case_summary, f, indent=2)

    print(f"\n  Saved to {out_dir}")
    return case_summary


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overall = {}
    for case_id in CASES:
        overall[case_id] = process_case(case_id)

    print("\n" + "="*60)
    print("TOPIC MODELING SUMMARY")
    print("="*60)
    for cid, s in overall.items():
        for phase, info in s.items():
            if isinstance(info, dict):
                print(f"  {cid} Phase {phase}: {info.get('n_texts',0)} texts → {info.get('n_topics',0)} topics")
