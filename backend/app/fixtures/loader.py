"""Fixture loading + DB seeding.

`python -m app.fixtures.loader` builds a case from every synthetic fixture, runs
it through the full pipeline, and persists the result so the officer queue /
proactive list / status pages have data on first launch.
"""
from __future__ import annotations

from ..graph import run_pipeline
from ..schemas import CaseState
from ..services import case_factory
from ..services.mocks import registry


def list_fixture_ids() -> list[str]:
    return sorted(registry.all_fixtures().keys())


def build_and_run(fixture_id: str, case_id: str | None = None) -> CaseState:
    """Create a case from a fixture and run the whole pipeline (no persistence)."""
    case = case_factory.create_case(fixture_id=fixture_id, case_id=case_id)
    return run_pipeline(case)


def seed_database() -> list[CaseState]:
    """Build, run and persist all fixtures. Deterministic case_ids so re-seeding
    is idempotent."""
    from ..db import get_repository

    repo = get_repository()
    out: list[CaseState] = []
    for fid in list_fixture_ids():
        case = build_and_run(fid, case_id=f"SZHP-DEMO-{fid.upper()}")
        repo.save(case)
        out.append(case)
    return out


def main() -> None:
    cases = seed_database()
    print(f"Seeded {len(cases)} demo case(s):")
    for c in cases:
        rec = c.recommendation
        tag = "HUMAN-REVIEW" if c.needs_human_review else "auto"
        print(
            f"  - {c.case_id:32s} {c.trigger_type.value:14s} "
            f"{(rec.outcome_type.value if rec else 'n/a'):22s} "
            f"[{tag}] conf={c.confidence.value if c.confidence else 0:.0%}"
        )


if __name__ == "__main__":
    main()
