"""Enumerations shared across the Mizan case state.

Centralising these keeps node logic, the policy engine, and the API contract
in lock-step. String enums so they serialise cleanly to JSON / SQLite.
"""
from __future__ import annotations

from enum import Enum


class TriggerType(str, Enum):
    """What caused this case to exist."""

    APPLICATION = "application"          # beneficiary-initiated rescheduling request
    PROACTIVE_FLAG = "proactive_flag"    # system detected emerging arrears risk (bonus)


class EmploymentStatus(str, Enum):
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"


class HardshipType(str, Enum):
    NONE = "none"
    UNEMPLOYMENT = "unemployment"
    MEDICAL = "medical"
    REDUCED_INCOME = "reduced_income"
    BEREAVEMENT = "bereavement"
    OTHER = "other"


class DocumentType(str, Enum):
    EMIRATES_ID = "emirates_id"
    SALARY_CERTIFICATE = "salary_certificate"
    BANK_STATEMENT = "bank_statement"
    TERMINATION_LETTER = "termination_letter"
    MEDICAL_REPORT = "medical_report"
    LIABILITY_LETTER = "liability_letter"     # AECB / obligations
    HARDSHIP_LETTER = "hardship_letter"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    EXPIRED = "expired"
    UNREADABLE = "unreadable"


class OutcomeType(str, Enum):
    """Candidate outcomes the deterministic solver can propose."""

    UPDATE_INSTALLMENT = "UPDATE_INSTALLMENT"        # re-spread balance within original term
    TRANSFER_ARREARS = "TRANSFER_ARREARS"            # defer arrears to maturity (balloon)
    MAINTAIN_INSTALLMENT = "MAINTAIN_INSTALLMENT"    # no change required
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"          # blocked on documents / data
    REJECT_ACTIVE_REQUEST = "REJECT_ACTIVE_REQUEST"  # active application conflict
    REFER_TO_OFFICER = "REFER_TO_OFFICER"            # escalate to human


class CaseStatus(str, Enum):
    INTAKE = "intake"
    PROCESSING = "processing"
    AUTO_APPROVED = "auto_approved"          # straight-through recommendation issued
    PENDING_HUMAN_REVIEW = "pending_human_review"
    OFFICER_APPROVED = "officer_approved"
    OFFICER_OVERRIDDEN = "officer_overridden"
    OFFICER_REJECTED = "officer_rejected"
    INFO_REQUESTED = "info_requested"
    REJECTED = "rejected"


class PolicyCheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    NOT_APPLICABLE = "not_applicable"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuditEventType(str, Enum):
    CASE_CREATED = "case_created"
    NODE_COMPLETED = "node_completed"
    POLICY_CHECK = "policy_check"
    FRAUD_FLAG = "fraud_flag"
    RECOMMENDATION_ISSUED = "recommendation_issued"
    ESCALATED = "escalated"
    OFFICER_ACTION = "officer_action"
    DOCUMENT_RECEIVED = "document_received"
