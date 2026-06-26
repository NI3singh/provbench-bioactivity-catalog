"""/api/catalog — the dataset "nutrition label"."""
from __future__ import annotations

from fastapi import APIRouter

import db

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog")
def catalog():
    meta = db.query_one("select * from dataset_meta order by id desc limit 1")
    target = db.query_one("select * from targets limit 1")
    return {"meta": meta or {}, "target": target or {}}
