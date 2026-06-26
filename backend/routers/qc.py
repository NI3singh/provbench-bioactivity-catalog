"""/api/qc — Landrum-Riniker before/after metrics + dashboard breakdowns."""
from __future__ import annotations

from fastapi import APIRouter

import db

router = APIRouter(prefix="/api", tags=["qc"])


@router.get("/qc")
def qc():
    metrics = db.query(
        """select curation_level, n_pairs, kendall_tau, frac_gt_03, frac_gt_10, mae_log
           from qc_metrics
           order by case curation_level
                      when 'minimal' then 1 when 'maximal' then 2 else 3 end"""
    )
    by_source = db.query(
        "select source, count(*) as n from source_records group by source order by n desc"
    )
    by_agreement = db.query(
        "select agreement, count(*) as n from consensus group by agreement order by n desc"
    )
    by_flag = db.query(
        """select coalesce(validity_flag, 'OK (not flagged)') as flag, count(*) as n
           from source_records group by validity_flag order by n desc"""
    )
    return {"metrics": metrics, "by_source": by_source,
            "by_agreement": by_agreement, "by_flag": by_flag}
