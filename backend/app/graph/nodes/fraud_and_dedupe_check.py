"""Node 3 — fraud_and_dedupe_check.

Compare independently-verified income against declared income, detect suspicious
documents and duplicate/active applications. Fraud uncertainty NEVER auto-rejects
— it raises a flag that routes the case to a human (SZHP-R7).
"""
from __future__ import annotations

from ...schemas import (
    AuditEventType,
    CaseState,
    DocumentStatus,
    FraudFlag,
    FraudFlags,
    Severity,
)
from ...services import audit
from ...services.mocks import mock_salary_verifier, registry

NODE = "fraud_and_dedupe_check"

_SUSPICIOUS_MARKERS = ("[ALTERED]", "[SUSPICIOUS]", "MISMATCH")


def run(state: CaseState) -> CaseState:
    bid = state.beneficiary.beneficiary_id if state.beneficiary else None
    record = registry.get_by_beneficiary_id(bid) if bid else {}
    flags: list[FraudFlag] = []

    # 1) Income mismatch (declared vs verified).
    verify = mock_salary_verifier.verify_income(record or {})
    income_mismatch = verify.get("matches_declared") is False
    if income_mismatch:
        flags.append(
            FraudFlag(
                code="INCOME_MISMATCH",
                severity=Severity.HIGH,
                description=(
                    f"Declared income differs from verified "
                    f"(verified AED {verify.get('verified_income_aed')})."
                ),
                evidence_ids=["salary_verifier"],
            )
        )

    # 2) Suspicious documents (markers or unreadable scans).
    suspicious_doc = bool((record or {}).get("suspicious_document"))
    for d in state.document_inventory.documents:
        text = (d.raw_text or "").upper()
        if d.status == DocumentStatus.UNREADABLE or any(m in text for m in _SUSPICIOUS_MARKERS):
            suspicious_doc = True
            flags.append(
                FraudFlag(
                    code="SUSPICIOUS_DOCUMENT",
                    severity=Severity.MEDIUM,
                    description=f"Document {d.document_id} ({d.doc_type.value}) looks irregular.",
                    evidence_ids=[d.document_id],
                )
            )

    # 3) Duplicate / active application.
    duplicate = state.active_application.exists or bool((record or {}).get("duplicate_application"))
    if duplicate:
        flags.append(
            FraudFlag(
                code="DUPLICATE_APPLICATION",
                severity=Severity.MEDIUM,
                description="An active or duplicate application already exists.",
                evidence_ids=["active_application"],
            )
        )

    state.fraud_flags = FraudFlags(
        flags=flags,
        suspicious_doc=suspicious_doc,
        duplicate_application=duplicate,
        income_mismatch=income_mismatch,
    )

    if flags:
        audit.record(
            state,
            AuditEventType.FRAUD_FLAG,
            "Raised " + ", ".join(f.code for f in flags) + ".",
            node=NODE,
            rule_ids=["SZHP-R7"],
            evidence_ids=[e for f in flags for e in f.evidence_ids],
        )
    else:
        audit.record(
            state,
            AuditEventType.NODE_COMPLETED,
            "No fraud or duplicate signals detected.",
            node=NODE,
        )
    return state
