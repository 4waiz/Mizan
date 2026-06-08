"""Mizan home — mock UAE PASS login + role selection.

This is the entry of a WORKFLOW app (not a chatbot). From here a beneficiary
starts a rescheduling request, or an officer opens the review queue.
"""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("Home")
ui.sidebar()
ui.band(t("app_title"), t("subtitle"))

st.write(
    "An autonomous case officer that turns the manual **5-working-day** arrears "
    "rescheduling review into an **instant, explainable, auditable** decision — "
    "and escalates only the exceptional cases to a human."
)

# ── Mock UAE PASS login ───────────────────────────────────────────────────────
st.subheader("🔐 " + t("login"))
try:
    fixtures = api_client.list_fixtures()
except Exception as exc:  # noqa: BLE001
    st.error(f"Cannot reach the backend at {api_client.BASE_URL}. Start it with "
             f"`make backend`.\n\n{exc}")
    st.stop()

applicant_fixtures = [f for f in fixtures if f["trigger_type"] == "application"]
labels = {f["fixture_id"]: f"{f['name_en']} · {f['beneficiary_id']} ({f['fixture_id']})"
          for f in fixtures}

col1, col2 = st.columns([3, 2])
with col1:
    choice = st.selectbox(
        "Select a citizen identity to sign in as (synthetic UAE PASS):",
        options=[f["fixture_id"] for f in applicant_fixtures],
        format_func=lambda x: labels.get(x, x),
    )
    note = next((f["note"] for f in fixtures if f["fixture_id"] == choice), "")
    st.caption(note)
with col2:
    if st.button("🆔 " + t("login"), type="primary", use_container_width=True):
        sel = next(f for f in fixtures if f["fixture_id"] == choice)
        st.session_state["logged_in_fixture"] = choice
        st.session_state["logged_in_beneficiary"] = sel["beneficiary_id"]
        st.session_state["logged_in_name"] = sel["name_en"]
        st.success(f"Signed in as {sel['name_en']}.")

if st.session_state.get("logged_in_name"):
    st.info(f"✅ Signed in as **{st.session_state['logged_in_name']}**. "
            f"Open **New Request** in the sidebar to begin.")

st.divider()
c1, c2, c3 = st.columns(3)
c1.markdown("#### 👤 Beneficiary\n- New Request\n- My Case (status + result)")
c2.markdown("#### 🧑‍⚖️ Officer\n- Review Queue\n- Case detail + actions")
c3.markdown("#### 📊 Insight\n- Proactive Alerts\n- Replay Dashboard")

st.caption("Use the page navigation in the left sidebar. Toggle language (EN/AR) "
           "and high-contrast mode there too.")
