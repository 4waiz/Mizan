"""Officer: case detail — evidence, policy, plans, confidence, escalation, and
the approve / override / reject actions with decision notes."""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import outcome_label, t

ui.setup_page("Officer Case")
ui.sidebar()
ui.band("🧑‍⚖️ Case Review", t("subtitle"))

case_id = st.session_state.get("officer_case_id")
case_id = st.text_input("Case ID", value=case_id or "")
if not case_id:
    st.info("Open a case from the Review Queue.")
    st.stop()

case = api_client.get_case(case_id)
officer_id = st.sidebar.text_input("Officer ID", value="officer-001")

left, right = st.columns([3, 2])

with left:
    ui.profile_card(case)
    ui.decision_badge(case)
    if case.get("escalation_reason"):
        st.warning("**" + t("escalation") + ":** " + case["escalation_reason"])

    st.markdown("#### " + t("candidate_plans"))
    ui.plan_cards(case)

    st.markdown("#### " + t("policy_checks"))
    ui.policy_table(case)

    st.markdown("#### " + t("evidence"))
    for d in case["document_inventory"]["documents"]:
        with st.expander(f"📎 {d['doc_type']} · {d.get('file_name','')}"):
            st.code(d.get("raw_text") or "(no extracted text)")
    ef = case.get("extracted_fields") or {}
    st.caption(f"Extracted: income={ef.get('declared_monthly_income_aed')} · "
               f"employer={ef.get('employer_name')} · "
               f"confidence={ef.get('extraction_confidence')}")
    flags = case.get("fraud_flags", {}).get("flags", [])
    if flags:
        st.error("Fraud flags: " + ", ".join(f"{f['code']} ({f['severity']})" for f in flags))

with right:
    ui.confidence_block(case)
    st.markdown("#### Decision")
    notes = st.text_area(t("notes"), placeholder="Rationale for your decision…")

    if st.button("✅ " + t("approve"), type="primary", use_container_width=True):
        api_client.officer_approve(case_id, officer_id, notes)
        st.success("Approved. Logged to the audit trail.")
        st.rerun()

    with st.expander("✏️ " + t("override")):
        outcomes = ["UPDATE_INSTALLMENT", "TRANSFER_ARREARS", "MAINTAIN_INSTALLMENT",
                    "REQUEST_MORE_INFO", "REJECT_ACTIVE_REQUEST"]
        oc = st.selectbox("New outcome", outcomes, format_func=outcome_label)
        inst = st.number_input("New installment (AED)", min_value=0.0, step=100.0, value=0.0)
        term = st.number_input("New term (months)", min_value=0, step=12, value=0)
        if st.button("Apply override", use_container_width=True):
            api_client.officer_override(case_id, officer_id, oc,
                                        inst or None, int(term) or None, notes)
            st.success("Override applied.")
            st.rerun()

    if st.button("❌ " + t("reject"), use_container_width=True):
        api_client.officer_reject(case_id, officer_id, notes)
        st.error("Rejected. Logged to the audit trail.")
        st.rerun()

    if case.get("officer_decision"):
        od = case["officer_decision"]
        st.info(f"Last action: **{od['action']}** by {od['officer_id']} · "
                f"{od.get('notes') or ''}")

st.divider()
with st.expander("🧾 " + t("audit"), expanded=False):
    audit = api_client.get_audit(case_id)
    ui.audit_timeline(audit["events"])
