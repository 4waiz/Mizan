"""Node 9 — finalize_case.

Stamp the SLA clock (the 'instant vs 5 working days' story), emit the final
recommendation/escalation audit event, and seal the case.
"""
from __future__ import annotations

from datetime import datetime

from ...schemas import AuditEventType, CaseState
from ...services import audit

NODE = "finalize_case"


def run(state: CaseState) -> CaseState:
    now = audit.now_iso()
    if state.sla is not None:
        state.sla.decided_at = now
        try:
            created = datetime.fromisoformat(state.sla.created_at)
            decided = datetime.fromisoformat(now)
            state.sla.processing_ms = round((decided - created).total_seconds() * 1000, 1)
        except ValueError:
            state.sla.processing_ms = 0.0

    if state.needs_human_review:
        audit.record(
            state,
            AuditEventType.ESCALATED,
            f"Case sealed pending human review. Reason: {state.escalation_reason}.",
            node=NODE,
        )
    else:
        rec = state.recommendation
        audit.record(
            state,
            AuditEventType.RECOMMENDATION_ISSUED,
            f"Recommendation issued: {rec.outcome_type.value if rec else 'n/a'} "
            f"(straight-through).",
            node=NODE,
            rule_ids=rec.explanation.rule_ids if rec else [],
            evidence_ids=rec.explanation.evidence_ids if rec else [],
        )
    return state
