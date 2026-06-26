"""s1 — Extract EGFR bioactivity from ChEMBL (cached to data/raw/chembl_egfr.csv).

Uses the ChEMBL REST API directly with 1000-row pages (the python client paginates
at 20/req, which is ~70x slower for a target this size). Pulls every IC50/Ki
activity, then attaches the assay-level confidence_score (which lives on the assay
resource, not the activity) so s6 can do Landrum-Riniker "maximal curation". The raw
pull is cached so re-runs never hit the API again; pass --force to refetch.

    python pipeline/s1_extract_chembl.py [--force]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402
import requests  # noqa: E402
from tqdm import tqdm  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s1.chembl")

BASE = "https://www.ebi.ac.uk/chembl/api/data"
PAGE = 1000

ACTIVITY_FIELDS = [
    "molecule_chembl_id", "canonical_smiles", "standard_type", "standard_relation",
    "standard_value", "standard_units", "pchembl_value", "assay_chembl_id",
    "assay_description", "target_chembl_id", "document_chembl_id",
    "bao_format", "data_validity_comment", "src_id",
]

RAW_CSV = config.RAW_DIR / "chembl_egfr.csv"


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{BASE}/{path}.json", params={**params, "format": "json"}, timeout=120)
    r.raise_for_status()
    return r.json()


def verify_target_uniprot() -> list:
    data = _get(f"target/{config.TARGET['chembl_id']}", {})
    accessions = [c.get("accession") for c in data.get("target_components", [])]
    log.info("Target %s -> UniProt %s (expected %s)",
             config.TARGET["chembl_id"], accessions, config.TARGET["uniprot"])
    return accessions


def fetch_activities() -> pd.DataFrame:
    out: list = []
    offset = 0
    only = ",".join(ACTIVITY_FIELDS)
    log.info("Querying ChEMBL activities for %s (%s) ...",
             config.TARGET["chembl_id"], "/".join(config.STANDARD_TYPES))
    bar = None
    while True:
        data = _get("activity", {
            "target_chembl_id": config.TARGET["chembl_id"],
            "standard_type__in": ",".join(config.STANDARD_TYPES),
            "only": only,
            "limit": PAGE,
            "offset": offset,
        })
        acts = data.get("activities", [])
        out.extend(acts)
        total = data.get("page_meta", {}).get("total_count")
        if bar is None and total:
            bar = tqdm(total=total, desc="chembl activities")
        if bar:
            bar.update(len(acts))
        if not acts or (total is not None and len(out) >= total):
            break
        if config.MAX_RECORDS and len(out) >= config.MAX_RECORDS:
            break
        offset += PAGE
    if bar:
        bar.close()
    df = pd.DataFrame(out)
    log.info("Pulled %d activity rows", len(df))
    return df


def attach_confidence(df: pd.DataFrame) -> pd.DataFrame:
    """confidence_score / assay_type live on the assay — fetch in batches and merge."""
    ids = sorted({a for a in df["assay_chembl_id"].dropna().unique()})
    log.info("Fetching assay metadata for %d unique assays ...", len(ids))
    recs: list = []
    batch = 50  # keep the __in URL comfortably short
    for i in tqdm(range(0, len(ids), batch), desc="chembl assays"):
        chunk = ids[i:i + batch]
        data = _get("assay", {
            "assay_chembl_id__in": ",".join(chunk),
            "only": "assay_chembl_id,confidence_score,assay_type",
            "limit": PAGE,
        })
        recs.extend(data.get("assays", []))
    meta = pd.DataFrame(recs)
    if not meta.empty:
        meta = meta.drop_duplicates("assay_chembl_id")
        df = df.merge(meta, on="assay_chembl_id", how="left")
    else:
        df["confidence_score"] = pd.NA
        df["assay_type"] = pd.NA
    return df


def fetch_sources() -> dict:
    """Map ChEMBL src_id -> human-readable upstream source (Scientific Literature,
    PubChem BioAssays, BindingDB, DrugMatrix, ...). This is what makes the dataset
    genuinely multi-source: ChEMBL aggregates records from 60+ upstream databases."""
    data = _get("source", {"limit": 1000})
    return {s["src_id"]: s.get("src_description") for s in data.get("sources", [])}


def main(force: bool = False) -> pd.DataFrame:
    if RAW_CSV.exists() and not force:
        df = pd.read_csv(RAW_CSV)
        log.info("Cache hit: %s (%d rows) -- pass --force to refetch", RAW_CSV.name, len(df))
        return df

    verify_target_uniprot()
    df = fetch_activities()
    if df.empty:
        log.warning("No ChEMBL activities returned -- check target/types.")
    else:
        df = attach_confidence(df)
        src_map = fetch_sources()
        df["src_name"] = df["src_id"].map(src_map).fillna("Unknown source")
        log.info("Upstream sources present: %s",
                 df["src_name"].value_counts().to_dict())
    df["source"] = "chembl"
    df["target_uniprot"] = config.TARGET["uniprot"]
    df.to_csv(RAW_CSV, index=False)
    log.info("Wrote %s (%d rows, %d cols)", RAW_CSV, len(df), df.shape[1])
    return df


if __name__ == "__main__":
    main(force="--force" in sys.argv)
