"""Real document text extraction for citizen-uploaded files.

The citizen portal sends the actual file bytes; this service pulls the readable
text out of them so the assessment reads what is *on the document*, not a value
baked into a fixture. Text-based PDFs are parsed for real with pypdf. Files with
no text layer (scanned/image PDFs, PNG/JPG) have no extractable text without OCR
— for those we return no text and a low confidence, and the caller falls back to
the value on file. (OCR is intentionally out of scope: it needs a heavy system
binary; see requirements.txt.)
"""
from __future__ import annotations

import io

from ..schemas import DocumentType

# Filenames → type. Ordered most-specific first so e.g. "salary_certificate"
# wins before a looser "statement" match. This is authoritative: a file whose
# name clearly names its type is never reclassified by its contents (an
# application form mentioning the words "salary certificate" stays a form).
# UNKNOWN entries pin documents that exist in the pack but carry no financial
# fields, so they don't fall through to the content sniffer and get mislabelled.
_TYPE_HINTS: list[tuple[tuple[str, ...], DocumentType]] = [
    (("emirates", "eid", "uae_pass"), DocumentType.EMIRATES_ID),
    (("salary_cert", "salary certificate", "payslip"), DocumentType.SALARY_CERTIFICATE),
    (("suspicious_salary", "salary_disputed"), DocumentType.SALARY_CERTIFICATE),
    (("obligation", "liability", "aecb"), DocumentType.LIABILITY_LETTER),
    (("termination", "unemploy", "separation"), DocumentType.TERMINATION_LETTER),
    (("medical", "treatment"), DocumentType.MEDICAL_REPORT),
    (("hardship",), DocumentType.HARDSHIP_LETTER),
    # Bank/income evidence (kept after salary so "salary_certificate" wins).
    (("income_statement", "bank", "direct_debit", "transfer", "payment_history"), DocumentType.BANK_STATEMENT),
    # Pack documents that carry no extractable financial fields.
    (("application_form", "audit_trail", "recommendation_memo", "loan_statement",
      "arrears_statement", "active_request", "rejection", "block_notice",
      "missing_documents", "human_review", "family_status"), DocumentType.UNKNOWN),
    # Generic "statement" only after the specific ones above.
    (("statement",), DocumentType.BANK_STATEMENT),
]

# Content markers — used ONLY when the filename is uninformative (UNKNOWN).
# Strong, type-defining phrases only, to avoid a stray word reclassifying a doc.
_CONTENT_HINTS: list[tuple[tuple[str, ...], DocumentType]] = [
    (("net salary", "gross monthly salary", "basic salary"), DocumentType.SALARY_CERTIFICATE),
    (("salary transfer statement", "average monthly income", "salary credit"), DocumentType.BANK_STATEMENT),
    (("medical incapacity", "fit to work"), DocumentType.MEDICAL_REPORT),
    (("last working day", "termination effective"), DocumentType.TERMINATION_LETTER),
    (("credit bureau", "monthly obligation"), DocumentType.LIABILITY_LETTER),
]


def extract_text(file_bytes: bytes, file_name: str) -> str:
    """Best-effort plain-text extraction from an uploaded document.

    Returns the document's text, or "" when nothing readable can be pulled out
    (image-only PDF, PNG/JPG, or a parse failure) — the caller treats an empty
    result as "no text layer" and falls back gracefully.
    """
    name = (file_name or "").lower()
    if name.endswith(".pdf") or file_bytes[:5] == b"%PDF-":
        return _extract_pdf_text(file_bytes)
    # PNG/JPG (and any non-PDF) carry no text layer without OCR.
    return ""


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        # pypdf not installed — degrade rather than crash the upload.
        return ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                parts.append(txt)
        return "\n".join(parts).strip()
    except Exception:
        # Encrypted, malformed, or image-only PDF — no usable text.
        return ""


def infer_doc_type(file_name: str, text: str) -> DocumentType:
    """Classify by filename (authoritative), falling back to content only when
    the filename does not identify the type."""
    name = (file_name or "").lower()
    for keys, dtype in _TYPE_HINTS:
        if any(k in name for k in keys):
            # A filename that names a real type wins outright. UNKNOWN here means
            # "recognised pack doc with no financial fields" — also authoritative,
            # so we don't let its body text reclassify it.
            return dtype
    low = (text or "").lower()
    for keys, dtype in _CONTENT_HINTS:
        if any(k in low for k in keys):
            return dtype
    return DocumentType.UNKNOWN
