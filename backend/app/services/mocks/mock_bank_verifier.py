"""Mock bank / AECB obligations verifier.

Returns the beneficiary's external monthly obligations (other loans, cards),
used by the affordability and obligations-policy checks.
"""
from __future__ import annotations

from ...schemas import ObligationItem, ObligationSummary


def get_obligations(record: dict) -> ObligationSummary:
    raw = record.get("obligations", {})
    items = [ObligationItem(**i) for i in raw.get("items", [])]
    return ObligationSummary.from_items(items)
