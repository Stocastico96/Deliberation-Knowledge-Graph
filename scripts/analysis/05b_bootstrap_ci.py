#!/usr/bin/env python3
"""
Step 5b: Bootstrap confidence intervals on DDI and ΔDDI.

For each case and each comparison (B_vs_A, B_vs_C):
  - Resample Phase B, Phase A, Phase C with replacement (n_boot=2000)
  - Phase B is resampled ONCE per iteration (shared denominator for both DDIs)
  - d_topic is held fixed (centroids are computed from BERTopic, not per-document)
  - d_salience_boot and d_stance_boot are computed from resampled distributions
  - Reports 95% CI (percentile method) for DDI(B,A), DDI(B,C), and ΔDDI

Also runs robustness check for Problem 3:
  - Filters Phase A to documents strictly before consultation open date (< t_open)
  - Recomputes d_salience and d_stance for the corrected Phase A
  - Reports ΔDDI under corrected Phase A vs. original

Writes: data/bootstrap_ci_v2/{case}/bootstrap_results.json
        data/bootstrap_ci_v2/bootstrap_summary.json
"""

import json
import math
import numpy as np
from pathlib import Path
from collections import Counter

UNIFIED_DIR  = Path("data/unified_topic_models_v2")
STANCE_DIR   = Path("data/stance_v2")
DATASET_DIR  = Path("data/pilot_study_dataset_v2")
DDI_DIR      = Path("data/ddi_v2")
OUT_DIR      = Path("data/bootstrap_ci_v2")

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]

WEIGHTS = {"d_topic": 0.40, "d_salience": 0.35, "d_stance": 0.25}

N_BOOT = 2000
RNG    = np.random.default_rng(42)


# ── Utilities ─────────────────────────────────────────────────────────────────

def jsd2(p: np.ndarray, q: np.ndarray) -> float:
    """JSD in bits (log2), range [0,1]."""
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))


def topic_dist(records, n_topics):
    """Frequency distribution over topic IDs from a list of assignment records."""
    counts = np.zeros(n_topics)
    for r in records:
        t = r["topic"]
        if t >= 0:
            counts[t] += 1
    total = counts.sum()
    return counts / total if total > 0 else counts


def stance_dist(records):
    """Distribution over (support, neutral, oppose) from stance records."""
    label_map = {"entailment": "support", "neutral": "neutral",
                 "contradiction": "oppose", "support": "support",
                 "oppose": "oppose"}
    counts = np.zeros(3)  # support, neutral, oppose
    idx = {"support": 0, "neutral": 1, "oppose": 2}
    for r in records:
        lbl = label_map.get(r.get("label", "neutral"), "neutral")
        counts[idx[lbl]] += 1
    total = counts.sum()
    return counts / total if total > 0 else counts


def bootstrap_ddi(b_topic, x_topic, b_stance, x_stance,
                  d_topic_fixed, n_topics, n_boot=N_BOOT):
    """
    Bootstrap DDI(B, X) over n_boot resamples.
    Returns array of n_boot DDI values.
    """
    b_topic  = np.array(b_topic)
    x_topic  = np.array(x_topic)
    b_stance = np.array(b_stance)
    x_stance = np.array(x_stance)
    n_b_t, n_x_t = len(b_topic), len(x_topic)
    n_b_s, n_x_s = len(b_stance), len(x_stance)

    ddis = np.zeros(n_boot)
    for i in range(n_boot):
        idx_b_t = RNG.integers(0, n_b_t, n_b_t)
        idx_x_t = RNG.integers(0, n_x_t, n_x_t)
        idx_b_s = RNG.integers(0, n_b_s, n_b_s)
        idx_x_s = RNG.integers(0, n_x_s, n_x_s)

        pb = topic_dist(b_topic[idx_b_t].tolist(), n_topics)
        px = topic_dist(x_topic[idx_x_t].tolist(), n_topics)
        sb = stance_dist(b_stance[idx_b_s].tolist())
        sx = stance_dist(x_stance[idx_x_s].tolist())

        d_sal  = jsd2(pb, px)
        d_st   = jsd2(sb, sx)
        ddis[i] = (WEIGHTS["d_topic"]    * d_topic_fixed
                 + WEIGHTS["d_salience"] * d_sal
                 + WEIGHTS["d_stance"]   * d_st)
    return ddis


def ci95(arr):
    lo, hi = np.percentile(arr, [2.5, 97.5])
    return float(lo), float(hi)


# ── Per-case processing ────────────────────────────────────────────────────────

def process_case(case_id):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    out_dir = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load metadata (consultation dates)
    with open(DATASET_DIR / case_id / "metadata.json") as f:
        meta = json.load(f)
    t_open  = meta["consultation_open"]   # YYYY-MM-DD
    t_close = meta["consultation_close"]

    # Load unified topic assignments
    with open(UNIFIED_DIR / case_id / "unified_assignments.json") as f:
        assignments = json.load(f)
    with open(UNIFIED_DIR / case_id / "unified_topics.json") as f:
        topics_info = json.load(f)
    n_topics = max(int(k) for k in topics_info.keys()) + 1

    by_phase = {"A": [], "B": [], "C": []}
    for rec in assignments:
        ph = rec.get("phase")
        if ph in by_phase:
            by_phase[ph].append(rec)

    # Load per-document stance labels
    def load_stance(phase):
        p = STANCE_DIR / case_id / f"phase_{phase}_stance.json"
        if not p.exists():
            return []
        with open(p) as f:
            return json.load(f)

    stance = {ph: load_stance(ph) for ph in ["A", "B", "C"]}

    # Load fixed d_topic values
    with open(DDI_DIR / case_id / "ddi_results.json") as f:
        ddi_res = json.load(f)
    comps = ddi_res.get("components", {})

    results = {}

    for comp_key, ph_x in [("B_vs_A", "A"), ("B_vs_C", "C")]:
        if comp_key not in comps:
            print(f"  [{comp_key}] no data, skipping")
            continue
        d_topic_fixed = comps[comp_key]["d_topic"]
        n_x = len(by_phase[ph_x])
        n_b = len(by_phase["B"])
        print(f"  {comp_key}: n_B={n_b}, n_{ph_x}={n_x}")

        if n_x < 5:
            print(f"  [{comp_key}] too few documents in Phase {ph_x}, skip")
            continue

        # --- Standard bootstrap (Phase A = all speeches before t_close) ---
        ddis_b = bootstrap_ddi(
            by_phase["B"], by_phase[ph_x],
            stance["B"],   stance[ph_x],
            d_topic_fixed, n_topics
        )
        lo_b, hi_b = ci95(ddis_b)
        mean_b = float(ddis_b.mean())

        res = {
            "n_B": n_b, f"n_{ph_x}": n_x,
            "d_topic_fixed": d_topic_fixed,
            "ddi_mean":  round(mean_b, 4),
            "ddi_ci95":  [round(lo_b, 4), round(hi_b, 4)],
        }
        print(f"    DDI({comp_key}) boot mean={mean_b:.4f}  95%CI=[{lo_b:.4f},{hi_b:.4f}]")

        # --- Robustness check: Phase A filtered to before t_open ---
        if ph_x == "A":
            # Filter topic records: need date — only possible for ep_phase_a.json
            # Load Phase A speeches with dates
            ep_a_path = DATASET_DIR / case_id / "ep_phase_a.json"
            if ep_a_path.exists():
                with open(ep_a_path) as f:
                    ep_a = json.load(f)
                # Build set of speeches before t_open (by position order)
                # ep_phase_a is ordered; match positional index to unified_assignments Phase A
                before_open_idx = set(
                    i for i, sp in enumerate(ep_a) if sp.get("date", "") < t_open
                )
                n_before = len(before_open_idx)
                n_total_a = len(ep_a)
                during = n_total_a - n_before
                print(f"    Phase A: {n_before} speeches before t_open={t_open}"
                      f" | {during} during consultation ({100*during/n_total_a:.1f}%)")

                # Filter Phase A unified records to the first n_before (positional)
                phase_a_all = by_phase["A"]
                phase_a_before = [phase_a_all[i] for i in before_open_idx
                                  if i < len(phase_a_all)]
                # Filter stance records similarly
                stance_a_all  = stance["A"]
                stance_a_before = [stance_a_all[i] for i in before_open_idx
                                   if i < len(stance_a_all)]

                n_a_before = len(phase_a_before)
                if n_a_before >= 5:
                    ddis_corr = bootstrap_ddi(
                        by_phase["B"], phase_a_before,
                        stance["B"],   stance_a_before,
                        d_topic_fixed, n_topics
                    )
                    lo_c, hi_c = ci95(ddis_corr)
                    mean_c = float(ddis_corr.mean())
                    res["corrected_phase_a"] = {
                        "n_before_open": n_a_before,
                        "n_during_consultation": during,
                        "ddi_mean":  round(mean_c, 4),
                        "ddi_ci95":  [round(lo_c, 4), round(hi_c, 4)],
                    }
                    print(f"    DDI(B,A_corrected) boot mean={mean_c:.4f}  95%CI=[{lo_c:.4f},{hi_c:.4f}]")

        results[comp_key] = res

    # --- ΔDDI bootstrap (shared Phase B resample) ---
    if "B_vs_A" in results and "B_vs_C" in results:
        d_t_a = comps["B_vs_A"]["d_topic"]
        d_t_c = comps["B_vs_C"]["d_topic"]
        n_a = len(by_phase["A"])
        n_c = len(by_phase["C"])
        b_arr   = np.array(by_phase["B"])
        a_arr   = np.array(by_phase["A"])
        c_arr   = np.array(by_phase["C"])
        bs_b    = np.array(stance["B"])
        bs_a    = np.array(stance["A"])
        bs_c    = np.array(stance["C"])
        n_b = len(b_arr)

        delta_ddis = np.zeros(N_BOOT)
        for i in range(N_BOOT):
            idx_b = RNG.integers(0, n_b, n_b)
            idx_a = RNG.integers(0, n_a, n_a)
            idx_c = RNG.integers(0, n_c, n_c)

            pb  = topic_dist(b_arr[idx_b].tolist(), n_topics)
            pa  = topic_dist(a_arr[idx_a].tolist(), n_topics)
            pc  = topic_dist(c_arr[idx_c].tolist(), n_topics)
            sb  = stance_dist(bs_b[idx_b].tolist())
            sa  = stance_dist(bs_a[idx_a].tolist())
            sc  = stance_dist(bs_c[idx_c].tolist())

            ddi_a = (0.40 * d_t_a + 0.35 * jsd2(pb, pa) + 0.25 * jsd2(sb, sa))
            ddi_c = (0.40 * d_t_c + 0.35 * jsd2(pb, pc) + 0.25 * jsd2(sb, sc))
            delta_ddis[i] = ddi_a - ddi_c

        lo_d, hi_d = ci95(delta_ddis)
        mean_d = float(delta_ddis.mean())
        p_null = float(np.mean(delta_ddis > 0))  # fraction of bootstrap > 0

        results["delta_ddi"] = {
            "mean":   round(mean_d, 4),
            "ci95":   [round(lo_d, 4), round(hi_d, 4)],
            "p_positive": round(p_null, 3),  # P(ΔDDI > 0): convergence probability
        }
        print(f"\n  ΔDDI boot: mean={mean_d:.4f}  95%CI=[{lo_d:.4f},{hi_d:.4f}]"
              f"  P(>0)={p_null:.3f}")
        if lo_d <= 0 <= hi_d:
            print(f"  → CI includes 0: null finding confirmed (no detectable effect)")
        else:
            sign = "positive" if mean_d > 0 else "negative"
            print(f"  → CI excludes 0: statistically {sign} ΔDDI")

    with open(out_dir / "bootstrap_results.json", "w") as f:
        json.dump(results, f, indent=2)
    return results


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    summary = {}
    for case_id in target_cases:
        r = process_case(case_id)
        if r and "delta_ddi" in r:
            summary[case_id] = {
                "delta_ddi_mean": r["delta_ddi"]["mean"],
                "delta_ddi_ci95": r["delta_ddi"]["ci95"],
                "delta_ddi_p_positive": r["delta_ddi"]["p_positive"],
                "ci_includes_zero": r["delta_ddi"]["ci95"][0] <= 0 <= r["delta_ddi"]["ci95"][1],
            }

    print("\n" + "="*60)
    print("BOOTSTRAP ΔDDI SUMMARY")
    print("="*60)
    for cid, s in summary.items():
        print(f"  {cid}:")
        print(f"    ΔDDI = {s['delta_ddi_mean']:.4f}  95%CI = {s['delta_ddi_ci95']}"
              f"  P(>0) = {s['delta_ddi_p_positive']:.3f}  CI∋0: {s['ci_includes_zero']}")

    with open(OUT_DIR / "bootstrap_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
