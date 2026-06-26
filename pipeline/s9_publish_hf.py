"""s9 — publish the curated dataset to the HuggingFace Hub.

Uploads consensus.csv + source_records.csv + a rich dataset card + the ENRICHED
Croissant/PROV-O metadata. HuggingFace will auto-generate a (thin) Croissant from the
data files; our uploaded croissant.json is the provenance-enriched version.

Reads HF_TOKEN from .env. No-ops with a warning if the token is missing.

    python pipeline/s9_publish_hf.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s9.hf")


def _card(meta: dict, qc: dict) -> str:
    def row(level):
        d = qc.get(level, {})
        return f"| {level} | {d.get('n_pairs','-')} | {d.get('kendall_tau','-')} | {d.get('frac_gt_03','-')} | {d.get('frac_gt_10','-')} | {d.get('mae_log','-')} |"

    sources = ", ".join(meta.get("sources", []))
    return f"""---
license: cc-by-sa-3.0
language:
- en
pretty_name: ProvBench EGFR Bioactivity (provenance-preserving)
tags:
- chemistry
- drug-discovery
- bioactivity
- ic50
- egfr
- data-curation
- provenance
size_categories:
- 1K<n<10K
configs:
- config_name: consensus
  data_files: consensus.csv
- config_name: source_records
  data_files: source_records.csv
---

# ProvBench — EGFR Bioactivity (provenance-preserving, multi-source)

A curated catalog of EGFR (UniProt **{meta['target']['uniprot']}**, ChEMBL **{meta['target']['chembl_id']}**)
IC50/Ki bioactivity, built to demonstrate rigorous **data provenance**, **metadata cataloging**,
and **multi-source harmonization**.

- **{meta.get('n_source_records','?')}** original measurements preserved (link-tracked, never deleted)
- **{meta.get('n_compounds','?')}** unique compounds (standardized; joined on standard InChIKey)
- **{meta.get('n_consensus_records','?')}** compound/target consensus values
- Upstream sources (via ChEMBL): {sources}

## Philosophy: annotate-don't-delete

Every original record is kept and linked to its source. Suspect values are **flagged** with a
ChEMBL-style `validity_flag` (e.g. *Potential transcription error*, *Outside typical range*), never
silently dropped. The consensus is a transparent **median** of the exact measurements.

## Data quality (Landrum & Riniker, 2024)

Pairwise agreement of repeat measurements under different curation regimes
(higher Kendall tau / lower MAE = better):

| curation | n_pairs | Kendall tau | frac >0.3 log | frac >1.0 log | MAE (log) |
|---|---|---|---|---|---|
{row('minimal')}
{row('maximal')}
{row('cross_source')}

## Files

- `consensus.csv` — one harmonized row per (compound, target).
- `source_records.csv` — every original measurement with source, flags, and provenance.
- `croissant.json` — **enriched** Croissant v1.1 metadata with PROV-O lineage
  (HuggingFace's auto-generated Croissant is structurally thin by comparison).
- `provenance.json` — W3C PROV document of the curation chain.

## Provenance & licensing

Derived from ChEMBL (CC BY-SA 3.0) which aggregates the upstream sources listed above.
Curation/QC methodology follows Landrum & Riniker (2024), *J. Chem. Inf. Model.*,
DOI 10.1021/acs.jcim.4c00049.

Built by [Nitin Singh](https://github.com/NI3singh) — code:
https://github.com/NI3singh/provbench-bioactivity-catalog
"""


def main() -> None:
    load_dotenv(config.PROJECT_DIR / ".env")
    token = os.getenv("HF_TOKEN")
    if not token:
        log.warning("HF_TOKEN not set in .env — skipping HuggingFace publish.")
        return

    from huggingface_hub import HfApi

    meta = json.loads((config.METADATA_DIR / "dataset_meta.json").read_text(encoding="utf-8"))
    qc = meta.get("qc", {})
    card_path = config.METADATA_DIR / "README.md"
    card_path.write_text(_card(meta, qc), encoding="utf-8")

    api = HfApi(token=token)
    api.create_repo(config.HF_REPO_ID, repo_type="dataset", exist_ok=True)
    log.info("Uploading to https://huggingface.co/datasets/%s ...", config.HF_REPO_ID)

    uploads = [
        (config.PROCESSED_DIR / "consensus.csv", "consensus.csv"),
        (config.PROCESSED_DIR / "source_records.csv", "source_records.csv"),
        (config.METADATA_DIR / "croissant.json", "croissant.json"),
        (config.METADATA_DIR / "provenance.json", "provenance.json"),
        (card_path, "README.md"),
    ]
    for path, repo_path in uploads:
        if path.exists():
            api.upload_file(path_or_fileobj=str(path), path_in_repo=repo_path,
                            repo_id=config.HF_REPO_ID, repo_type="dataset")
            log.info("  uploaded %s", repo_path)
    log.info("Published: https://huggingface.co/datasets/%s", config.HF_REPO_ID)


if __name__ == "__main__":
    main()
