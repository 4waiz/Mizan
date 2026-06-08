"""Mock UAE PASS identity provider.

Simulates a UAE PASS single-sign-on that returns the verified citizen identity
and the auto-filled beneficiary profile. No real identifiers are used.
"""
from __future__ import annotations

from ...schemas import BeneficiaryProfile, EmploymentStatus, HardshipType


def authenticate(record: dict) -> dict:
    """Return the minimal verified identity (as UAE PASS would after login)."""
    ben = record.get("beneficiary", {})
    return {
        "authenticated": True,
        "beneficiary_id": ben.get("beneficiary_id"),
        "full_name_en": ben.get("full_name_en"),
        "full_name_ar": ben.get("full_name_ar"),
        "emirates_id_masked": ben.get("emirates_id_masked"),
    }


def get_profile(record: dict) -> BeneficiaryProfile:
    ben = dict(record.get("beneficiary", {}))
    ben.setdefault("employment_status", EmploymentStatus.EMPLOYED.value)
    ben.setdefault("hardship_type", HardshipType.NONE.value)
    return BeneficiaryProfile(**ben)
