"""Bonus: proactive risk alerts — beneficiaries trending toward arrears."""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("Proactive Alerts")
ui.sidebar()
ui.band("📡 " + t("proactive"), t("subtitle"))

st.write("Cases flagged **before** they fall into serious arrears, ranked by "
         "re-default risk — enabling early officer outreach.")

alerts = api_client.proactive_alerts()
if not alerts:
    st.success("No proactive alerts at present.")
    st.stop()

for a in alerts:
    rp = a["redefault_probability"]
    color = ui.GOV_RED if rp >= 0.6 else ui.GOV_GOLD if rp >= 0.35 else ui.GOV_GREEN
    st.markdown(
        f"<div class='mz-card' style='border-left:6px solid {color}'>"
        f"<b>{a['beneficiary_name_en']}</b> · <code>{a['case_id']}</code><br>"
        f"{t('risk')}: <b style='color:{color}'>{rp:.0%}</b><br>"
        f"<span class='mz-muted'>Drivers: {', '.join(a['drivers'])}</span><br>"
        f"Suggested action: <b>{a['suggested_action']}</b></div>",
        unsafe_allow_html=True,
    )
    if st.button(f"Open case {a['case_id']}", key=a["case_id"]):
        st.session_state["officer_case_id"] = a["case_id"]
        st.switch_page("pages/4_Officer_Case.py")
