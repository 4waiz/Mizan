"""Aggregated insights over the organizer historical arrears dataset.

Everything here is *aggregate* — medians, counts, percentages, risk-bucket
distributions, anonymized pattern exemplars. No raw identifiable record is ever
returned. These functions power the "Historical Intelligence" dashboard and
calibrate the proactive risk layer.

All outputs are plain JSON-serializable dicts so the API can hand them straight
to the frontend.
"""
from __future__ import annotations

import functools
import re
from collections import Counter
from typing import Any

from ..data.organizer_dataset import OrganizerDataset, get_cached_dataset
from ..config import get_settings

# ── risk buckets (organizer overdue-month bands) ─────────────────────────────
# (key, label, min_months, max_months_inclusive_or_None)
RISK_BUCKETS: list[tuple[str, str, int, int | None]] = [
    ("low", "Low", 0, 2),
    ("medium", "Medium", 3, 6),
    ("high", "High", 7, 12),
    ("severe", "Severe", 13, 24),
    ("critical", "Critical", 25, None),
]

# Justification/remark keywords worth surfacing (free-text is noisy; we count
# normalized tokens but also scan for these domain phrases).
_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "by", "with",
    "this", "that", "is", "was", "be", "as", "at", "from", "request", "approved",
    "approve", "due", "no", "not", "has", "have", "had", "will", "are", "were",
    "his", "her", "their", "they", "he", "she", "it", "we", "you", "but", "if",
    "now", "old", "new", "open", "file", "system", "without", "having",
}


def _round(v: Any, n: int = 2):
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:  # NaN
            return None
        return round(f, n)
    except (TypeError, ValueError):
        return None


def _median(series):
    import pandas as pd  # noqa: F401

    s = series.dropna()
    return _round(s.median(), 2) if len(s) else None


def _pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


def _not_loaded_payload(ds: OrganizerDataset) -> dict:
    return {
        "loaded": False,
        "message": ds.message,
        "source_path": ds.source_path,
        "dataset_relative_path": "data/RescheduleArrears.xlsx",
    }


def bucket_for_months(months: float | int | None) -> tuple[str, str] | None:
    """Return (key, label) for an overdue-month count, or None if unknown.

    Buckets are a continuous partition over months ≥ 0: a value lands in a bucket
    if it is ≥ that bucket's lower bound and below the next bucket's lower bound.
    This keeps fractional months (e.g. 2.13) from falling through the cracks
    between integer-labelled bands.
    """
    if months is None:
        return None
    try:
        m = float(months)
    except (TypeError, ValueError):
        return None
    if m < 0:
        return None
    for i, (key, label, lo, _hi) in enumerate(RISK_BUCKETS):
        nxt = RISK_BUCKETS[i + 1][2] if i + 1 < len(RISK_BUCKETS) else None
        if m >= lo and (nxt is None or m < nxt):
            return key, label
    return None


# ── core insights ────────────────────────────────────────────────────────────
def compute_insights(ds: OrganizerDataset | None = None) -> dict:
    """Full aggregated insight object for the dashboard."""
    ds = ds or get_cached_dataset()
    if not ds.loaded:
        return _not_loaded_payload(ds)

    import pandas as pd

    df = ds.dataframe()
    settings = get_settings()
    cap = settings.max_deduction_ratio  # 0.20

    years = sorted({int(y) for y in df["year"].dropna().tolist()})

    # Request-type split (effective).
    rt = df["request_type_effective"].dropna()
    type_counts = rt.value_counts().to_dict()
    request_type_split = {
        str(k): {"count": int(v), "percent": _pct(int(v), len(rt))}
        for k, v in type_counts.items()
    }

    # 20% deduction-cap edge cases.
    cur_ratio = pd.to_numeric(df["current_emi_ratio"], errors="coerce")
    new_ratio = pd.to_numeric(df["new_emi_ratio"], errors="coerce")
    cur_known = cur_ratio.dropna()
    new_known = new_ratio.dropna()
    cur_over = int((cur_known > cap).sum())
    new_over = int((new_known > cap).sum())

    payload = {
        "loaded": True,
        "source_path": ds.source_path,
        "dataset_relative_path": "data/RescheduleArrears.xlsx",
        "message": ds.message,
        "deduction_cap": cap,
        "totals": {
            "raw_records": ds.raw_row_count,
            "usable_records": ds.usable_row_count,
            "dropped_records": ds.dropped_rows,
            "years_covered": years,
            "year_span": f"{years[0]}–{years[-1]}" if years else None,
            "sheets": ds.sheets,
        },
        "medians": {
            "current_salary": _median(pd.to_numeric(df["current_salary"], errors="coerce")),
            "over_due_amt": _median(pd.to_numeric(df["over_due_amt"], errors="coerce")),
            "over_due_months": _median(pd.to_numeric(df["over_due_months"], errors="coerce")),
            "current_emi_amt": _median(pd.to_numeric(df["current_emi_amt"], errors="coerce")),
            "new_emi_amt": _median(pd.to_numeric(df["new_emi_amt"], errors="coerce")),
            "current_emi_ratio": _median(cur_ratio),
            "new_emi_ratio": _median(new_ratio),
            "approval_duration_days": _median(
                pd.to_numeric(df["approval_duration_days"], errors="coerce")
            ),
        },
        "request_type_split": request_type_split,
        "risk_buckets": _risk_bucket_block(df),
        "deduction_cap_edge_cases": {
            "cap_percent": round(cap * 100, 1),
            "current_emi": {
                "evaluated": int(len(cur_known)),
                "over_cap": cur_over,
                "over_cap_percent": _pct(cur_over, len(cur_known)),
            },
            "new_emi": {
                "evaluated": int(len(new_known)),
                "over_cap": new_over,
                "over_cap_percent": _pct(new_over, len(new_known)),
            },
        },
        "approval_duration": _approval_duration_block(df),
        "justification_keywords": _justification_keywords(df),
        "by_year": _by_year_block(df, cap),
    }
    return payload


def _risk_bucket_block(df) -> dict:
    import pandas as pd

    months = pd.to_numeric(df["over_due_months"], errors="coerce")
    known = months.dropna()
    counts: dict[str, dict] = {}
    distribution = []
    for i, (key, label, lo, hi) in enumerate(RISK_BUCKETS):
        nxt = RISK_BUCKETS[i + 1][2] if i + 1 < len(RISK_BUCKETS) else None
        if nxt is None:
            mask = known >= lo
            range_label = f"{lo}+ months"
        else:
            # half-open [lo, nxt) so the partition is continuous over fractions
            mask = (known >= lo) & (known < nxt)
            range_label = f"{lo}–{hi} months"
        n = int(mask.sum())
        counts[key] = {
            "label": label,
            "range": range_label,
            "count": n,
            "percent": _pct(n, len(known)),
        }
        distribution.append({"key": key, "label": label, "range": range_label, "count": n, "percent": _pct(n, len(known))})
    return {
        "evaluated": int(len(known)),
        "definitions": [
            {"key": k, "label": lbl, "min_months": lo, "max_months": hi}
            for k, lbl, lo, hi in RISK_BUCKETS
        ],
        "counts": counts,
        "distribution": distribution,
    }


def _approval_duration_block(df) -> dict:
    import pandas as pd

    d = pd.to_numeric(df["approval_duration_days"], errors="coerce").dropna()
    if not len(d):
        return {"available": False}
    return {
        "available": True,
        "evaluated": int(len(d)),
        "median_days": _median(d),
        "mean_days": _round(d.mean(), 1),
        "p90_days": _round(d.quantile(0.9), 1),
        "manual_baseline_days": 5,  # the ~5-working-day manual review Mizan replaces
    }


def _by_year_block(df, cap: float) -> list[dict]:
    import pandas as pd

    out = []
    for year, g in df.groupby("year"):
        if year is None:
            continue
        cur_ratio = pd.to_numeric(g["current_emi_ratio"], errors="coerce").dropna()
        out.append(
            {
                "year": int(year),
                "records": int(len(g)),
                "median_over_due_months": _median(pd.to_numeric(g["over_due_months"], errors="coerce")),
                "median_over_due_amt": _median(pd.to_numeric(g["over_due_amt"], errors="coerce")),
                "median_salary": _median(pd.to_numeric(g["current_salary"], errors="coerce")),
                "over_cap_percent": _pct(int((cur_ratio > cap).sum()), len(cur_ratio)),
            }
        )
    return sorted(out, key=lambda r: r["year"])


def _justification_keywords(df, top: int = 12) -> list[dict]:
    counter: Counter[str] = Counter()
    for col in ("justifications", "remarks"):
        if col not in df.columns:
            continue
        for val in df[col].dropna().tolist():
            for tok in re.split(r"[^a-zA-Z]+", str(val).lower()):
                if len(tok) >= 3 and tok not in _STOPWORDS:
                    counter[tok] += 1
    total = sum(counter.values()) or 1
    return [
        {"keyword": kw, "count": c, "percent": round(100.0 * c / total, 1)}
        for kw, c in counter.most_common(top)
    ]


# ── focused sub-views the API exposes individually ───────────────────────────
def risk_buckets(ds: OrganizerDataset | None = None) -> dict:
    ds = ds or get_cached_dataset()
    if not ds.loaded:
        return _not_loaded_payload(ds)
    return {"loaded": True, **_risk_bucket_block(ds.dataframe())}


def policy_edge_cases(ds: OrganizerDataset | None = None) -> dict:
    """Aggregate 20%-rule edge-case stats only (no records)."""
    ds = ds or get_cached_dataset()
    if not ds.loaded:
        return _not_loaded_payload(ds)
    full = compute_insights(ds)
    return {
        "loaded": True,
        "deduction_cap": full["deduction_cap"],
        "edge_cases": full["deduction_cap_edge_cases"],
        "explanation": (
            "Each historical case is checked against the 20% deduction cap using "
            "EMI / salary. Cases where the installment exceeds the cap are exactly "
            "the rows that require automated policy enforcement before approval."
        ),
    }


def sample_patterns(ds: OrganizerDataset | None = None, limit: int = 8) -> dict:
    """Anonymized, *bucketed* example patterns — never raw rows.

    Each pattern rounds figures to ranges and strips every identifier so it is
    purely illustrative of a recurring shape in the data.
    """
    ds = ds or get_cached_dataset()
    if not ds.loaded:
        return _not_loaded_payload(ds)

    import pandas as pd

    df = ds.dataframe()
    cap = get_settings().max_deduction_ratio
    patterns: list[dict] = []

    # One representative pattern per (request_type x risk bucket), using medians.
    df = df.copy()
    df["_bucket"] = pd.to_numeric(df["over_due_months"], errors="coerce").map(
        lambda m: (bucket_for_months(m) or ("unknown", "Unknown"))[0]
    )
    grouped = df.groupby(["request_type_effective", "_bucket"])
    rows = []
    for (rtype, bucket), g in grouped:
        if rtype is None or bucket == "unknown" or len(g) < 3:
            continue
        cur_ratio = pd.to_numeric(g["current_emi_ratio"], errors="coerce")
        rows.append(
            {
                "request_type": str(rtype),
                "risk_bucket": bucket,
                "case_count": int(len(g)),
                "salary_band": _band(_median(pd.to_numeric(g["current_salary"], errors="coerce"))),
                "median_overdue_months": _median(pd.to_numeric(g["over_due_months"], errors="coerce")),
                "median_overdue_amount_band": _band(_median(pd.to_numeric(g["over_due_amt"], errors="coerce"))),
                "median_current_emi_ratio": _median(cur_ratio),
                "exceeds_cap_share": _pct(int((cur_ratio.dropna() > cap).sum()), len(cur_ratio.dropna())),
            }
        )
    rows.sort(key=lambda r: r["case_count"], reverse=True)
    patterns = rows[:limit]
    return {
        "loaded": True,
        "note": (
            "Synthetic aggregate patterns derived from historical groups. Figures "
            "are medians within anonymized bands — no individual record is shown."
        ),
        "patterns": patterns,
    }


def _band(value: float | None, width: int = 5000) -> str | None:
    """Bucket a figure into an anonymizing AED band, e.g. '25,000–30,000'."""
    if value is None:
        return None
    lo = int(value // width) * width
    return f"{lo:,}–{lo + width:,}"


@functools.lru_cache(maxsize=1)
def cached_insights() -> dict:
    return compute_insights()


def clear_cache() -> None:
    cached_insights.cache_clear()
