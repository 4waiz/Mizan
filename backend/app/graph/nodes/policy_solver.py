"""Node 6 — policy_solver.

The decision node. Generates candidate plans, applies hard-rule precedence to
select the outcome, computes the confidence score, and assembles the (tentative)
recommendation. NO free-form LLM reasoning is involved.

Selection precedence:
  1. active application open       -> REJECT_ACTIVE_REQUEST  (SZHP-R3)
  2. suspicious docs / income fraud -> REFER_TO_OFFICER       (SZHP-R7, untrusted inputs)
  3. required documents missing    -> REQUEST_MORE_INFO      (SZHP-R4)
  4. otherwise best valid plan     -> UPDATE / TRANSFER / MAINTAIN
  5. nothing valid                 -> REFER_TO_OFFICER
"""
from __future__ import annotations

from ...policies import rules, solver
from ...schemas import (
    AuditEventType,
    CandidatePlan,
    CaseState,
    OutcomeType,
    Recommendation,
)
from ...scoring import compute_confidence
from ...services import audit, explain

NODE = "policy_solver"


def _find(plans: list[CandidatePlan], outcome: OutcomeType) -> CandidatePlan | None:
    return next((c for c in plans if c.outcome_type == outcome and c.is_valid), None)


def run(state: CaseState) -> CaseState:
    ranked = solver.solve(state)
    state.candidate_plans = ranked

    untrusted = state.fraud_flags.has_high_severity or state.fraud_flags.suspicious_doc
    if state.active_application.exists:
        chosen = _find(ranked, OutcomeType.REJECT_ACTIVE_REQUEST)
    elif untrusted:
        # Inputs cannot be trusted -> no automatic plan; hand to an officer.
        chosen = _find(ranked, OutcomeType.REFER_TO_OFFICER)
    elif rules.documents_block_straight_through(state.policy_checks):
        chosen = _find(ranked, OutcomeType.REQUEST_MORE_INFO)
    else:
        chosen = solver.best_financial_plan(ranked)

    if chosen is None:
        chosen = _find(ranked, OutcomeType.REFER_TO_OFFICER) or ranked[0]

    # Confidence (depends on candidates + checks + risk + fraud, all now set).
    state.confidence = compute_confidence(state)

    state.recommendation = Recommendation(
        outcome_type=chosen.outcome_type,
        decision_label_en=chosen.label_en,
        decision_label_ar=chosen.label_ar,
        selected_plan=chosen,
        straight_through=False,  # decided by the human_review_gate
        explanation=explain.build_explanation(state, chosen),
        confidence=state.confidence,
    )

    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        f"Selected {chosen.outcome_type.value} from {len(ranked)} candidate(s); "
        f"confidence {state.confidence.value:.0%} ({state.confidence.band}).",
        node=NODE,
        rule_ids=state.recommendation.explanation.rule_ids,
        evidence_ids=state.recommendation.explanation.evidence_ids,
    )
    return state
