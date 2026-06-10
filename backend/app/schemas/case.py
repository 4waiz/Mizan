"""The shared, strongly-typed CaseState — the single object every graph node
reads from and writes to. It carries *raw facts*, never formatted prompts."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .analysis import (
    AffordabilityFeatures,
    AuditEvent,
    CandidatePlan,
    ConfidenceScore,
    FraudFlags,
    PolicyCheck,
    RationaleMemo,
    Recommendation,
    RiskScore,
    SLAClock,
    Telemetry,
)
from .beneficiary import BeneficiaryProfile, FamilySnapshot, ObligationSummary
from .documents import DocumentInventory, ExtractedDocumentFields
from .enums import CaseStatus, TriggerType
from .loan import (
    ActiveApplication,
    ArrearsSnapshot,
    LoanSnapshot,
    PaymentHistorySummary,
)


class OfficerDecision(BaseModel):
    officer_id: str
    action: str                 # approve | override | reject | request_info
    notes: str | None = None
    edited_plan: CandidatePlan | None = None
    decided_at: str


class CaseState(BaseModel):
    """End-to-end case record. Populated incrementally by the LangGraph nodes."""

    # --- identity / trigger ---
    case_id: str
    trigger_type: TriggerType = TriggerType.APPLICATION
    status: CaseStatus = CaseStatus.INTAKE
    # Source fixture this case was built from; lets the citizen portal "upload"
    # a document type and attach the matching record on file. None for cases
    # created outside the fixture flow.
    source_fixture_id: str | None = None

    # --- retrieved raw facts (intake_and_retrieve) ---
    beneficiary: BeneficiaryProfile | None = None
    loan: LoanSnapshot | None = None
    arrears: ArrearsSnapshot | None = None
    payment_history: PaymentHistorySummary | None = None
    family: FamilySnapshot | None = None
    active_application: ActiveApplication = Field(default_factory=ActiveApplication)
    obligations: ObligationSummary = Field(default_factory=ObligationSummary)

    # --- documents ---
    document_inventory: DocumentInventory = Field(default_factory=DocumentInventory)
    extracted_fields: ExtractedDocumentFields | None = None

    # --- analysis artefacts ---
    fraud_flags: FraudFlags = Field(default_factory=FraudFlags)
    affordability: AffordabilityFeatures | None = None
    risk: RiskScore | None = None
    candidate_plans: list[CandidatePlan] = Field(default_factory=list)
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    confidence: ConfidenceScore | None = None

    # --- routing / outcome ---
    needs_human_review: bool = False
    escalation_reason: str | None = None
    recommendation: Recommendation | None = None
    rationale_memo: RationaleMemo | None = None
    officer_decision: OfficerDecision | None = None

    # --- governance ---
    audit_events: list[AuditEvent] = Field(default_factory=list)
    sla: SLAClock | None = None

    # --- LLM telemetry (proof-of-work; observational, never affects decisions) ---
    telemetry: Telemetry = Field(default_factory=Telemetry)

    # convenience -------------------------------------------------------------
    def add_audit(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    @property
    def is_proactive(self) -> bool:
        return self.trigger_type == TriggerType.PROACTIVE_FLAG
