"""Deterministic candidate-plan solver.

This is where the *recommendation* is decided — never the LLM. The solver:
  1. generates concrete candidate outcomes with real numbers,
  2. filters out any candidate that violates a hard rule (R1 income cap,
     R2 original-period cap, R3 active-request, R4 documents),
  3. ranks the survivors by sustainability and citizen burden,
  4. returns the ranked list; the node picks the top valid plan.

Loan math is profit-free (Sheikh Zayed housing assistance), so balances are
simple principal arithmetic.
"""
from __future__ import annotations

import math

from ..config import get_settings
from ..schemas import (
    CandidatePlan,
    CaseState,
    HardshipType,
    OutcomeType,
)
from . import rules

# Below this AED amount arrears are treated as negligible (rounding noise).
NEGLIGIBLE_ARREARS_AED = 1.0


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _burden_score(ratio: float, cap: float) -> float:
    """Lighter monthly burden -> higher score. 0 at the cap, 1 at zero outflow."""
    if cap <= 0:
        return 0.0
    return _clamp(1.0 - ratio / cap)


def generate_candidates(state: CaseState) -> list[CandidatePlan]:
    """Produce every candidate, each pre-marked valid/invalid against hard rules."""
    settings = get_settings()
    cap = settings.max_deduction_ratio
    candidates: list[CandidatePlan] = []

    income = state.beneficiary.monthly_income_aed if state.beneficiary else 0.0
    redefault = state.risk.redefault_probability if state.risk else 0.5
    is_hardship = bool(
        state.beneficiary and state.beneficiary.hardship_type != HardshipType.NONE
    )

    # ── Terminal / blocking candidates ───────────────────────────────────────
    if state.active_application.exists:
        candidates.append(
            CandidatePlan(
                outcome_type=OutcomeType.REJECT_ACTIVE_REQUEST,
                label_en="Reject — active application already open",
                label_ar="رفض — يوجد طلب نشط بالفعل",
                arrears_handling="No new plan; existing application must be closed first.",
                is_valid=True,
                rule_ids=["SZHP-R3"],
                rationale="A conflicting active application exists (SZHP-R3).",
            )
        )

    policy_checks = state.policy_checks or rules.run_policy_checks(state)
    if rules.documents_block_straight_through(policy_checks):
        candidates.append(
            CandidatePlan(
                outcome_type=OutcomeType.REQUEST_MORE_INFO,
                label_en="Request missing documents",
                label_ar="طلب المستندات الناقصة",
                arrears_handling="Cannot assess affordability until documents are complete.",
                is_valid=True,
                rule_ids=["SZHP-R4"],
                rationale="Required documents are missing (SZHP-R4).",
            )
        )

    if state.loan is None or state.arrears is None:
        return candidates or [_refer("Insufficient loan data to compute a plan.")]

    loan = state.loan
    arrears = state.arrears.arrears_amount_aed
    remaining_term = loan.remaining_term_months
    outstanding = loan.outstanding_principal_aed

    # ── 1) MAINTAIN_INSTALLMENT (only sensible with ~no arrears) ─────────────
    if arrears <= NEGLIGIBLE_ARREARS_AED:
        ratio = rules.deduction_ratio(loan.current_installment_aed, income)
        valid = rules.passes_deduction_cap(loan.current_installment_aed, income)
        candidates.append(
            _financial(
                OutcomeType.MAINTAIN_INSTALLMENT,
                "Maintain current installment",
                "الإبقاء على القسط الحالي",
                installment=loan.current_installment_aed,
                term=remaining_term,
                ratio=ratio,
                cap=cap,
                resolution=1.0,
                redefault=redefault,
                is_hardship=is_hardship,
                valid=valid,
                violated=[] if valid else ["SZHP-R1"],
                arrears_handling="No arrears outstanding; schedule unchanged.",
            )
        )

    # ── 2) UPDATE_INSTALLMENT — re-spread (outstanding + arrears) in-period ──
    if remaining_term > 0:
        new_installment = round((outstanding + arrears) / remaining_term, 2)
        ratio = rules.deduction_ratio(new_installment, income)
        violated: list[str] = []
        if not rules.passes_deduction_cap(new_installment, income):
            violated.append("SZHP-R1")
        if not rules.within_original_period(remaining_term, loan.original_term_months):
            violated.append("SZHP-R2")
        candidates.append(
            _financial(
                OutcomeType.UPDATE_INSTALLMENT,
                "Update installment to clear arrears within the original term",
                "تعديل القسط لتسوية المتأخرات ضمن المدة الأصلية",
                installment=new_installment,
                term=remaining_term,
                ratio=ratio,
                cap=cap,
                resolution=1.0,           # fully clears arrears inside the period
                redefault=redefault,
                is_hardship=is_hardship,
                valid=not violated,
                violated=violated,
                arrears_handling=(
                    f"Arrears of AED {arrears:,.0f} spread across the remaining "
                    f"{remaining_term} months; end date unchanged."
                ),
            )
        )

    # ── 3) TRANSFER_ARREARS — defer arrears to maturity (balloon) ───────────
    if arrears > NEGLIGIBLE_ARREARS_AED and remaining_term > 0:
        # Keep the current installment; park arrears as a lump at the original
        # maturity. End date is unchanged, so SZHP-R2 always holds.
        ratio = rules.deduction_ratio(loan.current_installment_aed, income)
        violated = [] if rules.passes_deduction_cap(loan.current_installment_aed, income) else ["SZHP-R1"]
        candidates.append(
            _financial(
                OutcomeType.TRANSFER_ARREARS,
                "Transfer arrears to end of schedule (keep installment low)",
                "ترحيل المتأخرات إلى نهاية الجدول مع الإبقاء على القسط",
                installment=loan.current_installment_aed,
                term=remaining_term,
                ratio=ratio,
                cap=cap,
                resolution=0.6,           # arrears deferred, not yet cleared
                redefault=redefault,
                is_hardship=is_hardship,
                valid=not violated,
                violated=violated,
                arrears_handling=(
                    f"Arrears of AED {arrears:,.0f} deferred to maturity; monthly "
                    f"burden kept at the current AED {loan.current_installment_aed:,.0f}."
                ),
                hardship_bonus=is_hardship,  # this is the hardship-preferred option
            )
        )

    # ── 4) Always offer REFER_TO_OFFICER as a safe fallback ─────────────────
    candidates.append(_refer("Fallback if no automatic plan is clearly suitable."))
    return candidates


def rank(candidates: list[CandidatePlan]) -> list[CandidatePlan]:
    """Valid first, then by composite score (sustainability + burden)."""
    return sorted(
        candidates,
        key=lambda c: (c.is_valid, c.composite_score),
        reverse=True,
    )


def solve(state: CaseState) -> list[CandidatePlan]:
    return rank(generate_candidates(state))


def best_financial_plan(ranked: list[CandidatePlan]) -> CandidatePlan | None:
    """Top valid plan that is an actual repayment arrangement."""
    financial = {
        OutcomeType.UPDATE_INSTALLMENT,
        OutcomeType.TRANSFER_ARREARS,
        OutcomeType.MAINTAIN_INSTALLMENT,
    }
    for c in ranked:
        if c.is_valid and c.outcome_type in financial:
            return c
    return None


# ── helpers ──────────────────────────────────────────────────────────────────
def _financial(
    outcome: OutcomeType,
    label_en: str,
    label_ar: str,
    *,
    installment: float,
    term: int,
    ratio: float,
    cap: float,
    resolution: float,
    redefault: float,
    is_hardship: bool,
    valid: bool,
    violated: list[str],
    arrears_handling: str,
    hardship_bonus: bool = False,
) -> CandidatePlan:
    burden = _burden_score(ratio, cap)
    sustainability = _clamp(0.5 * resolution + 0.5 * (1.0 - redefault))

    # Weighting: hardship cases prioritise low monthly burden; healthy cases
    # prioritise durable resolution of the arrears.
    if is_hardship:
        composite = 0.6 * burden + 0.4 * sustainability
    else:
        composite = 0.6 * sustainability + 0.4 * burden
    if hardship_bonus:
        composite = _clamp(composite + 0.05)   # nudge the hardship-preferred plan
    if not valid:
        composite = 0.0

    return CandidatePlan(
        outcome_type=outcome,
        label_en=label_en,
        label_ar=label_ar,
        new_installment_aed=round(installment, 2),
        new_term_months=term,
        projected_end_term_months=term,
        deduction_ratio=ratio,
        sustainability_score=round(sustainability, 3),
        citizen_burden_score=round(burden, 3),
        composite_score=round(composite, 3),
        is_valid=valid,
        violated_rule_ids=violated,
        rule_ids=["SZHP-R1", "SZHP-R2"] if valid else [],
        arrears_handling=arrears_handling,
        rationale=(
            f"Installment AED {installment:,.0f} = {ratio:.0%} of income "
            f"(cap {cap:.0%}); sustainability {sustainability:.2f}, "
            f"burden-relief {burden:.2f}."
            + ("" if valid else f" Rejected by {', '.join(violated)}.")
        ),
    )


def _refer(reason: str) -> CandidatePlan:
    return CandidatePlan(
        outcome_type=OutcomeType.REFER_TO_OFFICER,
        label_en="Refer to officer",
        label_ar="إحالة إلى الموظف المختص",
        is_valid=True,
        composite_score=0.01,    # always lowest, only wins if nothing else valid
        arrears_handling="Manual officer assessment required.",
        rationale=reason,
    )
