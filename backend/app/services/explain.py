"""Build the machine-readable Explanation object linking a decision to the exact
rule_ids and evidence_ids behind it."""
from __future__ import annotations

from ..schemas import CandidatePlan, CaseState, Explanation, PolicyCheckResult


def build_explanation(state: CaseState, plan: CandidatePlan) -> Explanation:
    rule_ids: list[str] = list(plan.rule_ids)
    evidence_ids: list[str] = []
    factors: list[str] = []

    for check in state.policy_checks:
        if check.result in (PolicyCheckResult.PASS, PolicyCheckResult.FAIL, PolicyCheckResult.WARN):
            rule_ids.append(check.rule_id)
            evidence_ids.extend(check.evidence_ids)

    # Evidence from documents actually on file.
    evidence_ids.extend(d.document_id for d in state.document_inventory.documents)

    if state.affordability:
        factors.append(
            f"deduction {state.affordability.current_deduction_ratio:.0%} of income"
        )
        factors.append(
            f"obligations {state.affordability.obligations_ratio:.0%} of income"
        )
    if state.risk:
        factors.append(f"re-default risk {state.risk.redefault_probability:.0%} ({state.risk.band})")
        evidence_ids.append(f"risk_model:{state.risk.model_name}")
    if state.fraud_flags.flags:
        factors.extend(f"flag:{f.code}" for f in state.fraud_flags.flags)

    summary = plan.rationale or plan.label_en

    return Explanation(
        summary_en=summary,
        rule_ids=sorted(set(rule_ids)),
        evidence_ids=sorted(set(evidence_ids)),
        factors=factors,
    )
