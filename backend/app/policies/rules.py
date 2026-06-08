"""Hard policy rules for arrears rescheduling — enforced in deterministic code.

Every rule has a stable `rule_id` so decisions are auditable and explainable.
These functions are pure: they take facts and return verdicts. The LLM never
touches this module.
"""
from __future__ import annotations

from datetime import date, datetime

from ..config import get_settings
from ..schemas import (
    CaseState,
    DocumentType,
    EmploymentStatus,
    HardshipType,
    PolicyCheck,
    PolicyCheckResult,
)

# ── Rule catalogue ───────────────────────────────────────────────────────────
RULES: dict[str, str] = {
    "SZHP-R1": "Monthly deduction must not exceed 20% of beneficiary income",
    "SZHP-R2": "Proposed schedule must not exceed the original approved repayment period",
    "SZHP-R3": "An existing active application blocks a new straight-through decision",
    "SZHP-R4": "All required documents must be present and current",
    "SZHP-R5": "Arrears transfer / postponement requires a valid hardship justification",
    "SZHP-R6": "High external obligations reduce aggressiveness and may trigger review",
    "SZHP-R7": "Suspicious documents are referred to a human, never auto-rejected",
}

# Freshness window for income evidence (days).
SALARY_FRESHNESS_DAYS = 90
HIGH_OBLIGATIONS_RATIO = 0.50   # external obligations / income above this = "high"


# ── Atomic checks (used by the solver and the policy node) ───────────────────
def deduction_ratio(installment_aed: float, income_aed: float) -> float:
    if income_aed <= 0:
        return 1.0
    return round(installment_aed / income_aed, 4)


def passes_deduction_cap(installment_aed: float, income_aed: float) -> bool:
    """SZHP-R1: installment within 20% of income (configurable)."""
    cap = get_settings().max_deduction_ratio
    return deduction_ratio(installment_aed, income_aed) <= cap + 1e-9


def within_original_period(new_term_months: int, original_term_months: int) -> bool:
    """SZHP-R2: never extend beyond the original approved period."""
    return new_term_months <= original_term_months


def required_documents_for(state: CaseState) -> list[DocumentType]:
    """Document set required for straight-through processing, by situation."""
    req: list[DocumentType] = [DocumentType.EMIRATES_ID]
    ben = state.beneficiary
    if ben is None:
        return req

    if ben.employment_status in (EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED):
        req += [DocumentType.SALARY_CERTIFICATE, DocumentType.BANK_STATEMENT]
    if ben.hardship_type == HardshipType.UNEMPLOYMENT:
        req.append(DocumentType.TERMINATION_LETTER)
    if ben.hardship_type == HardshipType.MEDICAL:
        req.append(DocumentType.MEDICAL_REPORT)
    return req


def _days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date).date()
    except ValueError:
        return None
    return (date.today() - d).days


# ── High-level policy checks (one node calls this) ───────────────────────────
def check_active_application(state: CaseState) -> PolicyCheck:
    aa = state.active_application
    if aa.exists:
        return PolicyCheck(
            rule_id="SZHP-R3",
            title=RULES["SZHP-R3"],
            result=PolicyCheckResult.FAIL,
            detail=(
                f"Active application {aa.application_id or ''} "
                f"({aa.application_type or 'unknown'}) is already open."
            ),
            evidence_ids=[f"active_application:{aa.application_id or 'unknown'}"],
        )
    return PolicyCheck(
        rule_id="SZHP-R3",
        title=RULES["SZHP-R3"],
        result=PolicyCheckResult.PASS,
        detail="No conflicting active application.",
    )


def check_documents(state: CaseState) -> PolicyCheck:
    required = required_documents_for(state)
    inv = state.document_inventory
    inv.required = required
    missing = inv.missing_required

    # Freshness of the salary certificate (SZHP-R4 freshness facet).
    stale: list[str] = []
    salary = inv.by_type(DocumentType.SALARY_CERTIFICATE)
    if salary is not None:
        age = _days_since(salary.issued_on)
        if age is not None and age > SALARY_FRESHNESS_DAYS:
            stale.append(f"salary_certificate ({age}d old)")

    if missing:
        return PolicyCheck(
            rule_id="SZHP-R4",
            title=RULES["SZHP-R4"],
            result=PolicyCheckResult.FAIL,
            detail="Missing required documents: " + ", ".join(m.value for m in missing),
            evidence_ids=[f"missing:{m.value}" for m in missing],
        )
    if stale:
        return PolicyCheck(
            rule_id="SZHP-R4",
            title=RULES["SZHP-R4"],
            result=PolicyCheckResult.WARN,
            detail="Stale evidence: " + ", ".join(stale),
            evidence_ids=[f"stale:{s}" for s in stale],
        )
    return PolicyCheck(
        rule_id="SZHP-R4",
        title=RULES["SZHP-R4"],
        result=PolicyCheckResult.PASS,
        detail="All required documents present and current.",
        evidence_ids=[d.document_id for d in inv.documents],
    )


def check_obligations(state: CaseState) -> PolicyCheck:
    income = state.beneficiary.monthly_income_aed if state.beneficiary else 0.0
    obligations = state.obligations.total_monthly_obligations_aed
    ratio = round(obligations / income, 3) if income > 0 else 1.0
    if ratio >= HIGH_OBLIGATIONS_RATIO:
        return PolicyCheck(
            rule_id="SZHP-R6",
            title=RULES["SZHP-R6"],
            result=PolicyCheckResult.WARN,
            detail=f"External obligations are high ({ratio:.0%} of income).",
            evidence_ids=["obligations_summary"],
        )
    return PolicyCheck(
        rule_id="SZHP-R6",
        title=RULES["SZHP-R6"],
        result=PolicyCheckResult.PASS,
        detail=f"External obligations within normal range ({ratio:.0%} of income).",
        evidence_ids=["obligations_summary"],
    )


def check_hardship_evidence(state: CaseState) -> PolicyCheck:
    ben = state.beneficiary
    if ben is None or ben.hardship_type == HardshipType.NONE:
        return PolicyCheck(
            rule_id="SZHP-R5",
            title=RULES["SZHP-R5"],
            result=PolicyCheckResult.NOT_APPLICABLE,
            detail="No hardship claimed.",
        )
    inv = state.document_inventory
    needed = {
        HardshipType.UNEMPLOYMENT: DocumentType.TERMINATION_LETTER,
        HardshipType.MEDICAL: DocumentType.MEDICAL_REPORT,
    }.get(ben.hardship_type)
    if needed and needed not in inv.present_types:
        return PolicyCheck(
            rule_id="SZHP-R5",
            title=RULES["SZHP-R5"],
            result=PolicyCheckResult.FAIL,
            detail=f"Hardship '{ben.hardship_type.value}' claimed without {needed.value}.",
            evidence_ids=[f"missing:{needed.value}"],
        )
    return PolicyCheck(
        rule_id="SZHP-R5",
        title=RULES["SZHP-R5"],
        result=PolicyCheckResult.PASS,
        detail=f"Hardship '{ben.hardship_type.value}' supported by evidence.",
    )


def run_policy_checks(state: CaseState) -> list[PolicyCheck]:
    """Run the full deterministic policy sweep over the case."""
    return [
        check_active_application(state),
        check_documents(state),
        check_hardship_evidence(state),
        check_obligations(state),
    ]


def documents_block_straight_through(checks: list[PolicyCheck]) -> bool:
    return any(
        c.rule_id == "SZHP-R4" and c.result == PolicyCheckResult.FAIL for c in checks
    )


def has_hard_failure(checks: list[PolicyCheck]) -> bool:
    """Any FAIL that must stop straight-through processing."""
    return any(c.result == PolicyCheckResult.FAIL for c in checks)
