"""LangGraph nodes. Each exposes `run(CaseState) -> CaseState` and reads/writes
only the shared typed state."""
from . import (
    affordability_analysis,
    document_audit,
    finalize_case,
    fraud_and_dedupe_check,
    human_review_gate,
    intake_and_retrieve,
    policy_solver,
    rationale_generator,
    risk_forecast,
)

# Canonical execution order of the pipeline.
PIPELINE = [
    intake_and_retrieve,
    document_audit,
    fraud_and_dedupe_check,
    affordability_analysis,
    risk_forecast,
    policy_solver,
    human_review_gate,
    rationale_generator,
    finalize_case,
]

__all__ = [
    "intake_and_retrieve",
    "document_audit",
    "fraud_and_dedupe_check",
    "affordability_analysis",
    "risk_forecast",
    "policy_solver",
    "human_review_gate",
    "rationale_generator",
    "finalize_case",
    "PIPELINE",
]
