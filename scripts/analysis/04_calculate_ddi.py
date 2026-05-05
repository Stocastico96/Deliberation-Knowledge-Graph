#!/usr/bin/env python3
"""
Step 4: Compute Deliberative Distance Index (DDI) and ΔDDI.

DDI(B, X) = 0.40·d_topic + 0.35·d_salience + 0.25·d_stance

Where:
  d_topic    = 1 - AvgMaxCosine_sym(centroids_B, centroids_X)  (symmetric avg-max cosine)
  d_salience = JSD of topic-weight distributions between phases
  d_stance   = JSD of (support, neutral, oppose) distributions between B and X

ΔDDI = DDI(B, A) − DDI(B, C)  positive → convergence after consultation

Consultation inclusivity (d_diversity) is computed and saved as a
descriptive variable, NOT included in the DDI formula.

Topological graph metrics (CPBR, MPET, CPBC, r_BC) are in step 04b.
"""

import json
import math
import numpy as np
from pathlib import Path
from collections import Counter

# ── Config ─────────────────────────────────────────────────────────────────────

ALIGNMENT_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/alignment_v2")
STANCE_DIR    = Path("/home/svagnoni/deliberation-knowledge-graph/data/stance_v2")
TOPIC_DIR     = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")
UNIFIED_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/unified_topic_models_v2")
DATASET_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")
OUT_DIR       = Path("/home/svagnoni/deliberation-knowledge-graph/data/ddi_v2")

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]

WEIGHT_CONFIGS = {
    "base":         {"d_topic": 0.40, "d_salience": 0.35, "d_stance": 0.25},
    "uniform":      {"d_topic": 0.33, "d_salience": 0.33, "d_stance": 0.34},
    "topic_heavy":  {"d_topic": 0.60, "d_salience": 0.25, "d_stance": 0.15},
    "stance_heavy": {"d_topic": 0.25, "d_salience": 0.30, "d_stance": 0.45},
}

# ── Metrics ────────────────────────────────────────────────────────────────────

def jsd(p: dict, q: dict) -> float:
    """Jensen-Shannon divergence in bits (log base 2), range [0, 1]."""
    keys = sorted(set(p) | set(q))
    pp = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    qq = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    pp /= (pp.sum() + 1e-12)
    qq /= (qq.sum() + 1e-12)
    m = 0.5 * (pp + qq)
    def kl(a, b):
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(pp, m) + 0.5 * kl(qq, m)


def shannon_entropy(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((v / total) * math.log(v / total) for v in counts.values() if v > 0)


def d_topic_from_jaccard(jaccard: float) -> float:
    return 1.0 - jaccard


def d_salience_unified(unified_assignments: list, phase_b: str, phase_x: str) -> float:
    """
    Compute JSD between phase topic-weight distributions using the UNIFIED topic model.
    Both phases share the same topic vocabulary, so IDs are semantically comparable.
    Excludes outlier documents (topic == -1).
    """
    counts = {phase_b: {}, phase_x: {}}
    for a in unified_assignments:
        ph = a["phase"]
        if ph not in counts or a["topic"] == -1:
            continue
        t = str(a["topic"])
        counts[ph][t] = counts[ph].get(t, 0) + 1
    all_topics = sorted(set(counts[phase_b]) | set(counts[phase_x]), key=int)
    def to_dist(ph):
        total = sum(counts[ph].values()) + 1e-12
        return {t: counts[ph].get(t, 0) / total for t in all_topics}
    return jsd(to_dist(phase_b), to_dist(phase_x))


def d_stance_metric(dist_b: dict, dist_x: dict) -> float:
    keys = ["support", "neutral", "oppose"]
    return jsd({k: dist_b.get(k, 0.0) for k in keys},
               {k: dist_x.get(k, 0.0) for k in keys})


def consultation_inclusivity(hys_feedback: list) -> float:
    """Descriptive only — NOT part of DDI. Shannon diversity of actor types."""
    user_types = Counter(f.get("user_type", "ANONYMOUS") for f in hys_feedback)
    K = len(user_types)
    if K <= 1:
        return 0.0
    return round(shannon_entropy(user_types) / math.log(K), 4)


def ddi(d_t, d_sal, d_s, weights: dict) -> float:
    return (weights["d_topic"]    * d_t
          + weights["d_salience"] * d_sal
          + weights["d_stance"]   * d_s)


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    out_dir = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    align_path = ALIGNMENT_DIR / case_id / "alignment_results.json"
    if not align_path.exists():
        print(f"  [SKIP] No alignment results — run step 2 first")
        return None
    with open(align_path) as f:
        alignment = json.load(f)

    def load_stance_dist(phase):
        p = STANCE_DIR / case_id / "stance_summary.json"
        if not p.exists():
            return None
        with open(p) as f:
            s = json.load(f)
        return s.get(phase, {}).get("distribution")

    def load_topics(phase):
        p = TOPIC_DIR / case_id / f"phase_{phase}_topics.json"
        if not p.exists():
            return {}
        with open(p) as f:
            return json.load(f)

    with open(DATASET_DIR / case_id / "hys_feedback.json") as f:
        hys_feedback = json.load(f).get("feedback", [])

    # Load unified topic assignments (shared vocabulary across all phases)
    unified_path = UNIFIED_DIR / case_id / "unified_assignments.json"
    if not unified_path.exists():
        print(f"  [WARN] No unified assignments — run step 01b first; falling back to per-phase (INCORRECT) d_salience")
        unified_assignments = None
    else:
        with open(unified_path) as f:
            unified_assignments = json.load(f)

    topics_b = load_topics("B")
    topics_a = load_topics("A")
    topics_c = load_topics("C")

    inclusivity = consultation_inclusivity(hys_feedback)
    has_a = bool(topics_a) and "B_vs_A" in alignment
    has_c = bool(topics_c) and "B_vs_C" in alignment

    results = {
        "components": {},
        "ddi": {},
        "delta_ddi": None,
        "descriptive": {"inclusivity": inclusivity},
    }

    if has_c:
        amc_bc  = alignment["B_vs_C"].get("avg_max_cosine")
        d_t_c   = round(1.0 - amc_bc, 4) if amc_bc is not None \
                  else d_topic_from_jaccard(alignment["B_vs_C"].get("jaccard_index", 0.0))
        d_sal_c = round(d_salience_unified(unified_assignments, "B", "C"), 4) \
                  if unified_assignments else 0.5
        stance_b, stance_c = load_stance_dist("B"), load_stance_dist("C")
        d_s_c   = d_stance_metric(stance_b, stance_c) if stance_b and stance_c else 0.5

        results["components"]["B_vs_C"] = {
            "d_topic":    round(d_t_c, 4),
            "d_salience": round(d_sal_c, 4),
            "d_stance":   round(d_s_c, 4),
        }
        results["ddi"]["B_vs_C"] = {
            wname: round(ddi(d_t_c, d_sal_c, d_s_c, weights), 4)
            for wname, weights in WEIGHT_CONFIGS.items()
        }
        print(f"  DDI(B,C) = {results['ddi']['B_vs_C']}")

    if has_a:
        amc_ba  = alignment["B_vs_A"].get("avg_max_cosine")
        d_t_a   = round(1.0 - amc_ba, 4) if amc_ba is not None \
                  else d_topic_from_jaccard(alignment["B_vs_A"].get("jaccard_index", 0.0))
        d_sal_a = round(d_salience_unified(unified_assignments, "B", "A"), 4) \
                  if unified_assignments else 0.5
        stance_a, stance_b_dist = load_stance_dist("A"), load_stance_dist("B")
        d_s_a   = d_stance_metric(stance_b_dist, stance_a) if stance_b_dist and stance_a else 0.5

        results["components"]["B_vs_A"] = {
            "d_topic":    round(d_t_a, 4),
            "d_salience": round(d_sal_a, 4),
            "d_stance":   round(d_s_a, 4),
        }
        results["ddi"]["B_vs_A"] = {
            wname: round(ddi(d_t_a, d_sal_a, d_s_a, weights), 4)
            for wname, weights in WEIGHT_CONFIGS.items()
        }
        print(f"  DDI(B,A) = {results['ddi']['B_vs_A']}")

    if has_a and has_c:
        results["delta_ddi"] = {
            wname: round(results["ddi"]["B_vs_A"][wname] - results["ddi"]["B_vs_C"][wname], 4)
            for wname in WEIGHT_CONFIGS
        }
        print(f"  ΔDDI     = {results['delta_ddi']}")

    with open(out_dir / "ddi_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved to {out_dir}")
    return results


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    all_results = {}
    for case_id in target_cases:
        r = process_case(case_id)
        if r:
            all_results[case_id] = r

    print("\n" + "="*60)
    print("DDI SUMMARY (base weights)")
    print("="*60)
    for cid, r in all_results.items():
        ddi_bc = r.get("ddi", {}).get("B_vs_C", {}).get("base", "N/A")
        ddi_ba = r.get("ddi", {}).get("B_vs_A", {}).get("base", "N/A")
        delta  = r.get("delta_ddi", {})
        print(f"  {cid}:")
        print(f"    DDI(B,C)={ddi_bc}  DDI(B,A)={ddi_ba}  ΔDDI={delta.get('base','N/A') if delta else 'N/A'}")

    with open(OUT_DIR / "ddi_summary.json", "w") as f:
        json.dump(all_results, f, indent=2)
