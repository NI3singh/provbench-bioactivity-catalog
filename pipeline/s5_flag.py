"""s5 — flag suspect measurements (annotate-don't-delete).

Mirrors ChEMBL's DATA_VALIDITY_COMMENT controlled vocabulary. Every record is kept;
suspect ones simply get a `validity_flag` + human-readable `flag_reason`. Nothing is
deleted or silently overwritten — that is the whole point of the project.

    python pipeline/s5_flag.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s5.flag")

SR_CSV = config.PROCESSED_DIR / "source_records.csv"
CONSENSUS_CSV = config.PROCESSED_DIR / "consensus.csv"


def _flag_row(r, median_lookup) -> tuple:
    val = r["standard_value"]
    vnm = r["value_nm"]
    p = r["p_activity"]

    if pd.isna(val):
        return config.FLAG_MISSING, "standard_value is empty"
    if pd.isna(vnm):
        return config.FLAG_NONSTD_UNIT, f"units '{r['standard_units']}' not convertible to nM"
    lo_nm, hi_nm = config.VALUE_NM_RANGE
    lo_p, hi_p = config.P_ACTIVITY_RANGE
    if not (lo_nm <= vnm <= hi_nm) or (p is not None and not pd.isna(p) and not (lo_p <= p <= hi_p)):
        return config.FLAG_OUTSIDE_RANGE, f"value {vnm:.4g} nM (pActivity {p:.2f}) outside plausible range"

    # Transcription error: |Δ| vs the compound's consensus is ~3 or ~6 decades.
    med = median_lookup.get((r["inchikey"], r["target_uniprot"]))
    if med is not None and p is not None and not pd.isna(p):
        delta = abs(p - med)
        for decade in config.TRANSCRIPTION_ERROR_DECADES:
            if abs(delta - decade) <= config.TRANSCRIPTION_ERROR_TOL:
                return (config.FLAG_TRANSCRIPTION,
                        f"differs from compound consensus by ~{delta:.1f} log units (~{10**round(delta):.0f}x)")
    return config.VALIDITY_OK, None


def main() -> None:
    df = pd.read_csv(SR_CSV)
    median_lookup = {}
    if CONSENSUS_CSV.exists():
        cons = pd.read_csv(CONSENSUS_CSV)
        multi = cons[cons["n_records_used"] >= 2]
        median_lookup = {
            (row.inchikey, row.target_uniprot): row.consensus_p_activity
            for row in multi.itertuples()
        }

    flags, reasons = [], []
    for r in df.itertuples(index=False):
        f, why = _flag_row(r._asdict(), median_lookup)
        flags.append(f)
        reasons.append(why)
    df["validity_flag"] = flags
    df["flag_reason"] = reasons

    df.to_csv(SR_CSV, index=False)

    counts = df["validity_flag"].value_counts(dropna=False).to_dict()
    n_flagged = df["validity_flag"].notna().sum()
    log.info("Flagged %d / %d records (%.1f%%). Breakdown: %s",
             n_flagged, len(df), 100 * n_flagged / max(len(df), 1), counts)


if __name__ == "__main__":
    main()
