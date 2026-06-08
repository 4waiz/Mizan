"""Loan, arrears and payment-history snapshots from the (mock) MOEI core system."""
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class LoanSnapshot(BaseModel):
    """Profit-free housing loan (Sheikh Zayed Housing Programme)."""

    loan_id: str
    principal_aed: float = Field(..., gt=0, description="Original approved principal")
    outstanding_principal_aed: float = Field(..., ge=0)
    original_term_months: int = Field(..., gt=0, description="Original approved repayment period")
    months_elapsed: int = Field(..., ge=0)
    current_installment_aed: float = Field(..., gt=0)
    disbursed_on: str  # ISO date

    @computed_field  # type: ignore[misc]
    @property
    def remaining_term_months(self) -> int:
        """Months left within the *original* approved period (never negative)."""
        return max(self.original_term_months - self.months_elapsed, 0)


class ArrearsSnapshot(BaseModel):
    arrears_amount_aed: float = Field(..., ge=0, description="Total overdue amount")
    months_in_arrears: int = Field(..., ge=0)
    days_past_due: int = Field(..., ge=0)


class PaymentHistorySummary(BaseModel):
    total_installments_due: int = Field(..., ge=0)
    installments_paid_on_time: int = Field(..., ge=0)
    installments_late: int = Field(..., ge=0)
    installments_missed: int = Field(..., ge=0)
    longest_on_time_streak: int = Field(0, ge=0)

    @computed_field  # type: ignore[misc]
    @property
    def on_time_ratio(self) -> float:
        if self.total_installments_due == 0:
            return 1.0
        return round(self.installments_paid_on_time / self.total_installments_due, 3)


class ActiveApplication(BaseModel):
    """An already-open rescheduling/restructuring application, if any."""

    exists: bool = False
    application_id: str | None = None
    application_type: str | None = None
    opened_on: str | None = None
    status: str | None = None
