"""Ingestion for the organizer-provided historical arrears dataset.

The hackathon organizers shipped ``data/RescheduleArrears.xlsx`` — the official
historical record of housing-loan arrears rescheduling requests for 2023, 2024
and 2025 (one worksheet per year, ~2,150 rows). This module loads it defensively
and returns a single clean, normalized table that the insights / risk layers
build on.

Design goals:
  * Never crash if the file is missing or unreadable — return a clearly-flagged
    "not loaded" :class:`OrganizerDataset` so the API degrades gracefully.
  * Tolerate column drift between sheets (the 2025 sheet drops ``REQUEST_TYPE``
    and ``APPLICANT`` and adds ``CREATED_BY``). Column matching is fuzzy so the
    pipeline keeps working if the organizers tweak headers.
  * Derive a single canonical schema regardless of which year a row came from.

Privacy: identifier-ish columns (names, application/agreement/customer ids) are
*dropped during load* — they never enter the cleaned frame, so nothing
downstream can leak them.
"""
from __future__ import annotations

import functools
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("mizan.organizer_dataset")

# Repo-root-relative location the docs and CLI advertise.
DATASET_RELATIVE_PATH = "data/RescheduleArrears.xlsx"

# ── canonical schema ─────────────────────────────────────────────────────────
# Canonical column -> list of accepted source-header variants (case/space/
# underscore-insensitive; matched as normalized tokens). The first variant is
# the canonical organizer header.
_COLUMN_ALIASES: dict[str, list[str]] = {
    "current_salary": ["current_salary", "salary", "monthly_salary", "income"],
    "over_due_amt": ["over_due_amt", "overdue_amt", "overdue_amount", "arrears_amount", "over_due_amount"],
    "over_due_months": ["over_due_months", "overdue_months", "arrears_months", "months_overdue"],
    "current_emi_amt": ["current_emi_amt", "current_emi", "current_installment", "current_emi_amount"],
    "new_emi_amt": ["new_emi_amt", "new_emi", "new_installment", "new_emi_amount"],
    "new_emi_applicable_months": ["new_emi_applicable_months", "new_emi_months", "emi_applicable_months"],
    "request_type": ["request_type", "requesttype"],
    "approved_request_type": ["approved_request_type", "approvedrequesttype", "approved_type"],
    "deduct_from_salary": ["deduct_from_salary", "deductfromsalary", "salary_deduction"],
    "until_loan_end": ["until_loan_end", "untilloanend", "to_loan_end"],
    "status": ["status", "request_status"],
    "created_date": ["created_date", "request_date", "createddate", "createdon"],
    "approved_date": ["approved_date", "approval_date", "approveddate"],
    "justifications": ["justifications", "justification", "reason"],
    "remarks": ["remarks", "remark", "notes"],
    "additional_months": ["additional_months", "additionalmonths", "extra_months"],
    "additional_premium": ["additional_premium", "additionalpremium"],
    "start_month": ["start_month", "startmonth"],
    "start_year": ["start_year", "startyear"],
}

# Numeric canonical columns to coerce + range-clean.
_NUMERIC_COLUMNS = [
    "current_salary",
    "over_due_amt",
    "over_due_months",
    "current_emi_amt",
    "new_emi_amt",
    "new_emi_applicable_months",
    "additional_months",
    "additional_premium",
    "start_month",
    "start_year",
]
_DATE_COLUMNS = ["created_date", "approved_date"]
_TEXT_COLUMNS = [
    "request_type",
    "approved_request_type",
    "deduct_from_salary",
    "until_loan_end",
    "status",
    "justifications",
    "remarks",
]

# Identifier-ish source columns that must never survive into the clean frame.
_PII_TOKENS = {
    "applicant",
    "id",
    "application_id",
    "agreement_id",
    "edb_loan_id",
    "edb_customer_id",
    "created_by",
    "auth_signatory",
    "name",
    "emirates_id",
}

# Plausibility bounds — anything outside is treated as a data-entry artefact and
# dropped from the *usable* view (the raw count still reports it).
_SALARY_MIN, _SALARY_MAX = 1_000, 400_000          # AED / month
_OVERDUE_MONTHS_MAX = 360                            # 30 years of arrears is the ceiling
_EMI_MAX = 200_000                                   # AED / month


def _norm_token(name: str) -> str:
    """Normalize a header to a comparison token: lower, alnum + underscores."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    return re.sub(r"_+", "_", s).strip("_")


@functools.lru_cache(maxsize=1)
def _alias_lookup() -> dict[str, str]:
    """variant-token -> canonical column."""
    out: dict[str, str] = {}
    for canonical, variants in _COLUMN_ALIASES.items():
        for v in variants:
            out[_norm_token(v)] = canonical
    return out


def resolve_dataset_path(explicit: str | Path | None = None) -> Path:
    """Resolve the Excel path. Honors an explicit path, then ``MIZAN_DATASET_PATH``,
    then walks up from this file to find ``data/RescheduleArrears.xlsx``."""
    import os

    if explicit:
        return Path(explicit).expanduser()
    env = os.getenv("MIZAN_DATASET_PATH")
    if env:
        return Path(env).expanduser()

    # backend/app/data/organizer_dataset.py -> repo root is parents[3]
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / DATASET_RELATIVE_PATH,   # repo root
        Path.cwd() / DATASET_RELATIVE_PATH,
        here.parents[2] / DATASET_RELATIVE_PATH,    # backend/
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


@dataclass
class OrganizerDataset:
    """Result of an ingestion attempt.

    ``loaded`` is the single source of truth for "did we get usable data". When
    ``False``, ``records`` is empty and ``message`` explains why — callers should
    surface that as a graceful "dataset not loaded" response, not an error.
    """

    loaded: bool
    message: str
    source_path: str
    sheets: list[str] = field(default_factory=list)
    raw_row_count: int = 0
    usable_row_count: int = 0
    columns: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    dropped_rows: int = 0

    def dataframe(self):
        """Return the usable records as a pandas DataFrame (empty if not loaded)."""
        import pandas as pd

        return pd.DataFrame(self.records)


def _coerce_frame(df, year_label: str):
    """Map one sheet onto the canonical schema, dropping PII columns."""
    import pandas as pd

    lookup = _alias_lookup()
    rename: dict[str, str] = {}
    for col in df.columns:
        tok = _norm_token(col)
        if tok in _PII_TOKENS:
            continue  # never carry identifiers forward
        canonical = lookup.get(tok)
        if canonical:
            rename[col] = canonical

    keep = [c for c in df.columns if c in rename]
    out = df[keep].rename(columns=rename).copy()

    # Drop any duplicate canonical columns (keep first non-null wins later).
    out = out.loc[:, ~out.columns.duplicated()]

    # Ensure every canonical column exists so the frames concat cleanly.
    for canonical in _COLUMN_ALIASES:
        if canonical not in out.columns:
            out[canonical] = pd.NA

    # Provenance: which sheet/year this row came from.
    out["source_year"] = str(year_label).strip()
    return out


def _clean(df):
    """Type-coerce, range-filter, and derive helper columns on the merged frame."""
    import numpy as np
    import pandas as pd

    raw_count = len(df)

    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in _DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in _TEXT_COLUMNS:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})
            )
            # Normalize YES/NO-ish flags to upper for stable comparisons.
            if col in {"deduct_from_salary", "until_loan_end"}:
                df[col] = df[col].str.upper()

    # Unified request type: prefer the explicit request, fall back to approved.
    df["request_type_effective"] = df["request_type"].fillna(df["approved_request_type"])

    # Derived year: explicit start_year, else the created_date year, else sheet.
    derived_year = df["start_year"]
    if "created_date" in df.columns:
        derived_year = derived_year.fillna(df["created_date"].dt.year)
    derived_year = derived_year.fillna(pd.to_numeric(df["source_year"], errors="coerce"))
    df["year"] = pd.to_numeric(derived_year, errors="coerce").astype("Int64")

    # Approval duration in days (created -> approved), when both are present.
    if "created_date" in df.columns and "approved_date" in df.columns:
        delta = (df["approved_date"] - df["created_date"]).dt.days
        # Negative or absurd deltas are data artefacts; treat as missing.
        df["approval_duration_days"] = delta.where((delta >= 0) & (delta <= 3650))
    else:
        df["approval_duration_days"] = pd.NA

    # EMI / salary ratios (the 20%-cap evidence). Guard divide-by-zero.
    salary = df["current_salary"].where(df["current_salary"] > 0)
    df["current_emi_ratio"] = (df["current_emi_amt"] / salary).round(4)
    df["new_emi_ratio"] = (df["new_emi_amt"] / salary).round(4)

    # ── usability filter ──────────────────────────────────────────────────────
    # A row is "usable" for ratio/insight math if it has a plausible salary and a
    # non-negative overdue-months reading. Other fields may still be missing.
    usable = (
        df["current_salary"].between(_SALARY_MIN, _SALARY_MAX)
        & df["over_due_months"].fillna(-1).ge(0)
        & df["over_due_months"].fillna(_OVERDUE_MONTHS_MAX + 1).le(_OVERDUE_MONTHS_MAX)
        & df["current_emi_amt"].fillna(0).le(_EMI_MAX)
        & df["over_due_amt"].fillna(0).ge(0)
    )
    df["is_usable"] = usable

    # Replace numpy NaN/NaT with None for clean JSON serialization downstream.
    df = df.replace({np.nan: None})
    df = df.astype(object).where(pd.notnull(df), None)
    return df, raw_count


def load_organizer_dataset(path: str | Path | None = None) -> OrganizerDataset:
    """Load and clean the organizer Excel. Always returns an
    :class:`OrganizerDataset`; check ``.loaded`` before using ``.records``."""
    resolved = resolve_dataset_path(path)
    source = str(resolved)

    if not resolved.exists():
        msg = (
            f"Organizer dataset not found at '{source}'. Place "
            f"'{DATASET_RELATIVE_PATH}' in the repo to enable Historical Intelligence."
        )
        logger.warning(msg)
        return OrganizerDataset(loaded=False, message=msg, source_path=source)

    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - pandas is a hard dep
        return OrganizerDataset(
            loaded=False,
            message=f"pandas unavailable: {exc}",
            source_path=source,
        )

    try:
        xls = pd.ExcelFile(resolved)
        sheets = list(xls.sheet_names)
        frames = []
        for sheet in sheets:
            try:
                raw = pd.read_excel(xls, sheet_name=sheet)
            except Exception as exc:  # one bad sheet shouldn't kill the rest
                logger.warning("Skipping sheet %s: %s", sheet, exc)
                continue
            if raw.empty:
                continue
            frames.append(_coerce_frame(raw, sheet))

        if not frames:
            return OrganizerDataset(
                loaded=False,
                message="Workbook contained no readable rows.",
                source_path=source,
                sheets=sheets,
            )

        merged = pd.concat(frames, ignore_index=True, sort=False)
        cleaned, raw_count = _clean(merged)
        usable = cleaned[cleaned["is_usable"] == True]  # noqa: E712

        records = usable.to_dict(orient="records")
        return OrganizerDataset(
            loaded=True,
            message=f"Loaded {len(usable)} usable of {raw_count} raw records across {len(sheets)} sheets.",
            source_path=source,
            sheets=sheets,
            raw_row_count=int(raw_count),
            usable_row_count=int(len(usable)),
            columns=list(cleaned.columns),
            records=records,
            dropped_rows=int(raw_count - len(usable)),
        )
    except Exception as exc:  # noqa: BLE001 - last-resort graceful degradation
        logger.exception("Failed to load organizer dataset")
        return OrganizerDataset(
            loaded=False,
            message=f"Failed to read '{source}': {exc}",
            source_path=source,
        )


@functools.lru_cache(maxsize=1)
def get_cached_dataset() -> OrganizerDataset:
    """Process-wide cached load (the Excel is immutable at runtime)."""
    return load_organizer_dataset()


def clear_cache() -> None:
    get_cached_dataset.cache_clear()
