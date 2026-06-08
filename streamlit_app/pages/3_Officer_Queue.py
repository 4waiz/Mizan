"""Officer: queue of exceptional cases awaiting human review."""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("Officer Queue")
ui.sidebar()
ui.band("🧑‍⚖️ " + t("queue"), t("subtitle"))

queue = api_client.officer_queue()
st.caption(f"{len(queue)} case(s) escalated for human review.")

if not queue:
    st.success("Queue is empty — all recent cases were handled straight-through.")
    st.stop()

for item in queue:
    with st.container():
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.markdown(f"**{item['beneficiary_name_en']}**  \n`{item['case_id']}`")
        c2.metric(t("arrears"), f"AED {item.get('arrears_amount_aed') or 0:,.0f}")
        conf = item.get("confidence")
        c3.metric(t("confidence"), f"{conf:.0%}" if conf is not None else "—")
        with c4:
            if st.button("Open ➡", key=item["case_id"], use_container_width=True):
                st.session_state["officer_case_id"] = item["case_id"]
                st.switch_page("pages/4_Officer_Case.py")
        st.caption("⚠ " + (item.get("escalation_reason") or ""))
        st.divider()
