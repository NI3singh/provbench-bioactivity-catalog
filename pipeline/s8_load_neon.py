"""s8 — load the curated tables into Postgres (Neon / neon / any).

Runs schema.sql (drop + recreate), then bulk-loads each processed CSV with COPY
(fast and idempotent). Reads DATABASE_URL from .env.

Use a pooler / SSL connection string (Neon's default URL works as-is and supports COPY).

    python pipeline/s8_load_neon.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s8.load")

SCHEMA_SQL = config.PIPELINE_DIR / "schema.sql"

SR_COLS = ["source_record_id", "source", "access_path", "source_compound_id", "inchikey",
           "target_uniprot", "std_smiles", "original_smiles", "standard_type",
           "standard_relation", "standard_value", "standard_units", "value_nm",
           "p_activity", "pchembl_value", "is_exact", "assay_id", "assay_description",
           "confidence_score", "bao_format", "document_id", "source_url",
           "raw_validity_comment", "validity_flag", "flag_reason"]
CONS_COLS = ["inchikey", "target_uniprot", "consensus_p_activity", "consensus_value_nm",
             "n_records_used", "n_sources", "spread_log", "p_min", "p_max", "p_std", "agreement"]
COMP_COLS = ["inchikey", "std_smiles", "n_records", "n_sources"]
QC_COLS = ["curation_level", "n_pairs", "kendall_tau", "frac_gt_03", "frac_gt_10", "mae_log"]


def _load_table(cur, table, df, cols, int_cols=(), float_cols=()):
    sub = df.reindex(columns=cols).copy()
    for c in int_cols:
        sub[c] = pd.to_numeric(sub[c], errors="coerce").astype("Int64")
    for c in float_cols:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    buf = io.StringIO()
    sub.to_csv(buf, index=False, header=False)
    buf.seek(0)
    with cur.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN WITH (FORMAT csv)") as cp:
        cp.write(buf.read())
    log.info("  loaded %-15s %d rows", table, len(sub))


def main() -> None:
    load_dotenv(config.PROJECT_DIR / ".env")
    dsn = os.getenv("DATABASE_URL") or os.getenv("neon_DB_URL")
    if not dsn:
        log.error("DATABASE_URL not set in .env — aborting load.")
        sys.exit(1)

    import psycopg

    sr = pd.read_csv(config.PROCESSED_DIR / "source_records.csv")
    cons = pd.read_csv(config.PROCESSED_DIR / "consensus.csv")
    comp = pd.read_csv(config.PROCESSED_DIR / "compounds.csv")
    qc = pd.read_csv(config.PROCESSED_DIR / "qc_metrics.csv")
    meta = json.loads((config.METADATA_DIR / "dataset_meta.json").read_text(encoding="utf-8"))

    log.info("Connecting to Postgres ...")
    with psycopg.connect(dsn, prepare_threshold=None, autocommit=False) as conn:
        with conn.cursor() as cur:
            log.info("Applying schema.sql ...")
            # strip -- line comments first so a ';' inside a comment can't split a statement
            schema = re.sub(r"--[^\n]*", "", SCHEMA_SQL.read_text(encoding="utf-8"))
            for stmt in schema.split(";"):
                if stmt.strip():
                    cur.execute(stmt)

            cur.execute(
                "insert into targets (uniprot, chembl_id, pref_name, organism) values (%s,%s,%s,%s)",
                (config.TARGET["uniprot"], config.TARGET["chembl_id"],
                 config.TARGET["pref_name"], config.TARGET["organism"]),
            )

            _load_table(cur, "compounds", comp, COMP_COLS, int_cols=["n_records", "n_sources"])
            _load_table(cur, "source_records", sr, SR_COLS,
                        int_cols=["confidence_score"],
                        float_cols=["standard_value", "value_nm", "p_activity", "pchembl_value"])
            _load_table(cur, "consensus", cons, CONS_COLS,
                        int_cols=["n_records_used", "n_sources"],
                        float_cols=["consensus_p_activity", "consensus_value_nm", "spread_log",
                                    "p_min", "p_max", "p_std"])
            _load_table(cur, "qc_metrics", qc, QC_COLS, int_cols=["n_pairs"],
                        float_cols=["kendall_tau", "frac_gt_03", "frac_gt_10", "mae_log"])

            cur.execute(
                """insert into dataset_meta
                   (name, version, created_at, n_compounds, n_consensus_records,
                    n_source_records, sources, license, sha256_consensus, hf_url, croissant_url, qc)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (meta["name"], meta["version"], meta["created_at"], meta.get("n_compounds"),
                 meta.get("n_consensus_records"), meta.get("n_source_records"),
                 json.dumps(meta.get("sources")), meta.get("license"),
                 meta.get("sha256_consensus"), meta.get("hf_url"), meta.get("croissant_url"),
                 json.dumps(meta.get("qc"))),
            )
        conn.commit()
    log.info("Postgres load complete.")


if __name__ == "__main__":
    main()
