"""s2 — extract EGFR binding data from BindingDB by UniProt (graceful fallback).

BindingDB's REST JSON shapes vary, so the affinity list is dug out defensively. If
the call fails or returns nothing, we log it and write an empty file — the pipeline
then continues ChEMBL-only and the QC report notes the single-source situation.

    python pipeline/s2_extract_bindingdb.py [--force]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s2.bindingdb")
RAW_CSV = config.RAW_DIR / "bindingdb_egfr.csv"

COLUMNS = ["source_record_id", "canonical_smiles", "standard_type", "standard_relation",
           "standard_value", "standard_units", "source", "target_uniprot"]


def _extract_affinities(payload) -> list:
    """Dig the affinities list out of BindingDB's (XML-derived) JSON, defensively."""
    node = payload
    if isinstance(node, dict):
        for key in ("getLigandsByUniprotResponse", "getLigandsByUniprotsResponse"):
            if key in node:
                node = node[key]
                break
    aff = None
    if isinstance(node, dict):
        aff = node.get("affinities") or node.get("affinity")
    if aff is None and isinstance(payload, dict):
        for v in payload.values():  # last resort: find a nested affinities list
            if isinstance(v, dict) and isinstance(v.get("affinities"), list):
                aff = v["affinities"]
                break
    if isinstance(aff, dict):
        aff = [aff]
    return aff or []


def _norm(rec: dict):
    def g(*keys):
        for k in keys:
            if k in rec and rec[k] not in (None, ""):
                return rec[k]
        return None

    smiles = g("smile", "smiles", "SMILES", "@smile")
    atype = g("affinity_type", "@affinity_type", "type")
    aval = g("affinity", "@affinity", "value")
    mid = g("monomerid", "@monomerid", "reactant_set_id", "bdbm")
    if smiles is None or aval is None:
        return None
    # BindingDB affinities may carry a leading relation, e.g. ">10000".
    aval = str(aval).strip()
    relation = ""
    while aval and aval[0] in "<>=~":
        relation += aval[0]
        aval = aval[1:].strip()
    return {
        "source_record_id": str(mid) if mid is not None else None,
        "canonical_smiles": smiles,
        "standard_type": (atype or "IC50"),
        "standard_relation": relation or "=",
        "standard_value": aval,
        "standard_units": "nM",   # BindingDB affinities are reported in nM
        "source": "bindingdb",
        "target_uniprot": config.TARGET["uniprot"],
    }


def _fetch(params):
    """Use certifi's CA bundle (fixes the common Windows 'unable to get local issuer
    certificate' error). If TLS still fails, the caller degrades to ChEMBL-only."""
    import certifi
    return requests.get(config.BINDINGDB_REST, params=params, timeout=180, verify=certifi.where())


def main(force: bool = False) -> pd.DataFrame:
    if RAW_CSV.exists() and not force:
        df = pd.read_csv(RAW_CSV)
        log.info("Cache hit: %s (%d rows)", RAW_CSV.name, len(df))
        return df

    params = {
        "uniprot": config.TARGET["uniprot"],
        "cutoff": config.BINDINGDB_AFFINITY_CUTOFF_NM,
        "response": "application/json",
    }
    df = pd.DataFrame(columns=COLUMNS)
    try:
        log.info("GET %s uniprot=%s ...", config.BINDINGDB_REST, config.TARGET["uniprot"])
        r = _fetch(params)
        r.raise_for_status()
        try:
            payload = r.json()
        except (json.JSONDecodeError, ValueError):
            payload = json.loads(r.text)
        recs = [x for x in (_norm(a) for a in _extract_affinities(payload)) if x]
        if recs:
            df = pd.DataFrame(recs, columns=COLUMNS)
        log.info("BindingDB returned %d usable records", len(df))
    except Exception as e:  # graceful degrade -- continue ChEMBL-only
        log.warning("BindingDB fetch failed (%s) -- continuing ChEMBL-only", e)

    df.to_csv(RAW_CSV, index=False)
    log.info("Wrote %s (%d rows)", RAW_CSV, len(df))
    return df


if __name__ == "__main__":
    main(force="--force" in sys.argv)
