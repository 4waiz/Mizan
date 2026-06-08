"""Insight: masked historical replay — consistency + time saved at a glance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import api_client
import components as ui

ui.setup_page("Replay Dashboard")
ui.sidebar()
ui.band("📊 Replay Dashboard", "Consistency & impact across all synthetic cases")

s = api_client.replay_summary()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total cases", s["total_cases"])
c2.metric("Straight-through", s["straight_through"], f"{s['straight_through_rate']:.0%}")
c3.metric("Human review", s["human_review"])
c4.metric("Manual days saved", s["estimated_manual_working_days_saved"])

st.caption(f"Average automated processing time: {s['avg_processing_ms']:.0f} ms "
           f"· legacy SLA: {s['legacy_sla_working_days']} working days per case.")

st.markdown("#### Outcomes")
st.bar_chart(pd.Series(s["by_outcome"], name="cases"))

st.markdown("#### Cases")
df = pd.DataFrame(s["cases"])
st.dataframe(df, use_container_width=True, hide_index=True)
