"""The clean case: straight-through approval with a full explanation + memo."""
from __future__ import annotations

from app.schemas import CaseStatus, OutcomeType


def test_clean_case_auto_approves(run_fixture):
    case = run_fixture("clean_approval")
    assert case.recommendation.outcome_type == OutcomeType.UPDATE_INSTALLMENT
    assert case.status == CaseStatus.AUTO_APPROVED
    assert case.needs_human_review is False
    assert case.recommendation.straight_through is True


def test_clean_case_has_explanation_and_evidence(run_fixture):
    case = run_fixture("clean_approval")
    exp = case.recommendation.explanation
    assert "SZHP-R1" in exp.rule_ids
    assert exp.evidence_ids  # links to documents / risk model
    assert case.confidence.value >= 0.75


def test_clean_case_generates_bilingual_memo(run_fixture):
    case = run_fixture("clean_approval")
    memo = case.rationale_memo
    assert memo is not None
    assert memo.body_en and memo.body_ar
    # Arabic body must contain Arabic script.
    assert any("؀" <= ch <= "ۿ" for ch in memo.body_ar)


def test_audit_trail_is_populated(run_fixture):
    case = run_fixture("clean_approval")
    nodes_seen = {e.node for e in case.audit_events}
    assert "policy_solver" in nodes_seen
    assert "finalize_case" in nodes_seen
    assert case.sla and case.sla.processing_ms is not None
