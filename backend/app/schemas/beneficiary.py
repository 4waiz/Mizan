"""Beneficiary, family and obligation snapshots — raw facts, never prompts."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import EmploymentStatus, HardshipType


class BeneficiaryProfile(BaseModel):
    """Auto-filled from UAE PASS + MOEI records (mocked here)."""

    beneficiary_id: str
    full_name_en: str
    full_name_ar: str
    emirates_id_masked: str = Field(..., description="Only last 4 digits, e.g. ***-****-1234")
    emirate: str
    employment_status: EmploymentStatus
    employer_name: str | None = None
    monthly_income_aed: float = Field(..., ge=0)
    income_verified: bool = False
    hardship_type: HardshipType = HardshipType.NONE
    hardship_notes: str | None = None


class FamilySnapshot(BaseModel):
    household_size: int = Field(..., ge=1)
    dependents: int = Field(0, ge=0)
    is_sole_earner: bool = True
    other_household_income_aed: float = Field(0, ge=0)


class ObligationItem(BaseModel):
    creditor: str
    monthly_payment_aed: float = Field(..., ge=0)
    outstanding_aed: float = Field(0, ge=0)
    kind: str = "loan"   # loan | credit_card | other


class ObligationSummary(BaseModel):
    """Aggregated external obligations (AECB / bank-style)."""

    items: list[ObligationItem] = Field(default_factory=list)
    total_monthly_obligations_aed: float = Field(0, ge=0)
    total_outstanding_aed: float = Field(0, ge=0)

    @classmethod
    def from_items(cls, items: list[ObligationItem]) -> "ObligationSummary":
        return cls(
            items=items,
            total_monthly_obligations_aed=round(sum(i.monthly_payment_aed for i in items), 2),
            total_outstanding_aed=round(sum(i.outstanding_aed for i in items), 2),
        )
