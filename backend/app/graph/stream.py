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

import os
import time
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

# Per-step "thinking" time (seconds) so the live load bar reads like real
# processing instead of flashing through instantly. Heavier analytical steps
# (affordability, risk, policy solving) linger longer than bookkeeping ones.
# Every duration is scaled by the MIZAN_STEP_SPEED env var so the whole run can
# be sped up or slowed down at once (e.g. MIZAN_STEP_SPEED=0 disables it for
# tests, MIZAN_STEP_SPEED=2 doubles every pause).
STEP_DURATIONS: dict[str, float] = {
    "intake_and_retrieve": 1.6,
    "document_audit": 2.4,
    "fraud_and_dedupe_check": 2.0,
    "affordability_analysis": 3.2,
    "risk_forecast": 3.0,
    "policy_solver": 3.4,
    "human_review_gate": 1.8,
    "rationale_generator": 2.6,
    "finalize_case": 1.4,
}
_DEFAULT_DURATION = 2.0


def _step_speed() -> float:
    try:
        return max(0.0, float(os.getenv("MIZAN_STEP_SPEED", "1.0")))
    except ValueError:
        return 1.0


def _step_duration(node_name: str, speed: float) -> float:
    return STEP_DURATIONS.get(node_name, _DEFAULT_DURATION) * speed


def _meta(node_name: str) -> dict[str, str]:
    return STEP_LABELS.get(
        node_name, {"label": node_name, "active": node_name.replace("_", " ")}
    )


def _missing_documents_reason(state: CaseState) -> str | None:
    """If the case is still missing required documents, describe what's needed.

    The document audit runs first; an incomplete file can never produce a
    decision, so the pipeline stops here rather than burning affordability/risk
    analysis on a case that will only bounce back for more documents.
    """
    from ..policies import rules

    inv = state.document_inventory
    inv.required = rules.required_documents_for(state)
    missing = inv.missing_required
    if not missing:
        return None
    labels = {
        "emirates_id": "Emirates ID",
        "salary_certificate": "Salary certificate",
        "bank_statement": "Bank statement",
        "liability_letter": "Financial obligations letter",
        "termination_letter": "Termination / unemployment letter",
        "medical_report": "Medical report",
    }
    names = ", ".join(labels.get(m.value, m.value) for m in missing)
    return (
        "The application is incomplete — no decision is made on an incomplete "
        f"file. Missing required document(s): {names}. Please upload them and "
        "resubmit (SZHP-R4)."
    )


def _reject_for_missing_documents(state: CaseState, reason: str) -> CaseState:
    """Short-circuit the pipeline when required documents are missing.

    Mirrors the conflict exit: no plan is produced, the case is parked pending
    more information rather than rejected on its merits.
    """
    state.candidate_plans = []
    state.needs_human_review = True
    state.escalation_reason = reason
    state.status = CaseStatus.INFO_REQUESTED
    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        "Stopped during document audit — required documents missing. "
        "Affordability and risk analysis skipped. " + reason,
        node="document_audit",
        rule_ids=["SZHP-R4"],
        evidence_ids=["document_inventory"],
    )
    return state


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
      {"type": "telemetry","provider, model, live, total_calls, cumulative_usage, new_entries}
      {"type": "failed",  "reason, case}                             # hard conflict reject
      {"type": "complete","case}                                     # final state
    """
    pipeline = nodes.PIPELINE
    total = len(pipeline)
    speed = _step_speed()

    # Track how many telemetry log entries we've already streamed so each
    # "telemetry" event carries only the newly-appended LLM computation(s).
    streamed_calls = 0

    def telemetry_event(case: CaseState) -> dict | None:
        """Build a telemetry event for any log entries not yet streamed."""
        nonlocal streamed_calls
        log = case.telemetry.computation_log
        if len(log) <= streamed_calls:
            return None
        new_entries = [e.model_dump(mode="json") for e in log[streamed_calls:]]
        streamed_calls = len(log)
        return {
            "type": "telemetry",
            "provider": case.telemetry.provider,
            "model": case.telemetry.model,
            "live": case.telemetry.live,
            "total_calls": case.telemetry.total_calls,
            "cumulative_usage": case.telemetry.cumulative_usage.model_dump(mode="json"),
            "new_entries": new_entries,
        }

    # Start the processing clock when the assessment actually begins, so the
    # reported processing time reflects this run (not the gap since intake).
    if case.sla is not None:
        case.sla.created_at = audit.now_iso()

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

        # Linger on the "active" state so the step is visibly worked on rather
        # than completing instantly.
        dwell = _step_duration(name, speed)
        if dwell:
            time.sleep(dwell)

        case = node_module.run(case)

        # Stream any LLM telemetry this node produced (document_audit and
        # rationale_generator are the calls that actually burn tokens).
        tev = telemetry_event(case)
        if tev is not None:
            yield tev

        # ── Early exit: document audit found missing required documents. ──
        # The decision can't be made on an incomplete file, so stop here and
        # ask for the rest rather than running affordability/risk/solver.
        if name == "document_audit":
            reason = _missing_documents_reason(case)
            if reason is not None:
                yield {
                    "type": "done",
                    "key": name,
                    "index": index,
                    "total": total,
                    "status": "conflict",
                    "message": reason,
                }
                for skipped in pipeline[index + 1 :]:
                    skip_name = skipped.NODE
                    if skip_name in ("rationale_generator", "finalize_case"):
                        continue  # we still seal the case below
                    smeta = _meta(skip_name)
                    if speed:
                        time.sleep(0.6 * speed)
                    yield {
                        "type": "skipped",
                        "key": skip_name,
                        "label": smeta["label"],
                        "reason": "Not required — application incomplete.",
                    }

                case = _reject_for_missing_documents(case, reason)
                case = nodes.finalize_case.run(case)
                final_tev = telemetry_event(case)
                if final_tev is not None:
                    yield final_tev
                yield {"type": "failed", "reason": reason, "case": case.model_dump(mode="json")}
                yield {"type": "complete", "case": case.model_dump(mode="json")}
                return

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
                    if speed:
                        time.sleep(0.6 * speed)
                    yield {
                        "type": "skipped",
                        "key": skip_name,
                        "label": smeta["label"],
                        "reason": "Not required — request rejected on conflict.",
                    }

                case = _reject_for_conflict(case, reason)
                # Seal the SLA clock without a rationale memo (rejection is final).
                case = nodes.finalize_case.run(case)
                final_tev = telemetry_event(case)
                if final_tev is not None:
                    yield final_tev
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

    # Flush any trailing telemetry (e.g. the rationale memo call) before sealing.
    final_tev = telemetry_event(case)
    if final_tev is not None:
        yield final_tev

    yield {"type": "complete", "case": case.model_dump(mode="json")}
