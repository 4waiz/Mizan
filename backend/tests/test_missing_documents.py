"""Missing required documents must block straight-through processing."""
from __future__ import annotations

from app.schemas import CaseStatus, DocumentType, OutcomeType


def test_missing_documents_requests_more_info(run_fixture):
    case = run_fixture("missing_documents")
    assert case.recommendation.outcome_type == OutcomeType.REQUEST_MORE_INFO
    assert case.status == CaseStatus.INFO_REQUESTED


def test_missing_documents_fails_r4(run_fixture):
    case = run_fixture("missing_documents")
    r4 = next(c for c in case.policy_checks if c.rule_id == "SZHP-R4")
    assert r4.result.value == "fail"
    missing = case.document_inventory.missing_required
    assert DocumentType.SALARY_CERTIFICATE in missing
    assert DocumentType.BANK_STATEMENT in missing
