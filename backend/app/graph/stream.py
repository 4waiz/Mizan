"""Step-by-step streaming runner for the case pipeline.

`run_pipeline` (builder.py) executes the whole graph in one shot — perfect for
seeding and tests. This module runs the *same* node functions one at a time and
yields a progress event after each, so the UI can show a live "auditing
documents → checking for fraud → …" load bar.

It also enforces an **early-exit on conflict**: if the fraud/dedupe node finds a
duplicate or active application, the case is a hard reject. There is no reason to
spend time on affordability or risk forecasting — the request is rejected
immediately, the skipped steps are reported, and the case is finalised.
"""
from __future__ import annotations

from collections.abc import Iterator

from ..schemas import (
    AuditEventType,
    CandidatePlan,
    CaseState,
    CaseStatus,
    ConfidenceScore,
    OutcomeType,
    Recommendation,
)
from ..services import audit, explain
from . import nodes

# Human-readable label + the present-tense "doing" phrase shown on the load bar,
# keyed by node name. Order matches PIPELINE.
STEP_LABELS: dict[str, dict[str, str]] = {
    "intake_and_retrieve": {
        "label": "Intake & retrieve records",
        "active": "Retrieving beneficiary & loan records",
    },
    "document_audit": {
        "label": "Document audit",
        "active": "Auditing documents",
    },
    "fraud_and_dedupe_check": {
        "label": "Fraud & duplicate check",
        "active": "Checking for fraud & duplicate applications",
    },
    "affordability_analysis": {
        "label": "Affordability analysis",
        "active": "Analysing affordability",
    },
    "risk_forecast": {
        "label": "Risk forecast",
        "active": "Forecasting re-default risk",
    },
    "policy_solver": {
        "label": "Policy solver",
        "active": "Solving policy-compliant repayment plans",
    },
    "human_review_gate": {
        "label": "Human-review gate",
        "active": "Deciding straight-through vs human review",
    },
    "rationale_generator": {
        "label": "Rationale memo",
        "active": "Writing the bilingual rationale memo",
    },
    "finalize_case": {
        "label": "Finalise case",
        "active": "Sealing the case & audit trail",
    },
}

# The full ordered list of step keys (used by the UI to lay out the load bar).
STEP_ORDER: list[str] = [n.NODE for n in nodes.PIPELINE]


def _meta(node_name: str) -> dict[str, str]:
    return STEP_LABELS.get(
        node_name, {"label": node_name, "active": node_name.replace("_", " ")}
    )


def _conflict_reason(state: CaseState) -> str | None:
    """If the case has a hard duplicate/active-application conflict, describe it."""
    ff = state.fraud_flags
    if state.active_application.exists or ff.duplicate_application:
        app = state.active_application
        if app.exists and app.application_id:
            return (
                f"A conflicting application ({app.application_id}, "
                f"status: {app.status or 'open'}) is already in progress. "
                "A beneficiary may only have one active rescheduling request at a time (SZHP-R3)."
            )
        return (
            "A duplicate or active rescheduling application already exists for this "
            "beneficiary. Only one active request is permitted at a time (SZHP-R3)."
        )
    return None


def _reject_for_conflict(state: CaseState, reason: str) -> CaseState:
    """Short-circuit the pipeline to an immediate rejection.

    Skips affordability + risk + the full solver: a duplicate request can never be
    rescheduled, so running those agents would be wasted work.
    """
    plan = CandidatePlan(
        outcome_type=OutcomeType.REJECT_ACTIVE_REQUEST,
        label_en="Reject — active application already open",
        label_ar="رفض — يوجد طلب نشط بالفعل",
        is_valid=True,
        rule_ids=["SZHP-R3"],
        arrears_handling="No new plan; the existing application must be closed first.",
        rationale=reason,
    )
    state.candidate_plans = [plan]
    # A duplicate/active-application conflict is a deterministic, unambiguous
    # rule outcome (SZHP-R3): the engine is fully confident in the rejection.
    confidence = ConfidenceScore(
        value=1.0,
        band="high",
        components={"policy_clarity": 1.0},
        reasons=["Deterministic conflict rule (SZHP-R3) — no ambiguity."],
    )
    state.confidence = confidence
    state.recommendation = Recommendation(
        outcome_type=OutcomeType.REJECT_ACTIVE_REQUEST,
        decision_label_en=plan.label_en,
        decision_label_ar=plan.label_ar,
        selected_plan=plan,
        straight_through=True,
        explanation=explain.build_explanation(state, plan),
        confidence=confidence,
    )
    state.needs_human_review = False
    state.escalation_reason = reason
    state.status = CaseStatus.REJECTED
    audit.record(
        state,
        AuditEventType.RECOMMENDATION_ISSUED,
        "Rejected immediately on conflict — affordability and risk analysis skipped. "
        + reason,
        node="conflict_exit",
        rule_ids=["SZHP-R3"],
        evidence_ids=["active_application"],
    )
    return state


def run_stream(case: CaseState) -> Iterator[dict]:
    """Run the pipeline node-by-node, yielding a progress event per step.

    Event shapes (all dicts):
      {"type": "start",   "steps": [{key,label}, ...]}
      {"type": "step",    "key, label, active, index, total"}        # before a node runs
      {"type": "done",    "key, index, total, status, message?"}     # after a node runs
      {"type": "skipped", "key, label, reason"}                      # node not run (early exit)
      {"type": "failed",  "reason, case}                             # hard conflict reject
      {"type": "complete","case}                                     # final state
    """
    pipeline = nodes.PIPELINE
    total = len(pipeline)

    yield {
        "type": "start",
        "steps": [{"key": n.NODE, **_meta(n.NODE)} for n in pipeline],
        "total": total,
    }

    for index, node_module in enumerate(pipeline):
        name = node_module.NODE
        meta = _meta(name)
        yield {
            "type": "step",
            "key": name,
            "label": meta["label"],
            "active": meta["active"],
            "index": index,
            "total": total,
        }

        case = node_module.run(case)

        # ── Early exit: a duplicate / active-application conflict is terminal. ──
        if name == "fraud_and_dedupe_check":
            reason = _conflict_reason(case)
            if reason is not None:
                yield {
                    "type": "done",
                    "key": name,
                    "index": index,
                    "total": total,
                    "status": "conflict",
                    "message": reason,
                }
                # Report every downstream step we are deliberately skipping.
                for skipped in pipeline[index + 1 :]:
                    skip_name = skipped.NODE
                    if skip_name in ("rationale_generator", "finalize_case"):
                        continue  # we still seal the case below
                    smeta = _meta(skip_name)
                    yield {
                        "type": "skipped",
                        "key": skip_name,
                        "label": smeta["label"],
                        "reason": "Not required — request rejected on conflict.",
                    }

                case = _reject_for_conflict(case, reason)
                # Seal the SLA clock without a rationale memo (rejection is final).
                case = nodes.finalize_case.run(case)
                yield {"type": "failed", "reason": reason, "case": case.model_dump(mode="json")}
                yield {"type": "complete", "case": case.model_dump(mode="json")}
                return

        yield {
            "type": "done",
            "key": name,
            "index": index,
            "total": total,
            "status": "ok",
        }

    yield {"type": "complete", "case": case.model_dump(mode="json")}
