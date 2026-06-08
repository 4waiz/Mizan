"""Shared UI helpers: theme, sidebar, and render widgets for the workflow UI.
Deliberately NOT a chat UI — this is a structured, government-style workflow."""
from __future__ import annotations

import streamlit as st

from i18n import outcome_label, t

# Palette inspired by UAE federal government styling.
GOV_GREEN = "#0b7a4b"
GOV_RED = "#b00020"
GOV_GOLD = "#b68a35"
INK = "#1b1b1b"


def setup_page(title: str) -> None:
    st.set_page_config(page_title=f"Mizan · {title}", page_icon="⚖️", layout="wide")
    _inject_css()


def _inject_css() -> None:
    high_contrast = st.session_state.get("high_contrast", False)
    rtl = st.session_state.get("lang", "en") == "ar"
    bg = "#ffffff" if not high_contrast else "#000000"
    fg = INK if not high_contrast else "#ffffff"
    card_bg = "#f6f8f7" if not high_contrast else "#111111"
    border = "#d8e0dc" if not high_contrast else "#ffffff"
    direction = "rtl" if rtl else "ltr"
    st.markdown(
        f"""
        <style>
        .stApp {{ background:{bg}; color:{fg}; direction:{direction}; }}
        .mz-band {{ background:{GOV_GREEN}; color:#fff; padding:14px 18px; border-radius:10px;
                    margin-bottom:14px; }}
        .mz-band h1 {{ margin:0; font-size:1.35rem; }}
        .mz-band p {{ margin:2px 0 0; opacity:.9; font-size:.85rem; }}
        .mz-card {{ background:{card_bg}; border:1px solid {border}; border-radius:10px;
                    padding:14px 16px; margin-bottom:10px; }}
        .mz-pill {{ display:inline-block; padding:3px 12px; border-radius:999px; font-weight:600;
                    font-size:.8rem; color:#fff; }}
        .mz-kv {{ font-size:.9rem; }}
        .mz-kv b {{ color:{GOV_GREEN}; }}
        .mz-muted {{ color:#6b7670; font-size:.8rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> dict:
    with st.sidebar:
        st.markdown("### ⚖️ Mizan / ميزان")
        lang = st.radio("Language / اللغة", ["en", "ar"],
                        format_func=lambda x: "English" if x == "en" else "العربية",
                        horizontal=True, key="lang")
        st.checkbox("High-contrast mode", key="high_contrast")
        st.divider()
        try:
            import api_client
            h = api_client.health()
            st.success(f"Backend ✓ · engine: {h['engine']} · LLM: {h['llm_provider']}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Backend unreachable.\n{exc}")
        st.caption("Synthetic data only. No real identifiers.")
    return {"lang": lang}


def band(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<div class='mz-band'><h1>{title}</h1>"
        + (f"<p>{subtitle}</p>" if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


_STATUS_COLOR = {
    "auto_approved": GOV_GREEN, "officer_approved": GOV_GREEN,
    "pending_human_review": GOV_GOLD, "info_requested": GOV_GOLD,
    "rejected": GOV_RED, "officer_rejected": GOV_RED, "officer_overridden": "#2456b3",
    "processing": "#555", "intake": "#555",
}


def status_pill(status: str) -> None:
    color = _STATUS_COLOR.get(status, "#555")
    st.markdown(
        f"<span class='mz-pill' style='background:{color}'>{status.replace('_', ' ').upper()}</span>",
        unsafe_allow_html=True,
    )


def decision_badge(case: dict) -> None:
    rec = case.get("recommendation") or {}
    outcome = rec.get("outcome_type")
    review = case.get("needs_human_review")
    color = GOV_GOLD if review else GOV_GREEN
    label = outcome_label(outcome)
    st.markdown(
        f"<div class='mz-card' style='border-left:6px solid {color}'>"
        f"<div class='mz-muted'>{t('recommendation')}</div>"
        f"<div style='font-size:1.4rem;font-weight:700;color:{color}'>{label}</div>"
        f"<div class='mz-kv'>{rec.get('decision_label_ar','')}</div>"
        + (f"<div class='mz-muted'>⚠ {case.get('escalation_reason','')}</div>" if review
           else "<div class='mz-muted'>✓ Straight-through (auto-issued)</div>")
        + "</div>",
        unsafe_allow_html=True,
    )


def profile_card(case: dict) -> None:
    b = case.get("beneficiary") or {}
    loan = case.get("loan") or {}
    arr = case.get("arrears") or {}
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**{b.get('full_name_en','—')}** · {b.get('full_name_ar','')}")
        st.caption(f"{b.get('emirates_id_masked','')} · {b.get('emirate','')}")
        st.caption(f"{b.get('employment_status','')} · {b.get('employer_name') or '—'}")
    with c2:
        st.metric(t("income"), f"AED {b.get('monthly_income_aed',0):,.0f}")
        st.metric(t("installment"), f"AED {loan.get('current_installment_aed',0):,.0f}")
    with c3:
        st.metric(t("arrears"), f"AED {arr.get('arrears_amount_aed',0):,.0f}")
        st.metric("Hardship", b.get("hardship_type", "none"))


_RESULT_ICON = {"pass": "✅", "fail": "❌", "warn": "⚠️", "not_applicable": "➖"}


def policy_table(case: dict) -> None:
    rows = case.get("policy_checks") or []
    if not rows:
        st.info("No policy checks recorded.")
        return
    for c in rows:
        st.markdown(
            f"<div class='mz-kv'>{_RESULT_ICON.get(c['result'],'')} "
            f"<b>{c['rule_id']}</b> — {c['title']}<br>"
            f"<span class='mz-muted'>{c['detail']}</span></div>",
            unsafe_allow_html=True,
        )


def plan_cards(case: dict) -> None:
    plans = case.get("candidate_plans") or []
    selected = ((case.get("recommendation") or {}).get("selected_plan") or {}).get("outcome_type")
    for p in plans:
        valid = p.get("is_valid")
        chosen = p.get("outcome_type") == selected
        border = GOV_GREEN if chosen else ("#cfd8d3" if valid else GOV_RED)
        tag = "★ SELECTED" if chosen else ("valid" if valid else "filtered out")
        inst = p.get("new_installment_aed")
        ratio = p.get("deduction_ratio")
        st.markdown(
            f"<div class='mz-card' style='border-left:6px solid {border}'>"
            f"<b>{outcome_label(p.get('outcome_type'))}</b> "
            f"<span class='mz-muted'>· {tag}</span><br>"
            + (f"Installment <b>AED {inst:,.0f}</b> · {ratio:.0%} of income · "
               f"{p.get('new_term_months','—')} months<br>" if inst else "")
            + f"<span class='mz-muted'>{p.get('rationale','')}</span>"
            + (f"<br><span style='color:{GOV_RED}'>Violated: {', '.join(p.get('violated_rule_ids',[]))}</span>"
               if p.get("violated_rule_ids") else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def confidence_block(case: dict) -> None:
    conf = case.get("confidence") or {}
    risk = case.get("risk") or {}
    c1, c2 = st.columns(2)
    with c1:
        v = conf.get("value", 0)
        st.metric(t("confidence"), f"{v:.0%}", conf.get("band", ""))
        st.progress(min(max(v, 0.0), 1.0))
        st.caption(" · ".join(conf.get("reasons", [])))
    with c2:
        rp = risk.get("redefault_probability", 0)
        st.metric(t("risk"), f"{rp:.0%}", risk.get("band", ""))
        st.caption("Drivers: " + ", ".join(risk.get("drivers", [])))


def memo_block(case: dict) -> None:
    memo = case.get("rationale_memo") or {}
    if not memo:
        return
    with st.expander("📄 " + t("recommendation") + " memo (EN / AR)", expanded=True):
        st.markdown(f"**{memo.get('title_en','')}**")
        st.write(memo.get("body_en", ""))
        st.markdown(f"<div dir='rtl'><b>{memo.get('title_ar','')}</b><br>"
                    f"{memo.get('body_ar','')}</div>", unsafe_allow_html=True)


def audit_timeline(events: list[dict]) -> None:
    for e in events:
        rid = (", ".join(e.get("rule_ids", []))) or ""
        st.markdown(
            f"<div class='mz-kv'>🕒 <span class='mz-muted'>{e['timestamp'][11:19]}</span> · "
            f"<b>{e.get('node') or e['event_type']}</b> — {e['message']}"
            + (f" <span class='mz-muted'>[{rid}]</span>" if rid else "")
            + "</div>",
            unsafe_allow_html=True,
        )
