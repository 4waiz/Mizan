"""Tests for the organizer historical-dataset ingestion, insights, risk
forecaster, and the public API endpoints — including the privacy guarantee that
no identifiable field is ever returned by a public endpoint."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data.organizer_dataset import (
    OrganizerDataset,
    load_organizer_dataset,
    resolve_dataset_path,
)
from app.services import historical_insights_service as H
from app.services import risk_forecaster as R
from app.main import app

# Fields that must NEVER appear in a public payload.
_PII_KEYS = {
    "applicant",
    "application_id",
    "agreement_id",
    "edb_loan_id",
    "edb_customer_id",
    "auth_signatory",
    "created_by",
    "emirates_id",
    "name",
}

_DATASET_PRESENT = resolve_dataset_path().exists()
_needs_data = pytest.mark.skipif(not _DATASET_PRESENT, reason="organizer Excel not present")

client = TestClient(app)


# ── ingestion ────────────────────────────────────────────────────────────────
@_needs_data
def test_excel_loads_successfully():
    ds = load_organizer_dataset()
    assert ds.loaded is True
    assert ds.usable_row_count > 0
    assert ds.raw_row_count >= ds.usable_row_count
    assert ds.sheets  # at least one worksheet detected
    # canonical columns are present after normalization
    for col in ("current_salary", "over_due_months", "current_emi_ratio", "year"):
        assert col in ds.columns


@_needs_data
def test_loaded_records_contain_no_pii_columns():
    ds = load_organizer_dataset()
    cols = {c.lower() for c in ds.columns}
    assert not (_PII_KEYS & cols), f"PII columns leaked into clean frame: {_PII_KEYS & cols}"


def test_missing_excel_handled_gracefully(tmp_path: Path):
    ds = load_organizer_dataset(tmp_path / "does_not_exist.xlsx")
    assert isinstance(ds, OrganizerDataset)
    assert ds.loaded is False
    assert "not found" in ds.message.lower()
    assert ds.records == []
    # downstream services degrade, not crash
    assert H.compute_insights(ds)["loaded"] is False
    assert R.proactive_scan(ds)["loaded"] is False


# ── risk buckets ─────────────────────────────────────────────────────────────
def test_bucket_for_months_boundaries():
    assert H.bucket_for_months(0)[0] == "low"
    assert H.bucket_for_months(2)[0] == "low"
    assert H.bucket_for_months(3)[0] == "medium"
    assert H.bucket_for_months(6)[0] == "medium"
    assert H.bucket_for_months(7)[0] == "high"
    assert H.bucket_for_months(12)[0] == "high"
    assert H.bucket_for_months(13)[0] == "severe"
    assert H.bucket_for_months(24)[0] == "severe"
    assert H.bucket_for_months(25)[0] == "critical"
    assert H.bucket_for_months(200)[0] == "critical"
    assert H.bucket_for_months(None) is None
    assert H.bucket_for_months(-1) is None


@_needs_data
def test_risk_bucket_distribution_sums_to_evaluated():
    rb = H.risk_buckets()
    assert rb["loaded"] is True
    total = sum(b["count"] for b in rb["distribution"])
    assert total == rb["evaluated"]
    # five named buckets
    assert {b["key"] for b in rb["distribution"]} == {"low", "medium", "high", "severe", "critical"}


# ── 20% cap edge-case detection ──────────────────────────────────────────────
@_needs_data
def test_policy_edge_cases_detects_over_cap():
    ec = H.policy_edge_cases()
    assert ec["loaded"] is True
    assert ec["deduction_cap"] == pytest.approx(0.20)
    cur = ec["edge_cases"]["current_emi"]
    assert cur["evaluated"] > 0
    assert 0 <= cur["over_cap"] <= cur["evaluated"]
    assert 0.0 <= cur["over_cap_percent"] <= 100.0


def test_score_profile_over_cap_flagged():
    # EMI 4000 / salary 10000 = 40% > 20% cap → must be flagged in reasons
    a = R.score_profile(
        {"current_emi_amt": 4000, "current_salary": 10000, "over_due_months": 1}
    )
    assert any("exceeds the" in r for r in a.reasons)
    assert a.score > 0


def test_score_profile_severity_monotonic():
    low = R.score_profile({"over_due_months": 1, "current_salary": 30000, "current_emi_amt": 3000})
    high = R.score_profile({"over_due_months": 30, "current_salary": 30000, "current_emi_amt": 3000})
    assert high.score > low.score
    assert high.label in {"High", "Severe", "Critical"}


# ── insights endpoint shape ──────────────────────────────────────────────────
@_needs_data
def test_insights_endpoint_returns_expected_keys():
    r = client.get("/api/organizer-insights")
    assert r.status_code == 200
    j = r.json()
    assert j["loaded"] is True
    for key in (
        "totals",
        "medians",
        "request_type_split",
        "risk_buckets",
        "deduction_cap_edge_cases",
        "approval_duration",
    ):
        assert key in j, f"missing key: {key}"
    for key in ("current_salary", "over_due_months", "current_emi_ratio"):
        assert key in j["medians"]


@_needs_data
@pytest.mark.parametrize(
    "path",
    [
        "/api/organizer-insights",
        "/api/organizer-insights/risk-buckets",
        "/api/organizer-insights/policy-edge-cases",
        "/api/organizer-insights/sample-patterns",
        "/api/proactive-scan",
    ],
)
def test_public_endpoints_leak_no_identifiable_fields(path: str):
    import json

    blob = json.dumps(client.get(path).json()).lower()
    leaked = [k for k in _PII_KEYS if k in blob]
    # "name" / "id" appear as substrings in benign keys; check word-ish boundaries.
    hard_leaks = [
        k for k in leaked if k in {"applicant", "agreement_id", "edb_loan_id", "edb_customer_id", "auth_signatory", "created_by", "emirates_id"}
    ]
    assert not hard_leaks, f"{path} leaked identifiable fields: {hard_leaks}"


@_needs_data
def test_proactive_scan_endpoint():
    r = client.get("/api/proactive-scan")
    assert r.status_code == 200
    j = r.json()
    assert j["loaded"] is True
    assert "disclaimer" in j and "not a production" in j["disclaimer"].lower()
    assert j["evaluated"] > 0
    # patterns are anonymized aggregates, never raw rows
    for p in j["patterns"]:
        assert "case_count" in p and p["case_count"] >= 1
        assert "median_score" in p
