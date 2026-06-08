"""Beneficiary: start a new rescheduling request.

Workflow steps: confirm auto-filled profile -> confirm documents on file ->
submit (intake) -> run assessment -> see the validation + recommendation.
"""
from __future__ import annotations

import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("New Request")
ui.sidebar()
ui.band(t("new_request"), t("subtitle"))

fixture = st.session_state.get("logged_in_fixture")
if not fixture:
    st.warning("Please sign in on the Home page first.")
    st.stop()

# Build a preview case (intake) so we can show the auto-filled profile + docs.
if st.session_state.get("active_fixture") != fixture:
    res = api_client.intake(fixture_id=fixture, trigger_type="application")
    st.session_state["active_case_id"] = res["case_id"]
    st.session_state["active_fixture"] = fixture
case_id = st.session_state["active_case_id"]
case = api_client.get_case(case_id)

st.markdown("#### 1 · " + t("profile"))
st.caption("Auto-filled from UAE PASS and MOEI records.")
ui.profile_card(case)

st.markdown("#### 2 · " + t("documents"))
docs = case["document_inventory"]["documents"]
if docs:
    for d in docs:
        st.markdown(f"- 📎 **{d['doc_type']}** · {d.get('file_name','')} "
                    f"· issued {d.get('issued_on','—')} · `{d['status']}`")
else:
    st.write("No documents on file.")
st.caption("In production these are uploaded via the portal; here they are mocked "
           "in the document store.")

st.markdown("#### 3 · Submit & assess")
st.write("Submitting runs the governed pipeline: document audit → fraud/dedupe → "
         "affordability → risk → policy solver → human-review gate.")

if st.button("▶ " + t("run"), type="primary"):
    with st.spinner("Assessing against Sheikh Zayed Housing Programme policy…"):
        run = api_client.run_case(case_id)
    st.session_state["last_run_case_id"] = case_id
    st.success("Assessment complete.")
    proc = (run["case"].get("sla") or {}).get("processing_ms")
    st.metric("Processing time", f"{proc:.0f} ms" if proc is not None else "—",
              "vs. 5 working days manually")
    ui.decision_badge(run["case"])
    st.markdown("##### " + t("validation"))
    ui.policy_table(run["case"])
    st.page_link("pages/2_My_Case.py", label="➡ View full result on **My Case**", icon="📄")
