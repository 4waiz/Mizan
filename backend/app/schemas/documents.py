"""Document inventory + LLM-extracted fields (structured, never free text)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import DocumentStatus, DocumentType


class Document(BaseModel):
    document_id: str
    doc_type: DocumentType
    status: DocumentStatus = DocumentStatus.PRESENT
    file_name: str | None = None
    issued_on: str | None = None       # ISO date, used for freshness checks
    uploaded_on: str | None = None
    # Raw "content" the mock store hands back; the LLM/extractor reads this.
    raw_text: str | None = None


class DocumentInventory(BaseModel):
    required: list[DocumentType] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)

    def by_type(self, doc_type: DocumentType) -> Document | None:
        return next((d for d in self.documents if d.doc_type == doc_type), None)

    @property
    def present_types(self) -> set[DocumentType]:
        present = {d.doc_type for d in self.documents if d.status == DocumentStatus.PRESENT}
        # The Emirates ID is always available: identity is authenticated through
        # UAE PASS, whose profile carries the Emirates ID. It is never something
        # the beneficiary has to upload, so it always counts as present.
        present.add(DocumentType.EMIRATES_ID)
        return present

    @property
    def missing_required(self) -> list[DocumentType]:
        return [t for t in self.required if t not in self.present_types]


class ExtractedDocumentFields(BaseModel):
    """Fields the LLM/extractor pulls from documents — each Pydantic-typed.

    Confidence is per-extraction so the confidence node can weigh data quality.
    """

    declared_monthly_income_aed: float | None = None
    employer_name: str | None = None
    salary_certificate_date: str | None = None
    bank_avg_balance_aed: float | None = None
    bank_avg_monthly_credits_aed: float | None = None
    termination_effective_date: str | None = None
    medical_incapacity_months: int | None = None
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)
    classified_doc_types: list[DocumentType] = Field(default_factory=list)
    notes: str | None = None
