"""Hard policy caps: the 20% income rule (SZHP-R1) and the original-period rule
(SZHP-R2), plus the solver never emitting a cap-breaching valid plan."""
from __future__ import annotations

from app.policies import rules, solver
from app.schemas import OutcomeType


def test_deduction_cap_boundary():
    # 20% of 10,000 = 2,000 exactly -> allowed; 2,001 -> blocked.
    assert rules.passes_deduction_cap(2000, 10000) is True
    assert rules.passes_deduction_cap(2001, 10000) is False
    assert rules.deduction_ratio(2500, 10000) == 0.25


def test_zero_income_never_passes_cap():
    assert rules.passes_deduction_cap(100, 0) is False


def test_within_original_period():
    assert rules.within_original_period(180, 240) is True
    assert rules.within_original_period(240, 240) is True
    assert rules.within_original_period(241, 240) is False


def test_solver_valid_plans_respect_cap(run_fixture):
    case = run_fixture("clean_approval")
    for plan in case.candidate_plans:
        if plan.is_valid and plan.deduction_ratio is not None:
            assert plan.deduction_ratio <= rules.get_settings().max_deduction_ratio + 1e-9


def test_solver_valid_plans_respect_original_period(run_fixture):
    case = run_fixture("clean_approval")
    original = case.loan.original_term_months
    for plan in case.candidate_plans:
        if plan.is_valid and plan.new_term_months is not None:
            assert plan.new_term_months <= original


def test_unaffordable_update_is_filtered(run_fixture):
    # Medical case: clearing arrears in the remaining term would breach the cap,
    # so UPDATE must be marked invalid and TRANSFER chosen instead.
    case = run_fixture("medical_hardship")
    update = next(
        (p for p in case.candidate_plans if p.outcome_type == OutcomeType.UPDATE_INSTALLMENT),
        None,
    )
    assert update is not None and update.is_valid is False
    assert "SZHP-R1" in update.violated_rule_ids
    assert case.recommendation.outcome_type == OutcomeType.TRANSFER_ARREARS
