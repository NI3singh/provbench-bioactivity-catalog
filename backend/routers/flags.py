"""/api/flags — the annotate-don't-delete view of every caught record."""
from __future__ import annotations

from fastapi import APIRouter

import db

router = APIRouter(prefix="/api", tags=["flags"])


@router.get("/flags")
def list_flags(type: str = "", page: int = 1, page_size: int = 50):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    offset = (page - 1) * page_size

    where = "where validity_flag is not null"
    params: list = []
    if type:
        where += " and validity_flag = %s"
        params.append(type)

    items = db.query(
        f"""select source_record_id, source, inchikey, std_smiles, standard_type,
                   standard_value, standard_units, value_nm, p_activity,
                   validity_flag, flag_reason, source_url
            from source_records
            {where}
            order by validity_flag, source
            limit %s offset %s""",
        params + [page_size, offset],
    )
    total = db.query_one(f"select count(*) as n from source_records {where}", params)["n"]
    breakdown = db.query(
        """select validity_flag, count(*) as n
           from source_records where validity_flag is not null
           group by validity_flag order by n desc"""
    )
    return {"items": items, "total": total, "breakdown": breakdown,
            "page": page, "page_size": page_size}
