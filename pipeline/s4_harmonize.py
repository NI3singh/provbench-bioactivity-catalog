"""s4 — harmonise units and build the consensus (link-preserving).

Converts every measurement to nM and to pActivity (= -log10[M]), writes the final
per-measurement table (source_records.csv) keeping ALL originals, then computes a
consensus value per (compound, target) from the exact ('=') measurements only —
median pActivity, with a spread-based agreement badge. Censored ('>', '<') values
are kept as records but excluded from the consensus.

    python pipeline/s4_harmonize.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s4.harmonize")

IN_CSV = config.PROCESSED_DIR / "standardized.csv"
SR_CSV = config.PROCESSED_DIR / "source_records.csv"
CONSENSUS_CSV = config.PROCESSED_DIR / "consensus.csv"
COMPOUNDS_CSV = config.PROCESSED_DIR / "compounds.csv"


def _is_exact(rel) -> bool:
    return (rel is None) or (pd.isna(rel)) or (str(rel).strip() in ("=", ""))


def main() -> None:
    df = pd.read_csv(IN_CSV)
    log.info("Loaded %d standardized records", len(df))

    # Units -> nM -> pActivity
    df["value_nm"] = [
        utils.value_to_nm(v, u, config.UNIT_TO_NM)
        for v, u in zip(df["standard_value"], df["standard_units"])
    ]
    df["p_activity"] = [utils.to_p_activity(x) for x in df["value_nm"]]
    df["is_exact"] = df["standard_relation"].map(_is_exact)

    n_unconv = df["value_nm"].isna().sum()
    log.info("Records with non-convertible units/values: %d", n_unconv)

    # Final per-measurement table — keep everything, link-preserving.
    df.to_csv(SR_CSV, index=False)
    log.info("Wrote %s (%d records)", SR_CSV, len(df))

    # Consensus from exact, numeric measurements only.
    usable = df[df["is_exact"] & df["p_activity"].notna()].copy()
    grp = usable.groupby(["inchikey", "target_uniprot"])
    rows = []
    for (ik, tgt), g in grp:
        p = g["p_activity"].to_numpy(dtype=float)
        spread = float(p.max() - p.min()) if len(p) >= 2 else None
        rows.append({
            "inchikey": ik,
            "target_uniprot": tgt,
            "consensus_p_activity": float(np.median(p)),
            "consensus_value_nm": float(10 ** (9 - np.median(p))),
            "n_records_used": int(len(g)),
            "n_sources": int(g["source"].nunique()),
            "spread_log": spread,
            "p_min": float(p.min()),
            "p_max": float(p.max()),
            "p_std": float(np.std(p, ddof=0)),
            "agreement": utils.agreement_label(spread, config.AGREEMENT_STRONG, config.AGREEMENT_MODERATE),
        })
    consensus = pd.DataFrame(rows)
    consensus.to_csv(CONSENSUS_CSV, index=False)
    log.info("Wrote %s (%d compound/target consensus rows)", CONSENSUS_CSV, len(consensus))

    # Compounds table (one row per unique structure).
    tot = df.groupby("inchikey").agg(
        std_smiles=("std_smiles", "first"),
        n_records=("source_record_id", "count"),
        n_sources=("source", "nunique"),
    ).reset_index()
    tot.to_csv(COMPOUNDS_CSV, index=False)
    log.info("Wrote %s (%d unique compounds)", COMPOUNDS_CSV, len(tot))

    # Quick console summary
    if not consensus.empty:
        multi = consensus[consensus["n_records_used"] >= 2]
        log.info("Compounds with >=2 exact measurements: %d", len(multi))
        log.info("Agreement: strong=%d moderate=%d weak=%d",
                 (consensus["agreement"] == "strong").sum(),
                 (consensus["agreement"] == "moderate").sum(),
                 (consensus["agreement"] == "weak").sum())


if __name__ == "__main__":
    main()
