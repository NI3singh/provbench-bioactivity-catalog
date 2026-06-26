"""s3 — normalise both sources into one schema and standardise structures (RDKit).

Reads the cached raw pulls, maps ChEMBL and BindingDB onto a common "source record"
schema, then runs each unique SMILES through an explicit RDKit standardisation
pipeline (salt strip -> neutralise -> canonical tautomer) and computes the standard
InChIKey used as the cross-source compound join key. Every standardisation step that
actually changes the molecule is recorded per-compound for provenance.

    python pipeline/s3_standardize.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402
from tqdm import tqdm  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s3.standardize")

OUT_CSV = config.PROCESSED_DIR / "standardized.csv"

UNIFIED_COLS = [
    "source", "access_path", "source_record_id", "source_compound_id", "original_smiles",
    "standard_type", "standard_relation", "standard_value", "standard_units",
    "pchembl_value", "assay_id", "assay_description", "confidence_score",
    "bao_format", "document_id", "raw_validity_comment", "target_uniprot", "source_url",
]


def _norm_chembl(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=UNIFIED_COLS)
    out = pd.DataFrame()
    mid = df["molecule_chembl_id"].astype("string")
    aid = df.get("assay_chembl_id", pd.Series(index=df.index, dtype="string")).astype("string")
    # The "source" is the genuine upstream database the record came from (via ChEMBL).
    out["source"] = df.get("src_name", pd.Series("ChEMBL", index=df.index)).fillna("ChEMBL")
    out["access_path"] = "ChEMBL API"
    out["source_record_id"] = mid.fillna("NA") + ":" + aid.fillna("NA") + ":" + df.index.astype(str)
    out["source_compound_id"] = mid
    out["original_smiles"] = df["canonical_smiles"]
    out["standard_type"] = df["standard_type"]
    out["standard_relation"] = df.get("standard_relation", "=")
    out["standard_value"] = df["standard_value"]
    out["standard_units"] = df["standard_units"]
    out["pchembl_value"] = df.get("pchembl_value")
    out["assay_id"] = aid
    out["assay_description"] = df.get("assay_description")
    out["confidence_score"] = df.get("confidence_score")
    out["bao_format"] = df.get("bao_format")
    out["document_id"] = df.get("document_chembl_id")
    out["raw_validity_comment"] = df.get("data_validity_comment")
    out["target_uniprot"] = df.get("target_uniprot", config.TARGET["uniprot"])
    out["source_url"] = mid.map(lambda x: config.CHEMBL_COMPOUND_CARD.format(x) if pd.notna(x) else None)
    return out


def _norm_bindingdb(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=UNIFIED_COLS)
    out = pd.DataFrame()
    sid = df["source_record_id"].astype("string")
    out["source"] = "BindingDB"
    out["access_path"] = "BindingDB REST"
    out["source_record_id"] = "BDB:" + sid.fillna("NA") + ":" + df.index.astype(str)
    out["source_compound_id"] = sid
    out["original_smiles"] = df["canonical_smiles"]
    out["standard_type"] = df["standard_type"]
    out["standard_relation"] = df.get("standard_relation", "=")
    out["standard_value"] = df["standard_value"]
    out["standard_units"] = df["standard_units"]
    out["pchembl_value"] = pd.NA
    out["assay_id"] = pd.NA
    out["assay_description"] = "BindingDB binding measurement"
    out["confidence_score"] = pd.NA
    out["bao_format"] = pd.NA
    out["document_id"] = pd.NA
    out["raw_validity_comment"] = pd.NA
    out["target_uniprot"] = df.get("target_uniprot", config.TARGET["uniprot"])
    out["source_url"] = sid.map(
        lambda x: f"https://www.bindingdb.org/rwd/bind/chemsearch/marvin/MolStructure.jsp?monomerid={x}"
        if pd.notna(x) else None
    )
    return out[UNIFIED_COLS]


def _build_standardizers():
    from rdkit.Chem.MolStandardize import rdMolStandardize
    return {
        "largest_fragment": rdMolStandardize.LargestFragmentChooser(),
        "uncharger": rdMolStandardize.Uncharger(),
        "tautomer": rdMolStandardize.TautomerEnumerator(),
    }


def standardize_smiles(smiles, tools) -> dict:
    """Return {inchikey, std_smiles, steps} or {error} for one SMILES string."""
    from rdkit import Chem

    if smiles is None or (isinstance(smiles, float)) or str(smiles).strip() == "":
        return {"error": "empty_smiles"}
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {"error": "unparseable_smiles"}

    steps = []
    before = Chem.MolToSmiles(mol)

    cleaned = rd_cleanup(mol)
    if Chem.MolToSmiles(cleaned) != before:
        steps.append("cleanup")

    frag = tools["largest_fragment"].choose(cleaned)
    if Chem.MolToSmiles(frag) != Chem.MolToSmiles(cleaned):
        steps.append("salt_solvate_stripped")

    neutral = tools["uncharger"].uncharge(frag)
    if Chem.MolToSmiles(neutral) != Chem.MolToSmiles(frag):
        steps.append("neutralized")

    canon = neutral
    if config.STANDARDIZE_TAUTOMER and "tautomer" in tools:
        try:
            canon = tools["tautomer"].Canonicalize(neutral)
            if Chem.MolToSmiles(canon) != Chem.MolToSmiles(neutral):
                steps.append("tautomer_canonicalized")
        except Exception:
            canon = neutral  # tautomer enumeration can be slow/odd on exotic structures

    inchikey = Chem.MolToInchiKey(canon)
    if not inchikey:
        return {"error": "no_inchikey"}
    return {"inchikey": inchikey, "std_smiles": Chem.MolToSmiles(canon), "steps": ";".join(steps)}


def rd_cleanup(mol):
    from rdkit.Chem.MolStandardize import rdMolStandardize
    return rdMolStandardize.Cleanup(mol)


def main() -> pd.DataFrame:
    chembl_raw = config.RAW_DIR / "chembl_egfr.csv"
    bdb_raw = config.RAW_DIR / "bindingdb_egfr.csv"
    chembl = pd.read_csv(chembl_raw) if chembl_raw.exists() else pd.DataFrame()
    bdb = pd.read_csv(bdb_raw) if bdb_raw.exists() else pd.DataFrame()
    log.info("Loaded raw: chembl=%d, bindingdb=%d", len(chembl), len(bdb))

    unified = pd.concat([_norm_chembl(chembl), _norm_bindingdb(bdb)], ignore_index=True)
    log.info("Unified source records: %d", len(unified))

    tools = _build_standardizers()
    cache: dict = {}
    results = []
    for smi in tqdm(unified["original_smiles"].tolist(), desc="standardize"):
        if smi not in cache:
            cache[smi] = standardize_smiles(smi, tools)
        results.append(cache[smi])

    res = pd.DataFrame(results, index=unified.index)
    unified["inchikey"] = res.get("inchikey")
    unified["std_smiles"] = res.get("std_smiles")
    unified["std_steps"] = res.get("steps")
    unified["std_error"] = res.get("error")

    n_bad = unified["inchikey"].isna().sum()
    dropped = unified[unified["inchikey"].isna()]
    if n_bad:
        log.warning("Dropping %d records with unparseable/empty structures (logged).", n_bad)
        dropped.to_csv(config.PROCESSED_DIR / "dropped_structures.csv", index=False)
    kept = unified[unified["inchikey"].notna()].copy()

    kept.to_csv(OUT_CSV, index=False)
    log.info("Wrote %s (%d records, %d unique compounds, %d unique SMILES standardized)",
             OUT_CSV, len(kept), kept["inchikey"].nunique(), len(cache))
    n_changed = (kept["std_steps"].fillna("") != "").sum()
    log.info("Structures altered by standardization: %d (%.1f%%)",
             n_changed, 100 * n_changed / max(len(kept), 1))
    return kept


if __name__ == "__main__":
    main()
