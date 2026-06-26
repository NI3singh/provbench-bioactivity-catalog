"""/api/compounds — search + the "show the receipts" detail view."""
from __future__ import annotations

from fastapi import APIRouter

import db

router = APIRouter(prefix="/api", tags=["compounds"])


@router.get("/compounds")
def list_compounds(q: str = "", target: str | None = None, page: int = 1, page_size: int = 25):
    target = target or db.DEFAULT_TARGET
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    where = "where c.target_uniprot = %s"
    params: list = [target]
    if q:
        where += " and (c.inchikey ilike %s or co.std_smiles ilike %s)"
        params += [f"%{q}%", f"%{q}%"]

    base = f"""
        from consensus c
        join compounds co on co.inchikey = c.inchikey
        {where}
    """
    items = db.query(
        f"""select c.inchikey, co.std_smiles, c.consensus_p_activity, c.consensus_value_nm,
                   c.n_records_used, c.n_sources, c.agreement, c.spread_log
            {base}
            order by c.consensus_p_activity desc nulls last
            limit %s offset %s""",
        params + [page_size, offset],
    )
    total = db.query_one(f"select count(*) as n {base}", params)["n"]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/compounds/{inchikey}")
def compound_detail(inchikey: str, target: str | None = None):
    target = target or db.DEFAULT_TARGET
    compound = db.query_one("select * from compounds where inchikey = %s", (inchikey,))
    consensus = db.query_one(
        "select * from consensus where inchikey = %s and target_uniprot = %s",
        (inchikey, target),
    )
    records = db.query(
        """select source_record_id, source, access_path, source_compound_id, standard_type,
                  standard_relation, standard_value, standard_units, value_nm, p_activity,
                  pchembl_value, is_exact, assay_id, assay_description, confidence_score,
                  bao_format, document_id, source_url, raw_validity_comment,
                  validity_flag, flag_reason
           from source_records
           where inchikey = %s and target_uniprot = %s
           order by validity_flag nulls first, p_activity desc nulls last""",
        (inchikey, target),
    )
    return {"compound": compound, "consensus": consensus, "records": records,
            "n_records": len(records)}
