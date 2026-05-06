#!/usr/bin/env python3
"""
Step 5c: Null baseline for DDI via cross-dossier and permutation tests.

Two complementary null baselines:

  1. CROSS-DOSSIER NULL
     Compute d_stance between Phase B of case X and Phase C of case Y (X≠Y).
     Rationale: if DDI is measuring something real, within-dossier d_stance
     should be LOWER than cross-dossier d_stance (citizen topics match
     same-dossier EP better than different-dossier EP).
     Note: d_salience cannot be compared cross-dossier (different topic vocabularies);
     d_topic centroids from different models are in the same embedding space so
     avg-max cosine can be computed but the per-phase BERTopic models are needed.
     We focus on d_stance here since it is directly comparable.

  2. PERMUTATION NULL ON ΔDDI
     Pool Phase A and Phase C speeches for each case; randomly split into
     two groups of the same sizes |A| and |C|; compute permuted ΔDDI.
     Repeat 2000 times → null distribution of ΔDDI under H0: no temporal effect.
     p-value = fraction of permuted |ΔDDI| >= |observed ΔDDI|.

Writes: data/null_baseline_v2/null_baseline_summary.json
"""

import json
import math
import numpy as np
from pathlib import Path

STANCE_DIR    = Path("data/stance_v2")
UNIFIED_DIR   = Path("data/unified_topic_models_v2")
DDI_DIR       = Path("data/ddi_v2")
OUT_DIR       = Path("data/null_baseline_v2")

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]
LABELS = {"case_1_covid": "COVID", "case_2_climate_target": "Climate", "case_3_pesticides": "Pesticides"}

WEIGHTS = {"d_topic": 0.40, "d_salience": 0.35, "d_stance": 0.25}
N_PERM  = 2000
RNG     = np.random.default_rng(42)


# ── Utilities ─────────────────────────────────────────────────────────────────

def jsd2(p: np.ndarray, q: np.ndarray) -> float:
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))


def stance_dist(records):
    label_map = {"entailment": 0, "support": 0,
                 "neutral": 1,
                 "contradiction": 2, "oppose": 2}
    counts = np.zeros(3)
    for r in records:
        counts[label_map.get(r.get("label", "neutral"), 1)] += 1
    total = counts.sum()
    return counts / total if total > 0 else counts + 1/3


def topic_dist(records, n_topics):
    counts = np.zeros(n_topics)
    for r in records:
        t = r["topic"]
        if t >= 0:
            counts[t] += 1
    total = counts.sum()
    return counts / total if total > 0 else counts


# ── Load all stances and topic assignments ─────────────────────────────────────

def load_all():
    data = {}
    for case in CASES:
        stances, topics, n_topics_case = {}, {}, 0
        for ph in ["A", "B", "C"]:
            p = STANCE_DIR / case / f"phase_{ph}_stance.json"
            if p.exists():
                with open(p) as f:
                    stances[ph] = json.load(f)

        with open(UNIFIED_DIR / case / "unified_assignments.json") as f:
            assigns = json.load(f)
        with open(UNIFIED_DIR / case / "unified_topics.json") as f:
            ti = json.load(f)
        n_topics_case = max(int(k) for k in ti.keys()) + 1
        by_phase = {"A": [], "B": [], "C": []}
        for rec in assigns:
            ph = rec.get("phase")
            if ph in by_phase:
                by_phase[ph].append(rec)

        with open(DDI_DIR / case / "ddi_results.json") as f:
            ddi_res = json.load(f)

        data[case] = {
            "stances":  stances,
            "topics":   by_phase,
            "n_topics": n_topics_case,
            "ddi":      ddi_res,
        }
    return data


# ── Null Baseline 1: Cross-dossier d_stance ────────────────────────────────────

def cross_dossier_null(data):
    """
    For each pair (case_b, case_c) with case_b ≠ case_c:
      d_stance(B_of_case_b, C_of_case_c)
    Compare to within-dossier d_stance(B, C).
    """
    print("\n" + "="*60)
    print("NULL BASELINE 1: Cross-dossier d_stance")
    print("="*60)

    results = {}

    # Within-dossier d_stance (reference)
    print("\nWithin-dossier d_stance(B, C):")
    within = {}
    for case in CASES:
        d = data[case]
        if "B" not in d["stances"] or "C" not in d["stances"]:
            continue
        sb = stance_dist(d["stances"]["B"])
        sc = stance_dist(d["stances"]["C"])
        jsd = jsd2(sb, sc)
        within[case] = jsd
        print(f"  {LABELS[case]}: d_stance = {jsd:.4f}")
    results["within_dossier"] = {LABELS[c]: round(v, 4) for c, v in within.items()}

    # Cross-dossier d_stance
    print("\nCross-dossier d_stance(B_of_X, C_of_Y):")
    cross = {}
    for case_b in CASES:
        for case_c in CASES:
            if case_b == case_c:
                continue
            d_b = data[case_b]
            d_c = data[case_c]
            if "B" not in d_b["stances"] or "C" not in d_c["stances"]:
                continue
            sb = stance_dist(d_b["stances"]["B"])
            sc = stance_dist(d_c["stances"]["C"])
            jsd = jsd2(sb, sc)
            key = f"{LABELS[case_b]}_B × {LABELS[case_c]}_C"
            cross[key] = round(jsd, 4)
            print(f"  {key}: d_stance = {jsd:.4f}")
    results["cross_dossier"] = cross

    # Summary stats
    cross_vals = list(cross.values())
    within_vals = list(within.values())
    print(f"\nMean within-dossier: {np.mean(within_vals):.4f}")
    print(f"Mean cross-dossier:  {np.mean(cross_vals):.4f}")
    if np.mean(cross_vals) > np.mean(within_vals):
        print("→ Within-dossier d_stance is LOWER than cross-dossier: metric discriminates correctly")
    else:
        print("→ WARNING: within-dossier d_stance >= cross-dossier (metric may not discriminate dossiers)")

    results["summary"] = {
        "mean_within": round(float(np.mean(within_vals)), 4),
        "mean_cross":  round(float(np.mean(cross_vals)), 4),
        "discriminates": bool(np.mean(cross_vals) > np.mean(within_vals)),
    }
    return results


# ── Null Baseline 2: Permutation test on ΔDDI ─────────────────────────────────

def permutation_null(data):
    """
    Pool Phase A and Phase C for each case; randomly split into |A| and |C|;
    compute ΔDDI = DDI(B, A_perm) - DDI(B, C_perm).
    p-value = fraction of permuted |ΔDDI| >= |observed ΔDDI|.
    """
    print("\n" + "="*60)
    print("NULL BASELINE 2: Permutation test on ΔDDI")
    print("="*60)

    results = {}

    for case in CASES:
        d = data[case]
        comps = d["ddi"].get("components", {})
        if "B_vs_A" not in comps or "B_vs_C" not in comps:
            print(f"  {LABELS[case]}: skip (missing components)")
            continue

        n_topics = d["n_topics"]
        b_top    = d["topics"]["B"]
        a_top    = d["topics"]["A"]
        c_top    = d["topics"]["C"]
        b_st     = d["stances"].get("B", [])
        a_st     = d["stances"].get("A", [])
        c_st     = d["stances"].get("C", [])

        d_t_a = comps["B_vs_A"]["d_topic"]
        d_t_c = comps["B_vs_C"]["d_topic"]
        n_a, n_c = len(a_top), len(c_top)

        # Pool A+C topic and stance records
        pool_top = np.array(a_top + c_top)
        pool_st  = np.array(a_st  + c_st)
        n_pool   = len(pool_top)

        # Observed ΔDDI (from DDI results file)
        delta_obs = d["ddi"]["delta_ddi"]["base"]

        print(f"\n  {LABELS[case]}: observed ΔDDI = {delta_obs:.4f}  |A|={n_a}  |C|={n_c}")

        pb    = topic_dist(b_top, n_topics)
        sb    = stance_dist(b_st)
        b_top_arr = np.array(b_top)
        b_st_arr  = np.array(b_st)
        n_b   = len(b_top_arr)

        perm_deltas = np.zeros(N_PERM)
        for i in range(N_PERM):
            # Resample Phase B
            idx_b = RNG.integers(0, n_b, n_b)
            pb_i  = topic_dist(b_top_arr[idx_b].tolist(), n_topics)
            sb_i  = stance_dist(b_st_arr[idx_b].tolist())

            # Permute pool
            perm_idx = RNG.permutation(n_pool)
            a_perm_top = pool_top[perm_idx[:n_a]].tolist()
            c_perm_top = pool_top[perm_idx[n_a:]].tolist()
            a_perm_st  = pool_st[perm_idx[:n_a]].tolist()
            c_perm_st  = pool_st[perm_idx[n_a:]].tolist()

            pa = topic_dist(a_perm_top, n_topics)
            pc = topic_dist(c_perm_top, n_topics)
            sa = stance_dist(a_perm_st)
            sc = stance_dist(c_perm_st)

            ddi_a = 0.40*d_t_a + 0.35*jsd2(pb_i, pa) + 0.25*jsd2(sb_i, sa)
            ddi_c = 0.40*d_t_c + 0.35*jsd2(pb_i, pc) + 0.25*jsd2(sb_i, sc)
            perm_deltas[i] = ddi_a - ddi_c

        # p-value: fraction of permuted |ΔDDI| >= |observed ΔDDI|
        p_val = float(np.mean(np.abs(perm_deltas) >= abs(delta_obs)))
        perm_ci = (float(np.percentile(perm_deltas, 2.5)),
                   float(np.percentile(perm_deltas, 97.5)))
        perm_mean = float(perm_deltas.mean())
        perm_std  = float(perm_deltas.std())

        print(f"  Permutation null: mean={perm_mean:.4f}  std={perm_std:.4f}"
              f"  95%CI=[{perm_ci[0]:.4f},{perm_ci[1]:.4f}]")
        print(f"  p-value (two-tailed) = {p_val:.3f}")
        if p_val > 0.05:
            print(f"  → ΔDDI not significantly different from null (p={p_val:.3f} > 0.05)")
        else:
            print(f"  → ΔDDI significantly different from null (p={p_val:.3f} <= 0.05)")

        results[case] = {
            "observed_delta_ddi": delta_obs,
            "perm_null_mean":  round(perm_mean, 4),
            "perm_null_std":   round(perm_std, 4),
            "perm_null_ci95":  [round(perm_ci[0], 4), round(perm_ci[1], 4)],
            "p_value_twotail": round(p_val, 3),
            "significant_at_05": p_val <= 0.05,
        }

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all()

    cross_results = cross_dossier_null(data)
    perm_results  = permutation_null(data)

    summary = {
        "cross_dossier_null": cross_results,
        "permutation_null":   perm_results,
    }
    with open(OUT_DIR / "null_baseline_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {OUT_DIR / 'null_baseline_summary.json'}")
