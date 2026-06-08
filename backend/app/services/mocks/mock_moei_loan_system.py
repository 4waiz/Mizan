"""Mock MOEI / Sheikh Zayed Housing Programme core loan system.

Returns the loan, arrears, payment-history, family and active-application
snapshots for a beneficiary.
"""
from __future__ import annotations

from ...schemas import (
    ActiveApplication,
    ArrearsSnapshot,
    FamilySnapshot,
    LoanSnapshot,
    PaymentHistorySummary,
)


def get_loan(record: dict) -> LoanSnapshot:
    return LoanSnapshot(**record["loan"])


def get_arrears(record: dict) -> ArrearsSnapshot:
    return ArrearsSnapshot(**record["arrears"])


def get_payment_history(record: dict) -> PaymentHistorySummary:
    return PaymentHistorySummary(**record["payment_history"])


def get_family(record: dict) -> FamilySnapshot:
    return FamilySnapshot(**record.get("family", {"household_size": 1}))


def get_active_application(record: dict) -> ActiveApplication:
    return ActiveApplication(**record.get("active_application", {"exists": False}))
