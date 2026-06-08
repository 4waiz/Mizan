"""Pydantic v2 schemas for Mizan.

`CaseState` is the shared object the LangGraph nodes operate on; everything
else is a sub-model of it or part of the API contract.
"""
from __future__ import annotations

from .analysis import (
    AffordabilityFeatures,
    AuditEvent,
    CandidatePlan,
    ConfidenceScore,
    Explanation,
    FraudFlag,
    FraudFlags,
    PolicyCheck,
    RationaleMemo,
    Recommendation,
    RiskScore,
    SLAClock,
)
from .beneficiary import (
    BeneficiaryProfile,
    FamilySnapshot,
    ObligationItem,
    ObligationSummary,
)
from .case import CaseState, OfficerDecision
from .documents import Document, DocumentInventory, ExtractedDocumentFields
from .enums import (
    AuditEventType,
    CaseStatus,
    DocumentStatus,
    DocumentType,
    EmploymentStatus,
    HardshipType,
    OutcomeType,
    PolicyCheckResult,
    Severity,
    TriggerType,
)
from .loan import (
    ActiveApplication,
    ArrearsSnapshot,
    LoanSnapshot,
    PaymentHistorySummary,
)

__all__ = [
    "CaseState",
    "OfficerDecision",
    "BeneficiaryProfile",
    "FamilySnapshot",
    "ObligationItem",
    "ObligationSummary",
    "LoanSnapshot",
    "ArrearsSnapshot",
    "PaymentHistorySummary",
    "ActiveApplication",
    "Document",
    "DocumentInventory",
    "ExtractedDocumentFields",
    "AffordabilityFeatures",
    "FraudFlag",
    "FraudFlags",
    "RiskScore",
    "CandidatePlan",
    "PolicyCheck",
    "ConfidenceScore",
    "Explanation",
    "RationaleMemo",
    "Recommendation",
    "AuditEvent",
    "SLAClock",
    # enums
    "TriggerType",
    "EmploymentStatus",
    "HardshipType",
    "DocumentType",
    "DocumentStatus",
    "OutcomeType",
    "CaseStatus",
    "PolicyCheckResult",
    "Severity",
    "AuditEventType",
]
