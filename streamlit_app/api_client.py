"""Thin HTTP client for the Mizan FastAPI backend."""
from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("MIZAN_API_BASE_URL", "http://localhost:8000")
TIMEOUT = 30


class ApiError(Exception):
    pass


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _handle(resp: requests.Response):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ApiError(f"{resp.status_code}: {detail}")
    return resp.json()


def health() -> dict:
    return _handle(requests.get(_url("/"), timeout=TIMEOUT))


def list_fixtures() -> list[dict]:
    return _handle(requests.get(_url("/api/fixtures"), timeout=TIMEOUT))


def intake(fixture_id: str | None = None, beneficiary_id: str | None = None,
           trigger_type: str = "application") -> dict:
    return _handle(requests.post(_url("/api/cases/intake"),
                                 json={"fixture_id": fixture_id, "beneficiary_id": beneficiary_id,
                                       "trigger_type": trigger_type}, timeout=TIMEOUT))


def add_documents(case_id: str, documents: list[dict]) -> dict:
    return _handle(requests.post(_url(f"/api/cases/{case_id}/documents"),
                                 json={"documents": documents}, timeout=TIMEOUT))


def run_case(case_id: str) -> dict:
    return _handle(requests.post(_url(f"/api/cases/{case_id}/run"), timeout=TIMEOUT))


def get_case(case_id: str) -> dict:
    return _handle(requests.get(_url(f"/api/cases/{case_id}"), timeout=TIMEOUT))


def list_cases() -> list[dict]:
    return _handle(requests.get(_url("/api/cases"), timeout=TIMEOUT))


def get_audit(case_id: str) -> dict:
    return _handle(requests.get(_url(f"/api/cases/{case_id}/audit"), timeout=TIMEOUT))


def officer_queue() -> list[dict]:
    return _handle(requests.get(_url("/api/officer/queue"), timeout=TIMEOUT))


def officer_approve(case_id: str, officer_id: str, notes: str | None) -> dict:
    return _handle(requests.post(_url(f"/api/officer/{case_id}/approve"),
                                 json={"officer_id": officer_id, "notes": notes}, timeout=TIMEOUT))


def officer_reject(case_id: str, officer_id: str, notes: str | None) -> dict:
    return _handle(requests.post(_url(f"/api/officer/{case_id}/reject"),
                                 json={"officer_id": officer_id, "notes": notes}, timeout=TIMEOUT))


def officer_override(case_id: str, officer_id: str, outcome_type: str,
                     new_installment_aed: float | None, new_term_months: int | None,
                     notes: str | None) -> dict:
    return _handle(requests.post(_url(f"/api/officer/{case_id}/override"),
                                 json={"officer_id": officer_id, "outcome_type": outcome_type,
                                       "new_installment_aed": new_installment_aed,
                                       "new_term_months": new_term_months, "notes": notes},
                                 timeout=TIMEOUT))


def replay_summary() -> dict:
    return _handle(requests.get(_url("/api/replay/summary"), timeout=TIMEOUT))


def proactive_alerts() -> list[dict]:
    return _handle(requests.get(_url("/api/proactive/alerts"), timeout=TIMEOUT))
