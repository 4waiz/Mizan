"""An existing active application must block straight-through and reject."""
from __future__ import annotations

from app.schemas import CaseStatus, OutcomeType


def test_active_request_is_rejected(run_fixture):
    case = run_fixture("active_request_conflict")
    assert case.recommendation.outcome_type == OutcomeType.REJECT_ACTIVE_REQUEST
    assert case.status == CaseStatus.REJECTED
    # R3 must appear in the policy checks as a failure.
    r3 = next(c for c in case.policy_checks if c.rule_id == "SZHP-R3")
    assert r3.result.value == "fail"


def test_active_request_is_automated_not_escalated(run_fixture):
    # Clear, deterministic rejection -> straight-through (no human needed).
    case = run_fixture("active_request_conflict")
    assert case.needs_human_review is False
    assert case.recommendation.straight_through is True
