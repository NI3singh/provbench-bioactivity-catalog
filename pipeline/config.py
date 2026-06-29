"""Central configuration for the ProvBench pipeline.

One place for the target, thresholds, source endpoints and dataset identity so that
every stage (s1..s9) shares the same definitions and nothing is hard-coded twice.
"""
import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PIPELINE_DIR.parent
DATA_DIR = PIPELINE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
for _d in (RAW_DIR, PROCESSED_DIR, METADATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Target ───────────────────────────────────────────────────────────────
# EGFR — Epidermal growth factor receptor (erbB1). A data-rich, well-studied
# kinase with thousands of IC50/Ki measurements across many chemical series.
TARGET = {
    "chembl_id": "CHEMBL203",
    "uniprot": "P00533",
    "pref_name": "Epidermal growth factor receptor erbB1",
    "organism": "Homo sapiens",
}

# Activity types to collect.
STANDARD_TYPES = ["IC50", "Ki"]

# Full tautomer canonicalization is slow (hundreds of tautomers/molecule) and its
# value is debated; the standard InChIKey after desalt+neutralize is already a strong
# join key. Off by default; flip to True for stricter (slow) tautomer harmonization.
STANDARDIZE_TAUTOMER = False

# Optional hard cap on rows pulled per source (None = no cap). Safety valve only.
MAX_RECORDS = None

# ── Source endpoints (recorded verbatim in provenance) ───────────────────
CHEMBL_NOTE = "ChEMBL web services (https://www.ebi.ac.uk/chembl)"
CHEMBL_ACTIVITY_URL = "https://www.ebi.ac.uk/chembl/api/data/activity"
CHEMBL_COMPOUND_CARD = "https://www.ebi.ac.uk/chembl/compound_report_card/{}/"   # molecule_chembl_id
CHEMBL_ASSAY_CARD = "https://www.ebi.ac.uk/chembl/assay_report_card/{}/"          # assay_chembl_id
CHEMBL_DOC_CARD = "https://www.ebi.ac.uk/chembl/document_report_card/{}/"         # document_chembl_id
BINDINGDB_REST = "https://www.bindingdb.org/rest/getLigandsByUniprot"
BINDINGDB_AFFINITY_CUTOFF_NM = 1_000_000  # generous upper bound to bound payload size

# ── Curation thresholds ──────────────────────────────────────────────────
# "Maximal curation" (Landrum & Riniker 2024): match assays on metadata before
# combining values. confidence_score >= 8 == directly assigned single protein.
CONFIDENCE_MIN_MAXIMAL = 8
# Plausible ranges used for flagging (annotate-don't-delete; nothing is deleted).
P_ACTIVITY_RANGE = (1.0, 12.0)    # ~1 mM .. 1 pM in pActivity units
VALUE_NM_RANGE = (1e-3, 1e9)      # 0.001 nM .. 1e9 nM
# Transcription-error heuristic: a value whose |Δlog10| vs the compound median is
# within TOL of one of these decade magnitudes is flagged (e.g. a 1000x unit slip).
TRANSCRIPTION_ERROR_DECADES = (3, 6)
TRANSCRIPTION_ERROR_TOL = 0.35
# Agreement badge from the spread (max-min) of p_activity for a compound/target.
AGREEMENT_STRONG = 0.5    # < 0.5 log units
AGREEMENT_MODERATE = 1.0  # < 1.0 log units, else "weak"

# ── Unit conversion to nM ────────────────────────────────────────────────
UNIT_TO_NM = {
    "nM": 1.0, "nmol/L": 1.0, "nmol.L-1": 1.0,
    "uM": 1e3, "µM": 1e3, "μM": 1e3, "um": 1e3, "umol/L": 1e3,
    "mM": 1e6, "mmol/L": 1e6,
    "M": 1e9, "mol/L": 1e9,
    "pM": 1e-3, "pmol/L": 1e-3,
    "fM": 1e-6,
}

# ── Dataset identity ─────────────────────────────────────────────────────
DATASET_NAME = "provbench-egfr-bioactivity"
DATASET_VERSION = "1.0.0"
# ChEMBL data is CC BY-SA 3.0; BindingDB is CC BY 3.0 — the combined derivative
# inherits the more restrictive share-alike. Both sources attributed in the card.
DATASET_LICENSE = "CC-BY-SA-3.0"
# HuggingFace namespace is the HF username (Ni3SinghR), which differs from the GitHub
# username (NI3singh). Override with the HF_REPO_ID env var if needed.
HF_REPO_ID = os.getenv("HF_REPO_ID", "Ni3SinghR/provbench-egfr-bioactivity")

# ── ChEMBL DATA_VALIDITY_COMMENT controlled vocabulary (mirrored) ────────
VALIDITY_OK = None
FLAG_MISSING = "Potential missing data"
FLAG_NONSTD_UNIT = "Non standard unit for type"
FLAG_OUTSIDE_RANGE = "Outside typical range"
FLAG_TRANSCRIPTION = "Potential transcription error"
