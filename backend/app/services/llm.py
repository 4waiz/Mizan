"""LLM service — the ONLY place models are used, and only for:
  * document field extraction,
  * document classification,
  * bilingual (EN/AR) rationale memos,
  * exception summarisation.

Every call returns a Pydantic model. With no API key configured a deterministic
`MockLLM` produces stable output so the whole app runs and tests are repeatable.
The model never makes the decision — that is the deterministic solver's job.
"""
from __future__ import annotations

import re

from ..config import get_settings
from ..schemas import (
    CandidatePlan,
    CaseState,
    DocumentType,
    ExtractedDocumentFields,
    HardshipType,
    RationaleMemo,
    Recommendation,
)

_MONEY_RE = re.compile(r"(?:AED|aed)?\s*([\d,]{3,})")


def _amount_for_label(text: str, label: str) -> float | None:
    """Pull the AED amount associated with a labelled field in document text.

    Handles both inline ("Net Salary: AED 29,500") and the two-line table layout
    produced by the document generator, where the label is on one line and the
    value on the next ("Net Salary\\nAED 29,500").
    """
    # Same line as the label.
    m = re.search(rf"{re.escape(label)}\s*[:\-]?\s*(?:AED|aed)?\s*([\d,]{{3,}})", text, re.IGNORECASE)
    if not m:
        # Label line, then the amount on the following line.
        m = re.search(
            rf"{re.escape(label)}\s*[:\-]?\s*\n\s*(?:AED|aed)?\s*([\d,]{{3,}})",
            text,
            re.IGNORECASE,
        )
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _parse_salary_income(text: str) -> float | None:
    """The income a salary certificate evidences: prefer net, then gross, then
    basic, then any first money figure as a last resort."""
    for label in ("Net Salary", "Net Monthly Salary", "Gross Monthly Salary", "Monthly Salary", "Basic Salary"):
        amt = _amount_for_label(text, label)
        if amt:
            return amt
    m = _MONEY_RE.search(text)
    return float(m.group(1).replace(",", "")) if m else None


# ── Deterministic mock extractor ─────────────────────────────────────────────
def _mock_extract(state: CaseState) -> ExtractedDocumentFields:
    inv = state.document_inventory
    fields = ExtractedDocumentFields(classified_doc_types=sorted(
        {d.doc_type for d in inv.documents}, key=lambda t: t.value
    ))

    salary = inv.by_type(DocumentType.SALARY_CERTIFICATE)
    if salary and salary.raw_text:
        income = _parse_salary_income(salary.raw_text)
        if income:
            fields.declared_monthly_income_aed = income
        fields.salary_certificate_date = salary.issued_on
        # Employer on the same line ("Employer: X") or the next ("Employer Name\nX").
        emp = re.search(r"Employer(?:\s*Name)?\s*[:\-]?\s*(.+)", salary.raw_text)
        if emp and emp.group(1).strip():
            fields.employer_name = emp.group(1).strip()
        else:
            emp2 = re.search(r"Employer(?:\s*Name)?\s*[:\-]?\s*\n\s*(.+)", salary.raw_text)
            if emp2:
                fields.employer_name = emp2.group(1).strip()

    bank = inv.by_type(DocumentType.BANK_STATEMENT)
    if bank and bank.raw_text:
        bals = [float(x.replace(",", "")) for x in _MONEY_RE.findall(bank.raw_text)]
        if bals:
            fields.bank_avg_balance_aed = round(sum(bals) / len(bals), 2)
            fields.bank_avg_monthly_credits_aed = max(bals)

    term = inv.by_type(DocumentType.TERMINATION_LETTER)
    if term:
        fields.termination_effective_date = term.issued_on

    med = inv.by_type(DocumentType.MEDICAL_REPORT)
    if med and med.raw_text:
        mm = re.search(r"(\d+)\s*month", med.raw_text)
        fields.medical_incapacity_months = int(mm.group(1)) if mm else 3

    # Confidence: lower when documents are missing/unreadable.
    present = len(inv.present_types)
    required = max(len(inv.required), 1)
    fields.extraction_confidence = round(min(present / required, 1.0) * 0.9 + 0.05, 3)
    fields.notes = "Deterministic MockLLM extraction (no API key configured)."
    return fields


# ── Deterministic mock memo (bilingual) ──────────────────────────────────────
_OUTCOME_AR = {
    "UPDATE_INSTALLMENT": "تعديل قيمة القسط",
    "TRANSFER_ARREARS": "ترحيل المتأخرات إلى نهاية الجدول",
    "MAINTAIN_INSTALLMENT": "الإبقاء على القسط الحالي",
    "REQUEST_MORE_INFO": "طلب مستندات إضافية",
    "REJECT_ACTIVE_REQUEST": "رفض الطلب لوجود طلب نشط",
    "REFER_TO_OFFICER": "إحالة الحالة إلى الموظف المختص",
}


def _mock_memo(state: CaseState, rec: Recommendation) -> RationaleMemo:
    name_en = state.beneficiary.full_name_en if state.beneficiary else "the beneficiary"
    name_ar = state.beneficiary.full_name_ar if state.beneficiary else "المستفيد"
    plan = rec.selected_plan
    rules_str = ", ".join(rec.explanation.rule_ids) or "applicable policy rules"

    plan_line_en = ""
    plan_line_ar = ""
    if plan and plan.new_installment_aed:
        plan_line_en = (
            f" The proposed monthly installment is AED {plan.new_installment_aed:,.0f} "
            f"({(plan.deduction_ratio or 0):.0%} of income) over {plan.new_term_months} months."
        )
        plan_line_ar = (
            f" القسط الشهري المقترح هو {plan.new_installment_aed:,.0f} درهم "
            f"({(plan.deduction_ratio or 0):.0%} من الدخل) على مدى {plan.new_term_months} شهراً."
        )

    body_en = (
        f"Case {state.case_id}: after reviewing the loan, arrears, income and "
        f"documents for {name_en}, the recommended outcome is "
        f"'{rec.decision_label_en}'.{plan_line_en} This decision complies with "
        f"{rules_str}. Confidence: {rec.confidence.value:.0%} ({rec.confidence.band})."
    )
    body_ar = (
        f"الحالة {state.case_id}: بعد مراجعة القرض والمتأخرات والدخل والمستندات "
        f"الخاصة بـ{name_ar}، فإن التوصية هي '{rec.decision_label_ar}'.{plan_line_ar} "
        f"يتوافق هذا القرار مع {rules_str}. درجة الثقة: {rec.confidence.value:.0%}."
    )
    officer_summary = None
    if state.needs_human_review:
        officer_summary = state.escalation_reason or "Escalated for manual review."

    return RationaleMemo(
        title_en=f"Arrears rescheduling recommendation — {rec.decision_label_en}",
        title_ar=f"توصية إعادة جدولة المتأخرات — {rec.decision_label_ar}",
        body_en=body_en,
        body_ar=body_ar,
        officer_summary=officer_summary,
    )


# ── Public API (real model path falls back to mock on any error) ─────────────
def extract_document_fields(state: CaseState) -> ExtractedDocumentFields:
    settings = get_settings()
    if not settings.use_real_llm:
        return _mock_extract(state)
    try:
        return _real_extract(state)
    except Exception:
        return _mock_extract(state)


def generate_rationale_memo(state: CaseState, rec: Recommendation) -> RationaleMemo:
    settings = get_settings()
    if not settings.use_real_llm:
        return _mock_memo(state, rec)
    try:
        return _real_memo(state, rec)
    except Exception:
        return _mock_memo(state, rec)


def summarize_exception(state: CaseState) -> str:
    """Short officer-queue summary of why a case escalated."""
    if state.escalation_reason:
        return state.escalation_reason
    flags = [f.description for f in state.fraud_flags.flags]
    if flags:
        return "; ".join(flags)
    return "Low confidence or ambiguous case — manual review required."


# ── Real (Anthropic via LangChain) — structured output only ─────────────────
def _get_chat_model():
    from langchain_anthropic import ChatAnthropic

    settings = get_settings()
    return ChatAnthropic(model=settings.llm_model, api_key=settings.anthropic_api_key, temperature=0)


def _real_extract(state: CaseState) -> ExtractedDocumentFields:
    model = _get_chat_model().with_structured_output(ExtractedDocumentFields)
    docs = "\n\n".join(
        f"[{d.doc_type.value}] issued {d.issued_on}:\n{d.raw_text or '(no text)'}"
        for d in state.document_inventory.documents
    )
    prompt = (
        "Extract the listed financial fields from these government documents. "
        "Only return values you can support from the text; set extraction_confidence "
        "honestly in [0,1]. Documents:\n\n" + docs
    )
    return model.invoke(prompt)  # type: ignore[return-value]


def _real_memo(state: CaseState, rec: Recommendation) -> RationaleMemo:
    model = _get_chat_model().with_structured_output(RationaleMemo)
    prompt = (
        "Write a concise bilingual (English + Arabic) recommendation memo for a "
        "Sheikh Zayed Housing Programme arrears case. Do NOT change the decision; "
        "explain it. Decision facts (JSON):\n"
        + rec.model_dump_json()
        + "\nCase id: "
        + state.case_id
    )
    return model.invoke(prompt)  # type: ignore[return-value]
