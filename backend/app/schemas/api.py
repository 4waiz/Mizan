"""API request/response models (the public contract)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .case import CaseState
from .documents import Document
from .enums import CaseStatus, OutcomeType, TriggerType


class IntakeRequest(BaseModel):
    """Create a case. Either supply a fixture_id to load a synthetic case, or
    a beneficiary_id the mock connectors will resolve."""

    fixture_id: str | None = Field(
        None, description="Load one of the bundled synthetic cases by id."
    )
    beneficiary_id: str | None = None
    trigger_type: TriggerType = TriggerType.APPLICATION
    note: str | None = None


class IntakeResponse(BaseModel):
    case_id: str
    status: CaseStatus


class DocumentUploadRequest(BaseModel):
    documents: list[Document]


class RunResponse(BaseModel):
    case_id: str
    status: CaseStatus
    outcome_type: OutcomeType | None = None
    straight_through: bool = False
    needs_human_review: bool = False
    confidence: float | None = None
    case: CaseState


class OfficerActionRequest(BaseModel):
    officer_id: str = "officer-001"
    notes: str | None = None


class OverrideRequest(OfficerActionRequest):
    outcome_type: OutcomeType
    new_installment_aed: float | None = None
    new_term_months: int | None = None


class QueueItem(BaseModel):
    case_id: str
    beneficiary_name_en: str
    status: CaseStatus
    escalation_reason: str | None = None
    confidence: float | None = None
    arrears_amount_aed: float | None = None
    created_at: str | None = None


class ProactiveAlert(BaseModel):
    case_id: str
    beneficiary_name_en: str
    redefault_probability: float
    drivers: list[str]
    suggested_action: str
