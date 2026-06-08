"""Node 8 — rationale_generator.

Generate the bilingual (EN/AR) rationale memo that explains the decision to the
beneficiary and summarises the exception for the officer. LLM output only — it
explains the decision, it never makes it.
"""
from __future__ import annotations

from ...schemas import AuditEventType, CaseState
from ...services import audit, llm

NODE = "rationale_generator"


def run(state: CaseState) -> CaseState:
    if state.recommendation is None:
        return state
    state.rationale_memo = llm.generate_rationale_memo(state, state.recommendation)
    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        "Generated bilingual rationale memo.",
        node=NODE,
    )
    return state
