"""s6 — quantify the multi-source noise and that curation reduces it.

Reproduces the headline analysis of Landrum & Riniker (2024, JCIM, DOI
10.1021/acs.jcim.4c00049): for compounds measured more than once on the same target,
compare the paired pActivity values under different curation regimes.

  * minimal      — every pair of measurements (no metadata matching)
  * maximal      — only pairs where both assays are high-confidence (>=8), same
                   bao_format and same standard_type (assay-metadata matching)
  * cross_source — only pairs whose two measurements come from different upstream
                   sources (the "combining sources is noisy" effect, directly)

Metrics per regime: Kendall's tau, fraction of pairs differing by >0.3 and >1.0 log
units, and MAE (log units). Expectation: maximal curation -> higher tau, lower MAE.

    python pipeline/s6_qc_report.py
"""
from __future__ import annotations

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import kendalltau  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s6.qc")

SR_CSV = config.PROCESSED_DIR / "source_records.csv"
QC_CSV = config.PROCESSED_DIR / "qc_metrics.csv"
PAIRS_CAP = 300  # max pairs per compound, to bound combinatorial blow-up


def _capped_pairs(n: int):
    combos = list(itertools.combinations(range(n), 2))
    if len(combos) > PAIRS_CAP:
        step = len(combos) / PAIRS_CAP
        combos = [combos[int(i * step)] for i in range(PAIRS_CAP)]
    return combos


def _metrics(a: list, b: list, regime: str) -> dict:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    if n < 5:
        return {"curation_level": regime, "n_pairs": n, "kendall_tau": None,
                "frac_gt_03": None, "frac_gt_10": None, "mae_log": None}
    d = np.abs(a - b)
    tau, _ = kendalltau(a, b)
    return {
        "curation_level": regime,
        "n_pairs": int(n),
        "kendall_tau": round(float(tau), 4) if tau == tau else None,
        "frac_gt_03": round(float((d > 0.3).mean()), 4),
        "frac_gt_10": round(float((d > 1.0).mean()), 4),
        "mae_log": round(float(d.mean()), 4),
    }


def main() -> pd.DataFrame:
    df = pd.read_csv(SR_CSV)
    df = df[df["is_exact"] & df["p_activity"].notna()].copy()
    log.info("Usable exact measurements: %d", len(df))

    buckets = {"minimal": ([], []), "maximal": ([], []), "cross_source": ([], [])}

    for (_ik, _tgt), g in df.groupby(["inchikey", "target_uniprot"]):
        if len(g) < 2:
            continue
        recs = g[["p_activity", "confidence_score", "bao_format", "standard_type", "source"]].to_dict("records")
        for i, j in _capped_pairs(len(recs)):
            ri, rj = recs[i], recs[j]
            pi, pj = ri["p_activity"], rj["p_activity"]
            buckets["minimal"][0].append(pi); buckets["minimal"][1].append(pj)

            ci, cj = ri.get("confidence_score"), rj.get("confidence_score")
            same_bao = (ri.get("bao_format") == rj.get("bao_format")) and pd.notna(ri.get("bao_format"))
            same_type = ri.get("standard_type") == rj.get("standard_type")
            hi_conf = (pd.notna(ci) and pd.notna(cj)
                       and ci >= config.CONFIDENCE_MIN_MAXIMAL and cj >= config.CONFIDENCE_MIN_MAXIMAL)
            if hi_conf and same_bao and same_type:
                buckets["maximal"][0].append(pi); buckets["maximal"][1].append(pj)

            if ri.get("source") != rj.get("source"):
                buckets["cross_source"][0].append(pi); buckets["cross_source"][1].append(pj)

    rows = [_metrics(a, b, regime) for regime, (a, b) in buckets.items()]
    qc = pd.DataFrame(rows)
    qc.to_csv(QC_CSV, index=False)
    log.info("Wrote %s", QC_CSV)
    for r in rows:
        log.info("  %-12s n=%-7s tau=%s  >0.3=%s  >1.0=%s  MAE=%s",
                 r["curation_level"], r["n_pairs"], r["kendall_tau"],
                 r["frac_gt_03"], r["frac_gt_10"], r["mae_log"])

    mn = next((r for r in rows if r["curation_level"] == "minimal"), None)
    mx = next((r for r in rows if r["curation_level"] == "maximal"), None)
    if mn and mx and mn["kendall_tau"] and mx["kendall_tau"]:
        better = mx["kendall_tau"] > mn["kendall_tau"] and (mx["mae_log"] or 9) < (mn["mae_log"] or 0)
        log.info("Maximal curation improves agreement: %s (tau %.3f->%.3f, MAE %.3f->%.3f)",
                 better, mn["kendall_tau"], mx["kendall_tau"], mn["mae_log"], mx["mae_log"])
    return qc


if __name__ == "__main__":
    main()
