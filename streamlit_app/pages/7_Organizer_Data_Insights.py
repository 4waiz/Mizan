"""Insight: organizer data insights — historical arrears-rescheduling patterns.

Aggregated/anonymized view over the organizer dataset (data/RescheduleArrears.xlsx)
used to calibrate proactive risk scoring and validate policy edge cases.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import api_client
import components as ui
from i18n import t

ui.setup_page("Organizer Data Insights")
ui.sidebar()
ui.band("Organizer Data Insights", t("subtitle"))

st.write(
    "Aggregated, anonymized patterns from the historical arrears-rescheduling "
    "dataset — used to calibrate Mizan's proactive risk scoring and to validate "
    "policy edge cases against real operational volume."
)

# ── Load insights ─────────────────────────────────────────────────────────────
try:
    data = api_client.organizer_insights()
except api_client.ApiError as exc:
    st.error(
        f"Could not load organizer insights from the backend.\n\n{exc}\n\n"
        "Hint: start the backend (e.g. `make backend`) and retry."
    )
    st.stop()

if not data.get("loaded", False):
    st.info(
        data.get(
            "message",
            "Organizer dataset not found. Place the Excel file at "
            "`data/RescheduleArrears.xlsx` and restart the backend.",
        )
    )
    st.stop()

totals = data.get("totals", {}) or {}
medians = data.get("medians", {}) or {}


def _num(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


# ── KPI cards ─────────────────────────────────────────────────────────────────
st.markdown("#### Overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total historical cases", _num(totals.get("raw_records")))
k2.metric("Usable records", _num(totals.get("usable_records")))
k3.metric("Years covered", totals.get("year_span", "—"))
k4.metric("Median overdue amount", f"AED {_num(medians.get('over_due_amt'))}")

k5, k6, k7, _ = st.columns(4)
k5.metric("Median overdue months", _num(medians.get("over_due_months")))
k6.metric("Median salary", f"AED {_num(medians.get('current_salary'))}")
k7.metric("Median current installment", f"AED {_num(medians.get('current_emi_amt'))}")

st.divider()

# ── Request-type split ────────────────────────────────────────────────────────
st.markdown("#### Request-type split")
split = data.get("request_type_split", {}) or {}
if split:
    split_df = pd.DataFrame(
        [
            {
                "Request type": rtype,
                "Count": info.get("count", 0),
                "Percent": info.get("percent", 0),
            }
            for rtype, info in split.items()
        ]
    )
    sc1, sc2 = st.columns([2, 3])
    with sc1:
        st.dataframe(split_df, use_container_width=True, hide_index=True)
    with sc2:
        st.bar_chart(split_df.set_index("Request type")["Count"])
else:
    st.caption("No request-type breakdown available.")

st.divider()

# ── Overdue-month risk buckets ────────────────────────────────────────────────
st.markdown("#### Overdue-month risk buckets")
st.caption("How many historical cases fall into each overdue-severity band.")
risk_buckets = data.get("risk_buckets", {}) or {}
distribution = risk_buckets.get("distribution", []) or []
if distribution:
    buckets_df = pd.DataFrame(
        [{"label": b.get("label", b.get("key", "")), "count": b.get("count", 0)}
         for b in distribution]
    )
    st.bar_chart(buckets_df.set_index("label")["count"])
else:
    st.caption("No risk-bucket distribution available.")

st.divider()

# ── 20% deduction-cap edge cases ──────────────────────────────────────────────
st.markdown("#### 20% deduction-cap edge cases")
edge = data.get("deduction_cap_edge_cases", {}) or {}
cap_percent = edge.get("cap_percent", round(data.get("deduction_cap", 0.2) * 100, 1))
st.write(
    f"Policy caps a beneficiary's installment at **{cap_percent:.0f}% of salary**. "
    "These shares show how often historical installments breach that cap — the "
    "exact edge cases Mizan's policy engine must catch."
)
current_emi = edge.get("current_emi", {}) or {}
new_emi = edge.get("new_emi", {}) or {}
e1, e2 = st.columns(2)
e1.metric(
    "Current EMI over cap",
    f"{current_emi.get('over_cap_percent', 0):.1f}%",
    help=f"{_num(current_emi.get('over_cap'))} of "
         f"{_num(current_emi.get('evaluated'))} evaluated cases exceed the cap.",
)
e2.metric(
    "New EMI over cap",
    f"{new_emi.get('over_cap_percent', 0):.1f}%",
    help=f"{_num(new_emi.get('over_cap'))} of "
         f"{_num(new_emi.get('evaluated'))} evaluated cases exceed the cap.",
)

st.divider()

# ── Proactive scan ────────────────────────────────────────────────────────────
st.markdown("#### Proactive risk scan")
st.write(
    "Anonymized cohorts ranked by modeled risk — illustrating where earlier "
    "intervention would have been warranted."
)
try:
    scan = api_client.proactive_scan()
except api_client.ApiError as exc:
    st.error(
        f"Could not run the proactive scan.\n\n{exc}\n\n"
        "Hint: start the backend (e.g. `make backend`) and retry."
    )
    scan = None

if scan is not None:
    if not scan.get("loaded", False):
        st.info(scan.get("message", "Proactive scan unavailable for this dataset."))
    else:
        patterns = scan.get("patterns", []) or []
        if patterns:
            st.dataframe(
                pd.DataFrame(patterns), use_container_width=True, hide_index=True
            )
        else:
            st.caption("No proactive-scan patterns to display.")
        disclaimer = scan.get("disclaimer")
        model = scan.get("model")
        if disclaimer or model:
            parts = [p for p in (f"Model: {model}" if model else None, disclaimer) if p]
            st.caption(" · ".join(parts))

st.divider()

# ── What this proves ──────────────────────────────────────────────────────────
st.info(
    "The organizer dataset shows that arrears rescheduling is a recurring "
    "operational workflow, not a rare case. Mizan uses these historical patterns "
    "to calibrate proactive risk scoring, validate policy edge cases, and "
    "demonstrate earlier intervention before arrears become severe."
)

st.caption(
    "All figures are aggregated and anonymized. No raw citizen records are "
    "displayed — only counts, medians, banded ranges, and modeled cohorts."
)
