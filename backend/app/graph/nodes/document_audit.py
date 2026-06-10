"""Node 2 — document_audit.

Classify + extract document fields (LLM, structured), then run the deterministic
document-completeness/freshness policy check (SZHP-R4). Missing required
documents block straight-through processing.
"""
from __future__ import annotations

from ...policies import rules
from ...schemas import AuditEventType, CaseState
from ...services import audit, llm

NODE = "document_audit"


def run(state: CaseState) -> CaseState:
    # LLM is used ONLY for extraction/classification — structured output.
    state.extracted_fields = llm.extract_document_fields(state)

    # The uploaded salary certificate is the source of truth for income: when the
    # extractor reads a figure off the document, it drives the beneficiary's
    # monthly income for affordability, the profile card and every downstream
    # metric — rather than a value baked into the record. This keeps the figure
    # the citizen sees on the PDF identical to the one the assessment uses.
    extracted_income = state.extracted_fields.declared_monthly_income_aed
    if state.beneficiary and extracted_income and extracted_income > 0:
        if state.beneficiary.monthly_income_aed != extracted_income:
            audit.record(
                state,
                AuditEventType.DOCUMENT_RECEIVED,
                f"Monthly income set to AED {extracted_income:,.0f} from the "
                f"salary certificate (was AED {state.beneficiary.monthly_income_aed:,.0f}).",
                node=NODE,
                rule_ids=["SZHP-R4"],
                evidence_ids=["salary_certificate"],
            )
        state.beneficiary.monthly_income_aed = extracted_income

    check = rules.check_documents(state)
    state.policy_checks = [c for c in state.policy_checks if c.rule_id != "SZHP-R4"]
    state.policy_checks.append(check)

    audit.record(
        state,
        AuditEventType.DOCUMENT_RECEIVED,
        f"Audited {len(state.document_inventory.documents)} document(s); "
        f"{check.result.value} on SZHP-R4 ({check.detail}).",
        node=NODE,
        rule_ids=["SZHP-R4"],
        evidence_ids=check.evidence_ids,
    )
    return state
