"""Mapping from the synthetic demo scenarios to the real organizer-data patterns.

The demo citizens are **data-informed synthetic cases**: each one mirrors a
recurring pattern found in the organizer historical dataset
(``data/RescheduleArrears.xlsx``, 2023–2025). No real citizen identity is used —
the profiles are synthetic, but their *shape* (request type, arrears depth,
deduction pressure) is drawn from the historical distribution so the demo is
realistic rather than arbitrary.
"""
from __future__ import annotations

# Shown verbatim in the UI wherever synthetic demo identities appear.
SYNTHETIC_DATA_DISCLAIMER = (
    "Synthetic citizen profiles generated from historical patterns in the "
    "organizer dataset. No real citizen identities are displayed."
)

# fixture_id -> the historical pattern it is modelled on.
SCENARIO_PATTERN_MAP: dict[str, dict[str, str]] = {
    "clean_approval": {
        "pattern": "Common UPDATE_INSTALLMENT request, deduction under the 20% cap.",
        "historical_basis": "86.7% of historical requests are UPDATE_INSTALLMENT; median deduction ~15% of salary.",
        "rubric": "Agentic Decision Intelligence — straight-through on the dominant clean pattern.",
    },
    "missing_documents": {
        "pattern": "Document-validation case — incomplete pack blocks assessment.",
        "historical_basis": "Document completeness is a precondition before any historical request is approved.",
        "rubric": "Policy Compliance & Governance — deterministic completeness check.",
    },
    "high_obligations": {
        "pattern": "Affordability-pressure case — obligations high relative to income.",
        "historical_basis": "Sub-population where the current installment approaches/exceeds the 20% cap (~13% of cases).",
        "rubric": "Policy Compliance & Governance — 20% deduction-cap enforcement.",
    },
    "medical_hardship": {
        "pattern": "Temporary circumstance → transfer arrears to the loan end.",
        "historical_basis": "TRANSFER_ARREARS path (13.3% of historical requests), used for verified temporary hardship.",
        "rubric": "Agentic Decision Intelligence — humane, compliant treatment path.",
    },
    "unemployment_hardship": {
        "pattern": "Loss of stable income → maintain installment / transfer arrears.",
        "historical_basis": "Deeper-distress segment (Severe/Critical overdue bands, 46.8% of cases at 13+ months).",
        "rubric": "Impact on Service Transformation — early intervention before arrears worsen.",
    },
    "active_request_conflict": {
        "pattern": "Existing active application → governance auto-reject rule.",
        "historical_basis": "Rule 3: an active application may result in automatic rejection.",
        "rubric": "Policy Compliance & Governance — active-request validation.",
    },
    "duplicate_application": {
        "pattern": "Duplicate submission → governance / dedupe rule.",
        "historical_basis": "Duplicate-application detection guards against double-processing.",
        "rubric": "Policy Compliance & Governance — duplicate detection.",
    },
    "suspicious_document": {
        "pattern": "Inconsistent document → fraud-signal governance, human review.",
        "historical_basis": "Suspicious/inconsistent documents are never auto-rejected; they escalate to an officer.",
        "rubric": "Demo, Explainability & UX — never auto-reject on suspicion; hand the officer evidence.",
    },
    "proactive_alert": {
        "pattern": "Early-warning flag before serious arrears accumulate.",
        "historical_basis": "Calibrated on the organizer overdue-month distribution to flag rising risk early.",
        "rubric": "Impact on Service Transformation — proactive, pre-arrears intervention.",
    },
}


def demo_scenarios_payload() -> dict:
    return {
        "disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        "note": (
            "Demo scenarios are data-informed synthetic cases mapped to recurring "
            "patterns in the organizer historical dataset. Final decisions are "
            "always made by the deterministic policy engine, not by historical "
            "averages."
        ),
        "scenarios": SCENARIO_PATTERN_MAP,
    }
