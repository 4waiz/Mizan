"""Mock salary / income verification service (e.g. employer or WPS feed).

Returns the independently verified income, which the fraud node compares against
the income declared on documents to detect mismatches.
"""
from __future__ import annotations


def verify_income(record: dict) -> dict:
    sv = record.get("salary_verification", {})
    declared = record.get("beneficiary", {}).get("monthly_income_aed")
    verified = sv.get("verified_income_aed", declared)
    return {
        "verified": sv.get("verified", True),
        "verified_income_aed": verified,
        "employer_name": sv.get("employer_name"),
        # Tolerance band for an acceptable match (10%).
        "matches_declared": (
            declared is not None
            and verified is not None
            and abs(verified - declared) <= 0.10 * max(declared, 1)
        ),
    }
