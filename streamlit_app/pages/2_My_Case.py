"""Beneficiary: case status tracker + recommendation result + explanation."""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("My Case")
ui.sidebar()
ui.band(t("status"), t("subtitle"))

case_id = st.session_state.get("last_run_case_id") or st.session_state.get("active_case_id")
case_id = st.text_input("Case ID", value=case_id or "")
if not case_id:
    st.info("Submit a request first, or paste a case ID.")
    st.stop()

try:
    case = api_client.get_case(case_id)
except Exception as exc:  # noqa: BLE001
    st.error(str(exc))
    st.stop()

col1, col2 = st.columns([2, 1])
with col1:
    ui.profile_card(case)
with col2:
    st.markdown("**" + t("status") + "**")
    ui.status_pill(case["status"])
    sla = case.get("sla") or {}
    if sla.get("processing_ms") is not None:
        st.caption(f"Decided in {sla['processing_ms']:.0f} ms "
                   f"(legacy SLA: {sla.get('legacy_sla_working_days', 5)} working days).")

st.divider()
ui.decision_badge(case)
ui.confidence_block(case)

st.markdown("#### " + t("candidate_plans"))
ui.plan_cards(case)

st.markdown("#### " + t("validation"))
ui.policy_table(case)

ui.memo_block(case)

with st.expander("🧾 " + t("audit")):
    audit = api_client.get_audit(case_id)
    ui.audit_timeline(audit["events"])
