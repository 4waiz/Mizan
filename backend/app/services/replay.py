"""Masked historical replay.

Runs every synthetic fixture through the pipeline and aggregates the outcome to
demonstrate consistency and the time saved versus the 5-working-day manual
process. Inputs are masked synthetic records — no real identifiers.
"""
from __future__ import annotations

from ..config import get_settings
from ..fixtures.loader import build_and_run, list_fixture_ids


def replay_summary() -> dict:
    settings = get_settings()
    cases = [build_and_run(fid) for fid in list_fixture_ids()]
    total = len(cases)

    auto = sum(1 for c in cases if not c.needs_human_review)
    review = total - auto
    by_outcome: dict[str, int] = {}
    proc_times: list[float] = []

    rows = []
    for c in cases:
        rec = c.recommendation
        outcome = rec.outcome_type.value if rec else "n/a"
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        if c.sla and c.sla.processing_ms is not None:
            proc_times.append(c.sla.processing_ms)
        rows.append(
            {
                "case_id": c.case_id,
                "trigger_type": c.trigger_type.value,
                "outcome": outcome,
                "needs_human_review": c.needs_human_review,
                "confidence": c.confidence.value if c.confidence else None,
                "processing_ms": c.sla.processing_ms if c.sla else None,
            }
        )

    avg_ms = round(sum(proc_times) / len(proc_times), 1) if proc_times else 0.0
    # Each case historically took up to `sla_working_days`; STP saves that wait.
    manual_days_saved = auto * settings.sla_working_days

    return {
        "total_cases": total,
        "straight_through": auto,
        "human_review": review,
        "straight_through_rate": round(auto / total, 3) if total else 0.0,
        "by_outcome": by_outcome,
        "avg_processing_ms": avg_ms,
        "legacy_sla_working_days": settings.sla_working_days,
        "estimated_manual_working_days_saved": manual_days_saved,
        "cases": rows,
    }
