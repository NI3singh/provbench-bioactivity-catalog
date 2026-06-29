"""Database access — a small psycopg3 connection pool against Postgres (Neon).

Uses a pooled SSL connection. prepare_threshold=None avoids the PgBouncer
prepared-statement problem in transaction mode; autocommit=True keeps reads simple.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# override=True so the project's .env wins over any stale GEMINI_API_KEY / DATABASE_URL
# left in the shell or OS environment (python-dotenv does NOT override by default).
load_dotenv(override=True)

DSN = os.getenv("DATABASE_URL") or os.getenv("neon_DB_URL", "")
DEFAULT_TARGET = os.getenv("DEFAULT_TARGET", "P00533")

pool = ConnectionPool(
    conninfo=DSN,
    min_size=1,
    max_size=4,
    open=False,
    kwargs={"prepare_threshold": None, "autocommit": True},
)


def query(sql: str, params=None) -> list[dict]:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def query_one(sql: str, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None
