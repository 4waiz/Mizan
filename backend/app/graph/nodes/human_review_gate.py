"""Node 7 — human_review_gate.

Decide straight-through vs human review. Only exceptional, ambiguous, suspicious
or low-confidence cases are escalated; everything else is auto-issued.
"""
from __future__ import annotations

from ...config import get_settings
from ...schemas import (
    AuditEventType,
    CaseState,
    CaseStatus,
    OutcomeType,
    PolicyCheckResult,
)
from ...services import audit, llm

NODE = "human_review_gate"


def _escalation_reasons(state: CaseState) -> list[str]:
    settings = get_settings()
    reasons: list[str] = []
    rec = state.recommendation
    conf = state.confidence.value if state.confidence else 0.0

    if rec and rec.outcome_type == OutcomeType.REFER_TO_OFFICER:
        reasons.append("No automatic plan is clearly suitable.")
    if state.is_proactive:
        reasons.append("Proactive risk flag — officer outreach / early intervention.")
    if state.fraud_flags.has_high_severity:
        reasons.append("High-severity fraud flag requires human verification.")
    if state.fraud_flags.suspicious_doc:
        reasons.append("Suspicious document must be verified by an officer (SZHP-R7).")
    if conf < settings.auto_approve_confidence:
        reasons.append(f"Confidence {conf:.0%} below auto-approve threshold "
                       f"{settings.auto_approve_confidence:.0%}.")
    # High obligations + hardship is ambiguous -> review.
    obl_warn = any(
        c.rule_id == "SZHP-R6" and c.result == PolicyCheckResult.WARN
        for c in state.policy_checks
    )
    if obl_warn and rec and rec.outcome_type in (
        OutcomeType.UPDATE_INSTALLMENT,
        OutcomeType.TRANSFER_ARREARS,
    ):
        reasons.append("High external obligations alongside a repayment-change plan (SZHP-R6).")
    return reasons


def run(state: CaseState) -> CaseState:
    rec = state.recommendation
    outcome = rec.outcome_type if rec else OutcomeType.REFER_TO_OFFICER

    # Deterministic automated outcomes that do NOT need a human:
    auto_outcomes = {
        OutcomeType.REJECT_ACTIVE_REQUEST: CaseStatus.REJECTED,
        OutcomeType.REQUEST_MORE_INFO: CaseStatus.INFO_REQUESTED,
    }

    reasons = _escalation_reasons(state)
    needs_review = bool(reasons) or outcome == OutcomeType.REFER_TO_OFFICER

    # Active-request rejection and info requests are deterministic & clear, so
    # they auto-issue even though a flag may exist — unless a suspicious doc /
    # high-severity fraud demands a human.
    if outcome in auto_outcomes and not (
        state.fraud_flags.has_high_severity or state.fraud_flags.suspicious_doc
    ):
        needs_review = False

    state.needs_human_review = needs_review
    if rec:
        rec.straight_through = not needs_review

    if needs_review:
        if not reasons:
            reasons = ["Ambiguous case — manual review required."]
        state.escalation_reason = "; ".join(reasons)
        # LLM is used only to phrase the exception summary (structured/short).
        state.escalation_reason = llm.summarize_exception(state)
        state.status = CaseStatus.PENDING_HUMAN_REVIEW
        audit.record(
            state,
            AuditEventType.ESCALATED,
            "Escalated to officer: " + state.escalation_reason,
            node=NODE,
            evidence_ids=[e for f in state.fraud_flags.flags for e in f.evidence_ids],
        )
    else:
        state.status = auto_outcomes.get(outcome, CaseStatus.AUTO_APPROVED)
        audit.record(
            state,
            AuditEventType.NODE_COMPLETED,
            f"Straight-through: {outcome.value} (status {state.status.value}).",
            node=NODE,
        )
    return state
