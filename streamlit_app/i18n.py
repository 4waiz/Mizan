"""Minimal English/Arabic label dictionary for the workflow UI."""
from __future__ import annotations

import streamlit as st

T = {
    "app_title": {"en": "Mizan — Arrears Rescheduling", "ar": "ميزان — إعادة جدولة المتأخرات"},
    "subtitle": {
        "en": "Sheikh Zayed Housing Programme · MOEI",
        "ar": "برنامج الشيخ زايد للإسكان · وزارة الطاقة والبنية التحتية",
    },
    "login": {"en": "Sign in with UAE PASS", "ar": "تسجيل الدخول عبر الهوية الرقمية"},
    "beneficiary": {"en": "Beneficiary", "ar": "المستفيد"},
    "officer": {"en": "Officer", "ar": "الموظف"},
    "new_request": {"en": "New Rescheduling Request", "ar": "طلب إعادة جدولة جديد"},
    "profile": {"en": "Beneficiary Profile", "ar": "ملف المستفيد"},
    "documents": {"en": "Documents", "ar": "المستندات"},
    "validation": {"en": "Validation", "ar": "التحقق"},
    "recommendation": {"en": "Recommendation", "ar": "التوصية"},
    "status": {"en": "Case Status", "ar": "حالة الطلب"},
    "queue": {"en": "Review Queue", "ar": "قائمة المراجعة"},
    "confidence": {"en": "Confidence", "ar": "درجة الثقة"},
    "risk": {"en": "Re-default risk", "ar": "مخاطر التعثر"},
    "income": {"en": "Monthly income", "ar": "الدخل الشهري"},
    "installment": {"en": "Installment", "ar": "القسط"},
    "arrears": {"en": "Arrears", "ar": "المتأخرات"},
    "approve": {"en": "Approve", "ar": "اعتماد"},
    "override": {"en": "Override", "ar": "تعديل/تجاوز"},
    "reject": {"en": "Reject", "ar": "رفض"},
    "notes": {"en": "Decision notes", "ar": "ملاحظات القرار"},
    "submit": {"en": "Submit request", "ar": "إرسال الطلب"},
    "run": {"en": "Run assessment", "ar": "تشغيل التقييم"},
    "escalation": {"en": "Escalation reason", "ar": "سبب الإحالة"},
    "policy_checks": {"en": "Policy checks", "ar": "فحوصات السياسة"},
    "candidate_plans": {"en": "Candidate plans", "ar": "الخطط المقترحة"},
    "evidence": {"en": "Evidence", "ar": "الأدلة"},
    "audit": {"en": "Audit trail", "ar": "سجل التدقيق"},
    "proactive": {"en": "Proactive Alerts", "ar": "التنبيهات الاستباقية"},
}

OUTCOME = {
    "UPDATE_INSTALLMENT": {"en": "Update installment", "ar": "تعديل القسط"},
    "TRANSFER_ARREARS": {"en": "Transfer arrears to end", "ar": "ترحيل المتأخرات للنهاية"},
    "MAINTAIN_INSTALLMENT": {"en": "Maintain installment", "ar": "الإبقاء على القسط"},
    "REQUEST_MORE_INFO": {"en": "Request more information", "ar": "طلب مزيد من المعلومات"},
    "REJECT_ACTIVE_REQUEST": {"en": "Reject — active request", "ar": "رفض — طلب نشط"},
    "REFER_TO_OFFICER": {"en": "Refer to officer", "ar": "إحالة إلى الموظف"},
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str) -> str:
    return T.get(key, {}).get(lang(), key)


def outcome_label(code: str | None) -> str:
    if not code:
        return "—"
    return OUTCOME.get(code, {}).get(lang(), code)
