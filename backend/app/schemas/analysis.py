"""Analysis artefacts: affordability, fraud, risk, candidate plans, policy checks,
confidence, explanation, rationale, audit, SLA. All produced by deterministic
code or by structured (Pydantic) LLM output — never free-form."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import (
    AuditEventType,
    OutcomeType,
    PolicyCheckResult,
    Severity,
)


# ── Affordability ────────────────────────────────────────────────────────────
class AffordabilityFeatures(BaseModel):
    monthly_income_aed: float = Field(..., ge=0)
    disposable_income_aed: float          # income - existing obligations (excl. this loan)
    max_affordable_installment_aed: float  # 20% cap applied
    current_deduction_ratio: float = Field(..., ge=0)   # current installment / income
    obligations_ratio: float = Field(..., ge=0)         # external obligations / income
    affordability_margin_aed: float       # max_affordable - current_installment
    data_completeness: float = Field(..., ge=0, le=1)


# ── Fraud / dedupe ───────────────────────────────────────────────────────────
class FraudFlag(BaseModel):
    code: str
    severity: Severity
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class FraudFlags(BaseModel):
    flags: list[FraudFlag] = Field(default_factory=list)
    suspicious_doc: bool = False
    duplicate_application: bool = False
    income_mismatch: bool = False

    @property
    def has_high_severity(self) -> bool:
        return any(f.severity == Severity.HIGH for f in self.flags)


# ── Risk forecast ────────────────────────────────────────────────────────────
class RiskScore(BaseModel):
    model_config = {"protected_namespaces": ()}

    redefault_probability: float = Field(..., ge=0, le=1)
    band: str  # low | medium | high
    drivers: list[str] = Field(default_factory=list)
    model_name: str = "heuristic"


# ── Candidate repayment plans ────────────────────────────────────────────────
class CandidatePlan(BaseModel):
    outcome_type: OutcomeType
    label_en: str
    label_ar: str
    new_installment_aed: float | None = None
    new_term_months: int | None = None
    arrears_handling: str | None = None        # how arrears are resolved
    projected_end_term_months: int | None = None
    deduction_ratio: float | None = None       # new installment / income
    # Scores in [0,1]; higher = better. Burden is inverted (higher = lighter burden).
    sustainability_score: float = 0.0
    citizen_burden_score: float = 0.0
    composite_score: float = 0.0
    is_valid: bool = True
    violated_rule_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)   # rules this plan satisfies
    rationale: str | None = None


# ── Policy checks ────────────────────────────────────────────────────────────
class PolicyCheck(BaseModel):
    rule_id: str
    title: str
    result: PolicyCheckResult
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)


# ── Confidence ───────────────────────────────────────────────────────────────
class ConfidenceScore(BaseModel):
    value: float = Field(..., ge=0, le=1)
    band: str  # low | medium | high
    components: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


# ── Explanation (machine-readable) ──────────────────────────────────────────
class Explanation(BaseModel):
    """Links a decision to the exact rules and evidence behind it."""

    summary_en: str
    rule_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    factors: list[str] = Field(default_factory=list)


# ── Bilingual rationale memo (LLM-generated, structured) ─────────────────────
class RationaleMemo(BaseModel):
    title_en: str
    title_ar: str
    body_en: str
    body_ar: str
    officer_summary: str | None = None     # short exception summary for the queue


# ── Final recommendation ─────────────────────────────────────────────────────
class Recommendation(BaseModel):
    outcome_type: OutcomeType
    decision_label_en: str
    decision_label_ar: str
    selected_plan: CandidatePlan | None = None
    straight_through: bool = False         # auto-issued vs needs human
    explanation: Explanation
    confidence: ConfidenceScore


# ── Audit & SLA ──────────────────────────────────────────────────────────────
class AuditEvent(BaseModel):
    event_id: str
    event_type: AuditEventType
    node: str | None = None
    message: str
    rule_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    timestamp: str
    actor: str = "system"                  # system | officer:<id>


class SLAClock(BaseModel):
    legacy_sla_working_days: int = 5
    created_at: str
    decided_at: str | None = None
    processing_ms: float | None = None
    deadline_at: str | None = None         # legacy deadline, for the "instant vs 5 days" story
