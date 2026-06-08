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
