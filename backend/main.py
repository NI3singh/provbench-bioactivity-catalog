"""ProvBench API — thin, read-only FastAPI over the curated Postgres (Neon) tables,
plus one guarded LLM extraction endpoint. No RDKit here (it ran offline)."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db
from routers import catalog, compounds, extract, flags, qc


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db.pool.open(wait=False)
    except Exception as e:  # don't crash startup if the DB is briefly unreachable
        print("DB pool open warning:", e)
    yield
    try:
        db.pool.close()
    except Exception:
        pass


app = FastAPI(title="ProvBench API",
              description="Provenance-preserving multi-source bioactivity catalog.",
              version="1.0.0", lifespan=lifespan)

_frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend, "http://localhost:5173", "http://localhost:3000",
                   "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.onrender\.com",  # any Render static-site host
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compounds.router)
app.include_router(flags.router)
app.include_router(qc.router)
app.include_router(catalog.router)
app.include_router(extract.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def stats():
    def n(sql):
        row = db.query_one(sql)
        return row["n"] if row else 0
    return {
        "compounds": n("select count(*) as n from compounds"),
        "source_records": n("select count(*) as n from source_records"),
        "consensus": n("select count(*) as n from consensus"),
        "flagged": n("select count(*) as n from source_records where validity_flag is not null"),
        "sources": db.query(
            "select source, count(*) as n from source_records group by source order by n desc"),
        "target": db.query_one("select * from targets limit 1"),
    }
