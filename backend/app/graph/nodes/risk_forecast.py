"""Node 5 — risk_forecast.

Forecast the probability of re-default with the lightweight (sklearn/heuristic)
model. Feeds plan sustainability scoring and the confidence/escalation logic.
"""
from __future__ import annotations

from ...schemas import AuditEventType, CaseState
from ...scoring import forecast_risk
from ...services import audit

NODE = "risk_forecast"


def run(state: CaseState) -> CaseState:
    state.risk = forecast_risk(state)
    audit.record(
        state,
        AuditEventType.NODE_COMPLETED,
        f"Re-default risk {state.risk.redefault_probability:.0%} ({state.risk.band}); "
        f"drivers: {', '.join(state.risk.drivers)}.",
        node=NODE,
        evidence_ids=[f"risk_model:{state.risk.model_name}"],
    )
    return state
