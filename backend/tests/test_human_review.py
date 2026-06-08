"""Exceptional / suspicious cases must escalate to a human — and a suspicious
document must NEVER be auto-rejected (SZHP-R7)."""
from __future__ import annotations

from app.schemas import CaseStatus, OutcomeType


def test_suspicious_document_escalates(run_fixture):
    case = run_fixture("suspicious_document")
    assert case.needs_human_review is True
    assert case.status == CaseStatus.PENDING_HUMAN_REVIEW
    assert case.fraud_flags.suspicious_doc or case.fraud_flags.income_mismatch
    assert case.escalation_reason


def test_suspicious_document_not_auto_rejected(run_fixture):
    case = run_fixture("suspicious_document")
    # Referred to officer, NOT auto-rejected.
    assert case.recommendation.outcome_type == OutcomeType.REFER_TO_OFFICER
    assert case.status != CaseStatus.REJECTED


def test_high_obligations_escalates(run_fixture):
    case = run_fixture("high_obligations")
    assert case.needs_human_review is True
    r6 = next(c for c in case.policy_checks if c.rule_id == "SZHP-R6")
    assert r6.result.value == "warn"


def test_proactive_flag_escalates(run_fixture):
    case = run_fixture("proactive_alert")
    assert case.is_proactive
    assert case.needs_human_review is True
