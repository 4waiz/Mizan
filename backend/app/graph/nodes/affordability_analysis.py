"""Node 4 — affordability_analysis.

Compute affordability features and run the full deterministic policy sweep
(active application R3, documents R4, hardship R5, obligations R6).
"""
from __future__ import annotations

from ...policies import rules
from ...schemas import AuditEventType, CaseState
from ...scoring import compute_affordability
from ...services import audit

NODE = "affordability_analysis"


def run(state: CaseState) -> CaseState:
    state.affordability = compute_affordability(state)

    # Full policy sweep; keep the document check already produced upstream.
    existing_docs = next((c for c in state.policy_checks if c.rule_id == "SZHP-R4"), None)
    checks = rules.run_policy_checks(state)
    if existing_docs is not None:
        checks = [existing_docs if c.rule_id == "SZHP-R4" else c for c in checks]
    state.policy_checks = checks

    for c in checks:
        audit.record(
            state,
            AuditEventType.POLICY_CHECK,
            f"{c.rule_id} → {c.result.value}: {c.detail}",
            node=NODE,
            rule_ids=[c.rule_id],
            evidence_ids=c.evidence_ids,
        )

    aff = state.affordability
    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        f"Affordability: max installment AED {aff.max_affordable_installment_aed:,.0f} "
        f"(20% cap), current deduction {aff.current_deduction_ratio:.0%}, "
        f"obligations {aff.obligations_ratio:.0%}.",
        node=NODE,
        rule_ids=["SZHP-R1"],
    )
    return state
