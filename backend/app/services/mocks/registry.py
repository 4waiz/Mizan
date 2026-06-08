"""Shared in-memory 'source of truth' for the mock connectors.

Loads the synthetic fixture records (backend/app/fixtures/cases/*.json) once and
indexes them by fixture_id and by beneficiary_id. Each connector reads its slice
of these records, simulating separate government systems.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "cases"


@lru_cache
def _load() -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not _FIXTURES_DIR.exists():
        return records
    for path in sorted(_FIXTURES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        fixture_id = data.get("fixture_id", path.stem)
        data["fixture_id"] = fixture_id
        records[fixture_id] = data
    return records


def all_fixtures() -> dict[str, dict]:
    return _load()


def get_by_fixture_id(fixture_id: str) -> dict | None:
    return _load().get(fixture_id)


def get_by_beneficiary_id(beneficiary_id: str) -> dict | None:
    for rec in _load().values():
        if rec.get("beneficiary", {}).get("beneficiary_id") == beneficiary_id:
            return rec
    return None


def resolve(fixture_id: str | None, beneficiary_id: str | None) -> dict | None:
    if fixture_id:
        return get_by_fixture_id(fixture_id)
    if beneficiary_id:
        return get_by_beneficiary_id(beneficiary_id)
    return None
