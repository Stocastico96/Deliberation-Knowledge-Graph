#!/usr/bin/env python3
"""
Step 2: Topic alignment between phases.
Computes cosine similarity between BERTopic topic centroids across phases.
Classifies each B-topic as: aligned (θ≥0.65), partial (0.40≤θ<0.65), or gap (<0.40).
Also computes the Topic Jaccard Index (J_BC) as a graph-structural metric.
"""

import json
import numpy as np
from pathlib import Path
from itertools import product

# ── Config ─────────────────────────────────────────────────────────────────────

TOPIC_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")
OUT_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/alignment_v2")

CASES = ["case_1_covid", "case_2_dsa", "case_3_pesticides"]

ALIGNED_THRESHOLD = 0.65
PARTIAL_THRESHOLD = 0.40

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_phase_data(case_dir: Path, phase: str):
    """Load topic info and embeddings for a phase."""
    topic_path = case_dir / f"phase_{phase}_topics.json"
    assign_path = case_dir / f"phase_{phase}_assignments.json"
    emb_path    = case_dir / f"phase_{phase}_embeddings.npy"

    if not topic_path.exists() or not emb_path.exists():
        return None, None, None

    with open(topic_path) as f:
        topics = json.load(f)
    with open(assign_path) as f:
        assignments = json.load(f)

    embeddings = np.load(emb_path)
    return topics, assignments, embeddings


def compute_topic_centroids(topics: dict, assignments: list, embeddings: np.ndarray) -> dict:
    """Compute mean embedding (centroid) for each topic."""
    topic_indices = {}
    for i, item in enumerate(assignments):
        tid = str(item["topic"])
        if tid == "-1":
            continue
        topic_indices.setdefault(tid, []).append(i)

    centroids = {}
    for tid, indices in topic_indices.items():
        if tid in topics:
            centroids[tid] = embeddings[indices].mean(axis=0)
    return centroids


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_n = a / (np.linalg.norm(a) + 1e-9)
    b_n = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a_n, b_n))


def build_similarity_matrix(centroids_b: dict, centroids_other: dict) -> dict:
    """
    Compute pairwise cosine similarity between B topics and another phase's topics.
    Returns: {b_topic_id: {other_topic_id: sim, ...}, ...}
    """
    matrix = {}
    for bid, bvec in centroids_b.items():
        matrix[bid] = {}
        for oid, ovec in centroids_other.items():
            matrix[bid][oid] = cosine_similarity(bvec, ovec)
    return matrix


def classify_alignment(sim_matrix: dict) -> dict:
    """
    For each B topic, find its best-matching other-phase topic and classify.
    Returns: {b_topic_id: {best_match, best_sim, label}}
    """
    result = {}
    for bid, sims in sim_matrix.items():
        if not sims:
            result[bid] = {"best_match": None, "best_sim": 0.0, "label": "gap"}
            continue
        best_match = max(sims, key=sims.get)
        best_sim   = sims[best_match]
        if best_sim >= ALIGNED_THRESHOLD:
            label = "aligned"
        elif best_sim >= PARTIAL_THRESHOLD:
            label = "partial"
        else:
            label = "gap"
        result[bid] = {"best_match": best_match, "best_sim": round(best_sim, 4), "label": label}
    return result


def jaccard_topic_overlap(topics_b: dict, topics_c: dict, threshold: float = ALIGNED_THRESHOLD) -> float:
    """
    Topic Jaccard Index: fraction of B and C topics that are mutually aligned.
    J = |{b in B : best_sim(b,C) >= θ}| / |B ∪ C_unmatched|
    Simplified: |aligned pairs| / (|B| + |C| - |aligned pairs|)
    """
    nb = len([k for k in topics_b if k != "_outlier_count"])
    nc = len([k for k in topics_c if k != "_outlier_count"])
    if nb == 0 or nc == 0:
        return 0.0
    # count B topics that align with at least one C topic above threshold
    aligned = 0
    for bid, bvec in topics_b.items():
        if bid == "_outlier_count": continue
        # (centroids computed separately; this function only uses counts)
    # will be computed properly in process_case using centroids
    return 0.0   # placeholder, overridden below


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    case_dir = TOPIC_DIR / case_id
    out_dir  = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load all phases
    phase_data = {}
    for phase in ["A", "B", "C"]:
        topics, assignments, embeddings = load_phase_data(case_dir, phase)
        if topics is not None:
            centroids = compute_topic_centroids(topics, assignments, embeddings)
            phase_data[phase] = {"topics": topics, "assignments": assignments,
                                 "embeddings": embeddings, "centroids": centroids}
            print(f"  Phase {phase}: {len(centroids)} topic centroids")
        else:
            print(f"  Phase {phase}: no data")

    results = {}

    # B ↔ A alignment (if A exists)
    if "B" in phase_data and "A" in phase_data:
        sim_ba = build_similarity_matrix(phase_data["B"]["centroids"], phase_data["A"]["centroids"])
        align_ba = classify_alignment(sim_ba)
        results["B_vs_A"] = {
            "alignment": align_ba,
            "summary": {
                "aligned": sum(1 for v in align_ba.values() if v["label"] == "aligned"),
                "partial":  sum(1 for v in align_ba.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_ba.values() if v["label"] == "gap"),
            },
        }
        print(f"  B vs A: {results['B_vs_A']['summary']}")

    # B ↔ C alignment
    if "B" in phase_data and "C" in phase_data:
        sim_bc = build_similarity_matrix(phase_data["B"]["centroids"], phase_data["C"]["centroids"])
        align_bc = classify_alignment(sim_bc)

        # Topic Jaccard Index
        nb = len(phase_data["B"]["centroids"])
        nc = len(phase_data["C"]["centroids"])
        n_aligned_b = sum(1 for v in align_bc.values() if v["label"] == "aligned")
        # From C side too
        sim_cb = build_similarity_matrix(phase_data["C"]["centroids"], phase_data["B"]["centroids"])
        align_cb = classify_alignment(sim_cb)
        n_aligned_c = sum(1 for v in align_cb.values() if v["label"] == "aligned")
        # Jaccard: |intersection| / |union|
        # approximate: min(aligned_b, aligned_c) / (nb + nc - min(aligned_b, aligned_c))
        n_intersection = min(n_aligned_b, n_aligned_c)
        n_union = nb + nc - n_intersection
        jaccard = round(n_intersection / n_union, 4) if n_union > 0 else 0.0

        results["B_vs_C"] = {
            "alignment": align_bc,
            "summary": {
                "aligned": n_aligned_b,
                "partial":  sum(1 for v in align_bc.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_bc.values() if v["label"] == "gap"),
            },
            "jaccard_index": jaccard,
        }
        print(f"  B vs C: {results['B_vs_C']['summary']}, Jaccard={jaccard}")

    # A ↔ C alignment (change over time, EP side)
    if "A" in phase_data and "C" in phase_data:
        sim_ac = build_similarity_matrix(phase_data["A"]["centroids"], phase_data["C"]["centroids"])
        align_ac = classify_alignment(sim_ac)
        results["A_vs_C"] = {
            "alignment": align_ac,
            "summary": {
                "aligned": sum(1 for v in align_ac.values() if v["label"] == "aligned"),
                "partial":  sum(1 for v in align_ac.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_ac.values() if v["label"] == "gap"),
            },
        }
        print(f"  A vs C: {results['A_vs_C']['summary']}")

    with open(out_dir / "alignment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"  Saved to {out_dir}")
    return results


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for case_id in CASES:
        process_case(case_id)
