"""s7 — emit machine-readable metadata: Croissant v1.1 + W3C PROV-O lineage.

Produces, in pipeline/data/metadata/:
  * croissant.json     — MLCommons Croissant v1.1 (schema.org + cr:) describing the
                         published file, its fields, license, checksum, AND PROV-O
                         lineage (prov:wasDerivedFrom the upstream sources,
                         prov:wasGeneratedBy the curation pipeline).
  * provenance.json    — a full W3C PROV document (PROV-JSON) of the curation chain.
  * provenance.provn   — the same, in human-readable PROV-N.
  * qc_summary.json    — the Landrum-Riniker QC metrics, for the dataset card + API.
  * dataset_meta.json  — the catalog "nutrition label" row.

    python pipeline/s7_emit_metadata.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402

import config  # noqa: E402
import utils  # noqa: E402

log = utils.get_logger("s7.metadata")

CONSENSUS_CSV = config.PROCESSED_DIR / "consensus.csv"
SR_CSV = config.PROCESSED_DIR / "source_records.csv"
QC_CSV = config.PROCESSED_DIR / "qc_metrics.csv"
COMPOUNDS_CSV = config.PROCESSED_DIR / "compounds.csv"

CROISSANT_JSON = config.METADATA_DIR / "croissant.json"
PROV_JSON = config.METADATA_DIR / "provenance.json"
PROV_N = config.METADATA_DIR / "provenance.provn"
QC_SUMMARY_JSON = config.METADATA_DIR / "qc_summary.json"
DATASET_META_JSON = config.METADATA_DIR / "dataset_meta.json"

CROISSANT_CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileObject": "cr:fileObject",
    "fileProperty": "cr:fileProperty",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "prov": "http://www.w3.org/ns/prov#",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "sha256": "cr:sha256",
}

FIELD_DEFS = [
    ("inchikey", "sc:Text", "Standard InChIKey — the cross-source compound join key."),
    ("target_uniprot", "sc:Text", "UniProt accession of the protein target."),
    ("std_smiles", "sc:Text", "RDKit-standardized canonical SMILES (parent, neutral, canonical tautomer)."),
    ("consensus_p_activity", "sc:Float", "Median pActivity (-log10[M]) across exact measurements."),
    ("consensus_value_nm", "sc:Float", "Consensus potency in nM."),
    ("n_records_used", "sc:Integer", "Number of exact measurements feeding the consensus."),
    ("n_sources", "sc:Integer", "Number of distinct upstream sources for this compound/target."),
    ("spread_log", "sc:Float", "Max-min pActivity spread across measurements (log units)."),
    ("agreement", "sc:Text", "Agreement badge: strong / moderate / weak / single."),
]


def _qc_summary() -> dict:
    if not QC_CSV.exists():
        return {}
    qc = pd.read_csv(QC_CSV)
    out = {}
    for r in qc.to_dict("records"):
        out[r["curation_level"]] = {k: r[k] for k in
                                    ("n_pairs", "kendall_tau", "frac_gt_03", "frac_gt_10", "mae_log")}
    return out


def _build_croissant(file_name: str, sha256: str, size: int, n_records: int,
                     sources: list, qc: dict) -> dict:
    today = dt.date.today().isoformat()
    return {
        "@context": CROISSANT_CONTEXT,
        "@type": "sc:Dataset",
        "@id": f"https://huggingface.co/datasets/{config.HF_REPO_ID}",
        "conformsTo": "http://mlcommons.org/croissant/1.1",
        "name": config.DATASET_NAME,
        "description": (
            "Provenance-preserving, multi-source EGFR bioactivity catalog. "
            "Bioactivity records aggregated by ChEMBL from multiple upstream sources "
            "are standardized (RDKit), joined on standard InChIKey, harmonized to a "
            "median-consensus pActivity while EVERY original measurement is preserved "
            "and link-tracked, and suspect values are flagged (not deleted) using a "
            "ChEMBL-style DATA_VALIDITY vocabulary. Includes a Landrum-Riniker QC report."
        ),
        "version": config.DATASET_VERSION,
        "datePublished": today,
        "license": config.DATASET_LICENSE,
        "url": f"https://huggingface.co/datasets/{config.HF_REPO_ID}",
        "citeAs": (
            "Built on ChEMBL (Zdrazil et al. 2024, NAR) and the curation/QC methodology of "
            "Landrum & Riniker (2024, J. Chem. Inf. Model., DOI 10.1021/acs.jcim.4c00049)."
        ),
        "creator": {"@type": "sc:Person", "name": "Nitin Singh",
                    "url": "https://github.com/NI3singh"},
        # ---- PROV-O lineage (what makes this richer than HF's auto-Croissant) ----
        "prov:wasDerivedFrom": [
            {"@type": "prov:Entity", "@id": "https://www.ebi.ac.uk/chembl",
             "name": "ChEMBL", "description": f"Upstream sources present: {', '.join(sources)}"}
        ],
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "@id": "https://github.com/NI3singh/provbench-bioactivity-catalog#curation-pipeline",
            "name": "ProvBench curation pipeline (extract -> standardize -> harmonize -> flag -> QC)",
            "prov:endedAtTime": today,
        },
        "distribution": [{
            "@type": "cr:FileObject",
            "@id": file_name,
            "name": file_name,
            "description": "Per compound/target consensus records (CSV).",
            "contentUrl": f"https://huggingface.co/datasets/{config.HF_REPO_ID}/resolve/main/{file_name}",
            "encodingFormat": "text/csv",
            "sha256": sha256,
            "contentSize": f"{size} B",
        }],
        "recordSet": [{
            "@type": "cr:RecordSet",
            "@id": "records",
            "name": "records",
            "description": f"{n_records} consensus bioactivity records.",
            "key": {"@id": "records/inchikey"},
            "field": [
                {
                    "@type": "cr:Field",
                    "@id": f"records/{name}",
                    "name": name,
                    "description": desc,
                    "dataType": dtype,
                    "source": {"fileObject": {"@id": file_name},
                               "extract": {"column": name}},
                }
                for name, dtype, desc in FIELD_DEFS
            ],
        }],
        "cr:qualityReport": qc,
    }


def _build_croissant_mlc(file_name: str, sha256: str, size: int, n_records: int,
                         sources: list, qc: dict) -> dict:
    """Build a cleanly-validating Croissant via the mlcroissant library, then inject
    the PROV-O lineage + quality report on top (the part HF's auto-Croissant lacks)."""
    import mlcroissant as mlc

    dt_map = {"sc:Text": mlc.DataType.TEXT, "sc:Float": mlc.DataType.FLOAT,
              "sc:Integer": mlc.DataType.INTEGER}
    fields = [
        mlc.Field(
            id=f"records/{name}", name=name, description=desc,
            data_types=[dt_map.get(dtype, mlc.DataType.TEXT)],
            source=mlc.Source(file_object=file_name, extract=mlc.Extract(column=name)),
        )
        for name, dtype, desc in FIELD_DEFS
    ]
    record_set = mlc.RecordSet(
        id="records", name="records",
        description=f"{n_records} consensus bioactivity records.",
        key=["records/inchikey"], fields=fields,
    )
    file_object = mlc.FileObject(
        id=file_name, name=file_name,
        description="Per compound/target consensus records (CSV).",
        content_url=f"https://huggingface.co/datasets/{config.HF_REPO_ID}/resolve/main/{file_name}",
        content_size=f"{size} B", encoding_formats=["text/csv"], sha256=sha256,
    )
    md = mlc.Metadata(
        name=config.DATASET_NAME,
        description=(
            "Provenance-preserving, multi-source EGFR bioactivity catalog. Records that "
            "ChEMBL aggregated from multiple upstream sources are standardized (RDKit), "
            "joined on standard InChIKey, harmonized to a median-consensus pActivity while "
            "EVERY original measurement is preserved/link-tracked, and suspect values are "
            "flagged (not deleted). Includes a Landrum-Riniker QC report."
        ),
        cite_as=("Built on ChEMBL and the curation/QC methodology of Landrum & Riniker "
                 "(2024, J. Chem. Inf. Model., DOI 10.1021/acs.jcim.4c00049)."),
        conforms_to=["http://mlcommons.org/croissant/1.1"],
        date_published=dt.datetime.combine(dt.date.today(), dt.time()),
        license=[config.DATASET_LICENSE],
        url=f"https://huggingface.co/datasets/{config.HF_REPO_ID}",
        version=config.DATASET_VERSION,
        distribution=[file_object],
        record_sets=[record_set],
    )
    js = md.to_json()

    # ---- inject PROV-O lineage + quality report (the enrichment over auto-Croissant) ----
    ctx = js.get("@context")
    if isinstance(ctx, dict):
        ctx.setdefault("prov", "http://www.w3.org/ns/prov#")
    elif isinstance(ctx, list):
        for part in ctx:
            if isinstance(part, dict):
                part.setdefault("prov", "http://www.w3.org/ns/prov#")
                break
    today = dt.date.today().isoformat()
    js["prov:wasDerivedFrom"] = [{
        "@type": "prov:Entity", "@id": "https://www.ebi.ac.uk/chembl", "name": "ChEMBL",
        "description": f"Upstream sources present: {', '.join(sources)}",
    }]
    js["prov:wasGeneratedBy"] = {
        "@type": "prov:Activity",
        "@id": "https://github.com/NI3singh/provbench-bioactivity-catalog#curation-pipeline",
        "name": "ProvBench curation pipeline (extract -> standardize -> harmonize -> flag -> QC)",
        "prov:endedAtTime": today,
    }
    js["cr:qualityReport"] = qc
    return js


def _build_prov(sources: list) -> object:
    from prov.model import ProvDocument

    today = dt.date.today().isoformat()
    doc = ProvDocument()
    doc.add_namespace("pb", "https://github.com/NI3singh/provbench-bioactivity-catalog#")
    doc.add_namespace("chembl", "https://www.ebi.ac.uk/chembl/")
    doc.add_namespace("prov", "http://www.w3.org/ns/prov#")

    agent = doc.agent("pb:pipeline", {"prov:type": "prov:SoftwareAgent",
                                      "prov:label": "ProvBench curation pipeline"})
    src_entity = doc.entity("chembl:EGFR-activities",
                            {"prov:label": "ChEMBL EGFR IC50/Ki activities",
                             "pb:upstreamSources": ", ".join(sources)})

    a_std = doc.activity("pb:standardize", other_attributes={"prov:label": "RDKit standardization + InChIKey"})
    a_harm = doc.activity("pb:harmonize", other_attributes={"prov:label": "units->nM, pActivity, consensus"})
    a_flag = doc.activity("pb:flag", other_attributes={"prov:label": "ChEMBL-style validity flagging"})
    a_qc = doc.activity("pb:qc", other_attributes={"prov:label": "Landrum-Riniker QC report"})

    e_std = doc.entity("pb:standardized", {"prov:label": "Standardized source records"})
    e_cons = doc.entity("pb:consensus", {"prov:label": "Consensus dataset", "pb:version": config.DATASET_VERSION})

    for a in (a_std, a_harm, a_flag, a_qc):
        doc.wasAssociatedWith(a, agent)
    doc.used(a_std, src_entity)
    doc.wasGeneratedBy(e_std, a_std)
    doc.used(a_harm, e_std)
    doc.wasGeneratedBy(e_cons, a_harm)
    doc.used(a_flag, e_std)
    doc.used(a_qc, e_cons)
    doc.wasDerivedFrom(e_std, src_entity)
    doc.wasDerivedFrom(e_cons, e_std)
    return doc


def main() -> None:
    consensus = pd.read_csv(CONSENSUS_CSV)
    sr = pd.read_csv(SR_CSV)
    sources = sorted(sr["source"].dropna().unique().tolist())
    n_records = len(consensus)

    sha = utils.sha256_file(CONSENSUS_CSV)
    size = os.path.getsize(CONSENSUS_CSV)
    qc = _qc_summary()

    try:
        croissant = _build_croissant_mlc(CONSENSUS_CSV.name, sha, size, n_records, sources, qc)
        builder = "mlcroissant"
    except Exception as e:
        log.warning("mlcroissant builder failed (%s); using hand-authored JSON-LD", str(e)[:160])
        croissant = _build_croissant(CONSENSUS_CSV.name, sha, size, n_records, sources, qc)
        builder = "hand-authored"
    CROISSANT_JSON.write_text(json.dumps(croissant, indent=2), encoding="utf-8")
    log.info("Wrote %s (%s)", CROISSANT_JSON, builder)

    # Validate the Croissant file with mlcroissant (best-effort).
    try:
        import mlcroissant as mlc
        mlc.Dataset(jsonld=str(CROISSANT_JSON))
        log.info("Croissant validated by mlcroissant OK")
    except Exception as e:
        log.warning("mlcroissant validation note: %s", str(e)[:200])

    try:
        doc = _build_prov(sources)
        PROV_JSON.write_text(doc.serialize(format="json"), encoding="utf-8")
        try:
            PROV_N.write_text(doc.serialize(format="provn"), encoding="utf-8")
        except Exception:
            pass
        log.info("Wrote %s", PROV_JSON)
    except Exception as e:
        log.warning("PROV emission failed: %s", str(e)[:200])

    QC_SUMMARY_JSON.write_text(json.dumps(qc, indent=2), encoding="utf-8")

    meta = {
        "name": config.DATASET_NAME,
        "version": config.DATASET_VERSION,
        "created_at": dt.date.today().isoformat(),
        "target": config.TARGET,
        "n_compounds": int(pd.read_csv(COMPOUNDS_CSV).shape[0]) if COMPOUNDS_CSV.exists() else None,
        "n_consensus_records": n_records,
        "n_source_records": int(len(sr)),
        "sources": sources,
        "license": config.DATASET_LICENSE,
        "sha256_consensus": sha,
        "hf_url": f"https://huggingface.co/datasets/{config.HF_REPO_ID}",
        "croissant_url": f"https://huggingface.co/api/datasets/{config.HF_REPO_ID}/croissant",
        "qc": qc,
    }
    DATASET_META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("Wrote %s", DATASET_META_JSON)
    log.info("Sources represented: %s", sources)


if __name__ == "__main__":
    main()
