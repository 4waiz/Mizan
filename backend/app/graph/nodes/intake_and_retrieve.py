"""Node 1 — intake_and_retrieve.

Given the authenticated beneficiary identity, pull every raw fact from the
(mock) source systems: MOEI loan core, bank/AECB obligations, document store.
"""
from __future__ import annotations

from ...schemas import AuditEventType, CaseState, CaseStatus, SLAClock
from ...services import audit
from ...services.mocks import (
    mock_bank_verifier,
    mock_document_store,
    mock_moei_loan_system,
    registry,
)

NODE = "intake_and_retrieve"


def run(state: CaseState) -> CaseState:
    bid = state.beneficiary.beneficiary_id if state.beneficiary else None
    record = registry.get_by_beneficiary_id(bid) if bid else None

    if record:
        state.loan = mock_moei_loan_system.get_loan(record)
        state.arrears = mock_moei_loan_system.get_arrears(record)
        state.payment_history = mock_moei_loan_system.get_payment_history(record)
        state.family = mock_moei_loan_system.get_family(record)
        state.active_application = mock_moei_loan_system.get_active_application(record)
        state.obligations = mock_bank_verifier.get_obligations(record)
        if not state.document_inventory.documents:
            state.document_inventory = mock_document_store.build_inventory(record)

    if state.sla is None:
        state.sla = SLAClock(legacy_sla_working_days=5, created_at=audit.now_iso())

    state.status = CaseStatus.PROCESSING
    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        f"Retrieved loan, arrears, payment history, family and obligations for {bid}.",
        node=NODE,
        evidence_ids=["uae_pass", "moei_loan_core", "bank_aecb"],
    )
    return state
