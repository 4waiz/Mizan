"""Shared test setup: force deterministic MockLLM + an isolated temp database."""
from __future__ import annotations

import os
import tempfile

import pytest

# Force deterministic mode BEFORE the app config is imported/cached.
os.environ.setdefault("MIZAN_LLM_PROVIDER", "mock")
os.environ.pop("ANTHROPIC_API_KEY", None)
_TMP_DB = os.path.join(tempfile.gettempdir(), "mizan_test.db")
os.environ["MIZAN_DATABASE_URL"] = f"sqlite:///{_TMP_DB}"


@pytest.fixture(autouse=True)
def _clean_db():
    if os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)
    yield


@pytest.fixture
def run_fixture():
    from app.fixtures.loader import build_and_run

    return build_and_run
