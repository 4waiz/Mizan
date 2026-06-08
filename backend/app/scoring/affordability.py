"""Affordability analysis — deterministic feature engineering for the solver."""
from __future__ import annotations

from ..config import get_settings
from ..schemas import AffordabilityFeatures, CaseState, DocumentType


def compute_affordability(state: CaseState) -> AffordabilityFeatures:
    settings = get_settings()
    ben = state.beneficiary
    income = ben.monthly_income_aed if ben else 0.0
    obligations = state.obligations.total_monthly_obligations_aed
    current_installment = state.loan.current_installment_aed if state.loan else 0.0

    max_affordable = round(income * settings.max_deduction_ratio, 2)
    disposable = round(income - obligations, 2)
    obl_ratio = round(obligations / income, 4) if income > 0 else 1.0
    current_ratio = round(current_installment / income, 4) if income > 0 else 1.0

    # Data completeness drives the confidence node; reward verified income +
    # presence of the key financial documents.
    inv = state.document_inventory
    signals = [
        bool(ben and ben.income_verified),
        DocumentType.SALARY_CERTIFICATE in inv.present_types,
        DocumentType.BANK_STATEMENT in inv.present_types,
        state.extracted_fields is not None
        and state.extracted_fields.extraction_confidence >= 0.6,
    ]
    completeness = round(sum(1 for s in signals if s) / len(signals), 3)

    return AffordabilityFeatures(
        monthly_income_aed=income,
        disposable_income_aed=disposable,
        max_affordable_installment_aed=max_affordable,
        current_deduction_ratio=current_ratio,
        obligations_ratio=obl_ratio,
        affordability_margin_aed=round(max_affordable - current_installment, 2),
        data_completeness=completeness,
    )
