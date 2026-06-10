"""Transparent, organizer-calibrated arrears-risk scoring (MVP).

This is **not** a production ML credit model. It is a transparent, fully
explainable scoring layer whose thresholds are *calibrated against the organizer
historical dataset* (``data/RescheduleArrears.xlsx``, 2023–2025). Every point a
profile earns maps to a named reason, so an officer can read exactly why a case
scored the way it did.

Two entry points:
  * :func:`score_profile` — score one arbitrary profile dict (used by the
    proactive scan and reusable by the live pipeline).
  * :func:`proactive_scan` — run scoring across the cleaned organizer rows and
    return the top anonymized high-risk *patterns* (no raw records).

An optional scikit-learn baseline (:func:`train_baseline`) is provided for
completeness, deriving a weak "severity" target from overdue months. It is only
illustrative; the deterministic score remains the source of truth so output is
reproducible with or without sklearn.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings
from ..data.organizer_dataset import OrganizerDataset, get_cached_dataset

# Score band thresholds (0–100).
_BANDS = [
    (80, "Critical"),
    (60, "Severe"),
    (40, "High"),
    (20, "Medium"),
    (0, "Low"),
]

# Recommended intervention per band — escalating response.
_INTERVENTION = {
    "Low": "Monitor",
    "Medium": "Send early warning",
    "High": "Pre-fill rescheduling option",
    "Severe": "Human review",
    "Critical": "Urgent collection-risk review",
}

# Justification keywords that, when present, signal elevated hardship/risk.
_RISK_KEYWORDS = {
    "delay", "delayed", "default", "unemploy", "termination", "terminated",
    "medical", "hardship", "unable", "difficult", "hospital", "death",
    "deceased", "salary stopped", "no income", "loss", "reduced",
}


@dataclass
class RiskAssessment:
    score: int
    label: str
    reasons: list[str]
    recommended_intervention: str
    features: dict[str, Any] = field(default_factory=dict)
    model: str = "organizer-calibrated-deterministic-v1"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "label": self.label,
            "reasons": self.reasons,
            "recommended_intervention": self.recommended_intervention,
            "features": self.features,
            "model": self.model,
        }


def _band(score: float) -> str:
    for threshold, label in _BANDS:
        if score >= threshold:
            return label
    return "Low"


def _num(v: Any) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def score_profile(
    profile: dict[str, Any],
    *,
    cap: float | None = None,
) -> RiskAssessment:
    """Score a single profile.

    Accepts flexible keys (canonical organizer names or friendly aliases):
      overdue_months / over_due_months, overdue_amount / over_due_amt,
      current_emi_ratio, new_emi_ratio, current_emi_amt + current_salary,
      salary / current_salary, request_type / request_type_effective,
      justifications / remarks (free text), missed_payments.
    """
    if cap is None:
        cap = get_settings().max_deduction_ratio

    g = profile.get
    overdue_months = _num(g("overdue_months") or g("over_due_months"))
    overdue_amount = _num(g("overdue_amount") or g("over_due_amt"))
    salary = _num(g("salary") or g("current_salary"))
    cur_ratio = _num(g("current_emi_ratio"))
    new_ratio = _num(g("new_emi_ratio"))
    cur_emi = _num(g("current_emi_amt"))
    if cur_ratio is None and cur_emi is not None and salary:
        cur_ratio = cur_emi / salary
    request_type = (g("request_type") or g("request_type_effective") or "") or ""
    text = " ".join(
        str(g(k) or "") for k in ("justifications", "remarks", "notes")
    ).lower()
    missed = _num(g("missed_payments"))

    score = 0.0
    reasons: list[str] = []

    # 1) Overdue months — dominant driver (calibrated to organizer bucket bands).
    if overdue_months is not None:
        if overdue_months >= 25:
            score += 45
            reasons.append(f"{int(overdue_months)} months overdue (critical band, 25+)")
        elif overdue_months >= 13:
            score += 34
            reasons.append(f"{int(overdue_months)} months overdue (severe band, 13–24)")
        elif overdue_months >= 7:
            score += 22
            reasons.append(f"{int(overdue_months)} months overdue (high band, 7–12)")
        elif overdue_months >= 3:
            score += 12
            reasons.append(f"{int(overdue_months)} months overdue (medium band, 3–6)")
        else:
            reasons.append(f"{int(overdue_months)} months overdue (low band, 0–2)")

    # 2) Overdue amount relative to the dataset median (~AED 43k).
    if overdue_amount is not None:
        if overdue_amount >= 120_000:
            score += 16
            reasons.append("very large arrears balance (≥AED 120k)")
        elif overdue_amount >= 60_000:
            score += 10
            reasons.append("large arrears balance (≥AED 60k)")
        elif overdue_amount >= 43_000:
            score += 5
            reasons.append("arrears above the historical median")

    # 3) Current deduction vs the 20% policy cap.
    if cur_ratio is not None:
        if cur_ratio > cap:
            score += 18
            reasons.append(f"current installment {cur_ratio:.0%} of salary exceeds the {cap:.0%} cap")
        elif cur_ratio > cap * 0.75:
            score += 8
            reasons.append(f"current installment {cur_ratio:.0%} of salary nears the {cap:.0%} cap")

    # 4) Proposed new installment still over cap (rescheduling won't be enough).
    if new_ratio is not None and new_ratio > cap:
        score += 8
        reasons.append(f"proposed installment {new_ratio:.0%} still exceeds the cap")

    # 5) Low salary amplifies burden.
    if salary is not None and salary < 15_000:
        score += 6
        reasons.append("below-median household salary")

    # 6) Transfer-arrears requests historically correlate with deeper distress.
    if str(request_type).upper() == "TRANSFER_ARREARS":
        score += 6
        reasons.append("transfer-arrears request type (deeper-distress pattern)")

    # 7) Free-text hardship signals.
    hit = sorted({kw for kw in _RISK_KEYWORDS if kw in text})
    if hit:
        score += min(10, 4 * len(hit))
        reasons.append("hardship keywords in justification: " + ", ".join(hit[:3]))

    # 8) Repeated missed payments, if tracked.
    if missed is not None and missed >= 3:
        score += 6
        reasons.append(f"{int(missed)} recent missed payments")

    score = int(max(0, min(100, round(score))))
    label = _band(score)
    if not reasons:
        reasons.append("no elevated-risk signals in the available fields")

    return RiskAssessment(
        score=score,
        label=label,
        reasons=reasons,
        recommended_intervention=_INTERVENTION[label],
        features={
            "overdue_months": overdue_months,
            "overdue_amount": overdue_amount,
            "current_emi_ratio": round(cur_ratio, 4) if cur_ratio is not None else None,
            "new_emi_ratio": round(new_ratio, 4) if new_ratio is not None else None,
            "salary": salary,
            "request_type": str(request_type) or None,
        },
    )


def _anonymize_pattern(rows, cap: float) -> dict:
    """Collapse a group of high-risk rows into one anonymized pattern card."""
    import pandas as pd

    df = pd.DataFrame(rows)
    scores = [r["_score"] for r in rows]

    def med(col):
        s = pd.to_numeric(df.get(col), errors="coerce").dropna()
        return round(float(s.median()), 2) if len(s) else None

    salary_med = med("current_salary")
    overdue_amt_med = med("over_due_amt")
    return {
        "request_type": str(df["request_type_effective"].dropna().mode().iloc[0])
        if df["request_type_effective"].notna().any()
        else None,
        "risk_label": rows[0]["_label"],
        "case_count": len(rows),
        "median_score": int(round(sum(scores) / len(scores))),
        "median_overdue_months": med("over_due_months"),
        "salary_band": _band_str(salary_med),
        "overdue_amount_band": _band_str(overdue_amt_med),
        "exceeds_cap_share": round(
            100.0
            * sum(1 for r in rows if (r.get("current_emi_ratio") or 0) > cap)
            / len(rows),
            1,
        ),
        "recommended_intervention": _INTERVENTION[rows[0]["_label"]],
        "top_reason": rows[0]["_top_reason"],
    }


def _band_str(value: float | None, width: int = 5000) -> str | None:
    if value is None:
        return None
    lo = int(value // width) * width
    return f"{lo:,}–{lo + width:,}"


def proactive_scan(
    ds: OrganizerDataset | None = None,
    *,
    top: int = 10,
    min_score: int = 60,
) -> dict:
    """Score every usable organizer row, then return the highest-risk
    *anonymized patterns* (grouped by request type + band). No raw records."""
    ds = ds or get_cached_dataset()
    if not ds.loaded:
        return {
            "loaded": False,
            "message": ds.message,
            "source_path": ds.source_path,
            "dataset_relative_path": "data/RescheduleArrears.xlsx",
        }

    cap = get_settings().max_deduction_ratio
    scored: list[dict] = []
    band_counts: dict[str, int] = {label: 0 for _, label in _BANDS}

    for rec in ds.records:
        a = score_profile(rec, cap=cap)
        band_counts[a.label] = band_counts.get(a.label, 0) + 1
        if a.score >= min_score:
            scored.append(
                {
                    **rec,
                    "_score": a.score,
                    "_label": a.label,
                    "_top_reason": a.reasons[0] if a.reasons else "",
                }
            )

    # Group high-risk rows into anonymized patterns.
    import pandas as pd

    patterns: list[dict] = []
    if scored:
        sdf = pd.DataFrame(scored)
        sdf["_grp_type"] = sdf["request_type_effective"].fillna("UNKNOWN")
        for (_, _), idx in sdf.groupby(["_grp_type", "_label"]).groups.items():
            group_rows = [scored[i] for i in idx]
            if len(group_rows) >= 3:
                patterns.append(_anonymize_pattern(group_rows, cap))
        patterns.sort(key=lambda p: (p["median_score"], p["case_count"]), reverse=True)

    total = sum(band_counts.values()) or 1
    return {
        "loaded": True,
        "model": "organizer-calibrated-deterministic-v1",
        "disclaimer": (
            "Transparent, deterministic risk-calibration layer (MVP) — not a "
            "production ML credit model. Thresholds are calibrated on the "
            "organizer 2023–2025 historical dataset; every score maps to named "
            "reasons. Final eligibility is always decided by the deterministic "
            "policy engine, not by this score."
        ),
        "evaluated": int(total),
        "min_score": min_score,
        "band_distribution": {
            label: {"count": c, "percent": round(100.0 * c / total, 1)}
            for label, c in band_counts.items()
        },
        "high_risk_count": len(scored),
        "patterns": patterns[:top],
    }


# ── optional sklearn baseline (illustrative only) ────────────────────────────
@functools.lru_cache(maxsize=1)
def train_baseline():
    """Fit a tiny LogisticRegression predicting "severe arrears" (overdue ≥ 13
    months) from a few numeric features. Returns (model, feature_names) or None
    if sklearn/data is unavailable. Deterministic; illustrative, not used for the
    headline score."""
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
    except Exception:
        return None

    ds = get_cached_dataset()
    if not ds.loaded:
        return None

    import pandas as pd

    df = ds.dataframe()
    feats = ["current_salary", "over_due_amt", "over_due_months", "current_emi_ratio"]
    X = df[feats].apply(pd.to_numeric, errors="coerce")
    y = (pd.to_numeric(df["over_due_months"], errors="coerce") >= 13).astype(int)
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]
    if len(X) < 50 or y.nunique() < 2:
        return None
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X.to_numpy(dtype=float), y.to_numpy())
    return clf, feats
