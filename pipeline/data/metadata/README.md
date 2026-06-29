---
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

A curated catalog of EGFR (UniProt **P00533**, ChEMBL **CHEMBL203**)
IC50/Ki bioactivity, built to demonstrate rigorous **data provenance**, **metadata cataloging**,
and **multi-source harmonization**.

- **28689** original measurements preserved (link-tracked, never deleted)
- **15507** unique compounds (standardized; joined on standard InChIKey)
- **11107** compound/target consensus values
- Upstream sources (via ChEMBL): BindingDB Patent Bioactivity Data, Chemical Probe data from Scientific Literature, DrugMatrix, EUbOPEN Chemogenomic Library Literature Data, PubChem BioAssays, SGC Frankfurt - Donated Chemical Probes, Scientific Literature, SureChEMBL Patent Bioactivity Data

## Philosophy: annotate-don't-delete

Every original record is kept and linked to its source. Suspect values are **flagged** with a
ChEMBL-style `validity_flag` (e.g. *Potential transcription error*, *Outside typical range*), never
silently dropped. The consensus is a transparent **median** of the exact measurements.

## Data quality (Landrum & Riniker, 2024)

Pairwise agreement of repeat measurements under different curation regimes
(higher Kendall tau / lower MAE = better):

| curation | n_pairs | Kendall tau | frac >0.3 log | frac >1.0 log | MAE (log) |
|---|---|---|---|---|---|
| minimal | 20398 | 0.3716 | 0.6844 | 0.3745 | 0.9483 |
| maximal | 13255 | 0.401 | 0.6611 | 0.3442 | 0.883 |
| cross_source | 1993 | 0.2854 | 0.7341 | 0.4305 | 1.0506 |

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
