"""With no model API key, the app must run and produce identical decisions on
repeated runs (deterministic MockLLM + deterministic policy engine)."""
from __future__ import annotations

from app.config import get_settings
from app.schemas import OutcomeType


def test_runs_without_api_key():
    assert get_settings().use_real_llm is False


def test_decisions_are_deterministic(run_fixture):
    for fid in [
        "clean_approval",
        "unemployment_hardship",
        "suspicious_document",
        "active_request_conflict",
    ]:
        a = run_fixture(fid)
        b = run_fixture(fid)
        assert a.recommendation.outcome_type == b.recommendation.outcome_type
        assert a.needs_human_review == b.needs_human_review
        assert a.confidence.value == b.confidence.value
        # Candidate financial figures are reproducible too.
        assert [p.new_installment_aed for p in a.candidate_plans] == [
            p.new_installment_aed for p in b.candidate_plans
        ]


def test_mock_extraction_present(run_fixture):
    case = run_fixture("clean_approval")
    assert case.extracted_fields is not None
    assert case.extracted_fields.declared_monthly_income_aed == 20000
