"""Confidence scoring — decides straight-through vs human review.

Confidence blends data quality, evidence agreement, fraud signals, policy
clarity and how decisively the solver preferred one plan. Low confidence (or any
hard escalation trigger) routes the case to the officer queue.
"""
from __future__ import annotations

from ..schemas import CandidatePlan, CaseState, ConfidenceScore, PolicyCheckResult


def _solver_decisiveness(plans: list[CandidatePlan]) -> float:
    """Gap between the best and second-best valid financial plan -> decisiveness."""
    valid = sorted(
        [p for p in plans if p.is_valid and p.composite_score > 0.02],
        key=lambda p: p.composite_score,
        reverse=True,
    )
    if not valid:
        return 0.2
    if len(valid) == 1:
        return 0.9
    gap = valid[0].composite_score - valid[1].composite_score
    return round(min(0.5 + gap, 1.0), 3)


def compute_confidence(state: CaseState) -> ConfidenceScore:
    components: dict[str, float] = {}
    reasons: list[str] = []

    # 1) Data completeness
    completeness = state.affordability.data_completeness if state.affordability else 0.3
    components["data_completeness"] = round(completeness, 3)
    if completeness < 0.5:
        reasons.append("incomplete financial data")

    # 2) Extraction confidence
    extraction = (
        state.extracted_fields.extraction_confidence if state.extracted_fields else 0.4
    )
    components["extraction_confidence"] = round(extraction, 3)
    if extraction < 0.5:
        reasons.append("low document-extraction confidence")

    # 3) Fraud cleanliness (1 = clean)
    fraud = state.fraud_flags
    fraud_score = 1.0
    if fraud.has_high_severity:
        fraud_score = 0.2
        reasons.append("high-severity fraud flag")
    elif fraud.flags:
        fraud_score = 0.6
        reasons.append("fraud/anomaly flags present")
    components["fraud_clean"] = fraud_score

    # 4) Policy clarity (FAILs/WARNs reduce clarity)
    fails = sum(1 for c in state.policy_checks if c.result == PolicyCheckResult.FAIL)
    warns = sum(1 for c in state.policy_checks if c.result == PolicyCheckResult.WARN)
    policy_score = max(0.0, 1.0 - 0.3 * fails - 0.1 * warns)
    components["policy_clarity"] = round(policy_score, 3)
    if fails:
        reasons.append("policy check failure")

    # 5) Solver decisiveness
    decisiveness = _solver_decisiveness(state.candidate_plans)
    components["solver_decisiveness"] = decisiveness

    # Weighted blend
    weights = {
        "data_completeness": 0.20,
        "extraction_confidence": 0.15,
        "fraud_clean": 0.25,
        "policy_clarity": 0.20,
        "solver_decisiveness": 0.20,
    }
    value = round(sum(components[k] * w for k, w in weights.items()), 3)
    band = "high" if value >= 0.75 else "medium" if value >= 0.5 else "low"
    if not reasons:
        reasons.append("all signals consistent")

    return ConfidenceScore(value=value, band=band, components=components, reasons=reasons)
