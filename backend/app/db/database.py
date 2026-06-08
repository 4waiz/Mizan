"""SQLite persistence (stdlib only, zero-setup for the local prototype).

All access goes through `repository.CaseRepository`; this module just owns the
connection + schema. To move to Postgres later, swap this file for a SQLAlchemy
engine and keep the repository interface unchanged.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id           TEXT PRIMARY KEY,
    status            TEXT NOT NULL,
    trigger_type      TEXT NOT NULL,
    beneficiary_name  TEXT,
    needs_review      INTEGER DEFAULT 0,
    confidence        REAL,
    arrears_amount    REAL,
    redefault_prob    REAL,
    created_at        TEXT,
    updated_at        TEXT,
    data              TEXT NOT NULL
);
"""


def _db_path() -> str:
    url = get_settings().database_url
    # Accept sqlite:///relative or sqlite:////absolute or a bare path.
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "", 1)
    return url


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    if path not in (":memory:", ""):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or get_connection()
    conn.executescript(_SCHEMA)
    conn.commit()
    if own:
        conn.close()
