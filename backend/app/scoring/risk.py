"""Lightweight re-default risk forecast.

Uses a scikit-learn LogisticRegression trained at import time on a small,
*seeded synthetic* dataset (deterministic). If scikit-learn is unavailable the
same feature vector is scored by a transparent hand-tuned logistic — so output
is stable and explainable either way. This is illustrative, not a production
credit model.
"""
from __future__ import annotations

import math

from ..schemas import CaseState, RiskScore

# Feature order: [obligations_ratio, current_deduction_ratio, months_in_arrears,
#                 on_time_ratio, is_unemployed, dependents_norm]
_FEATURE_NAMES = [
    "obligations_ratio",
    "current_deduction_ratio",
    "months_in_arrears",
    "on_time_ratio",
    "is_unemployed",
    "dependents_norm",
]

# Hand-tuned logistic weights (used directly as fallback, and as the synthetic
# "ground truth" the sklearn model learns from). Sign-meaningful & auditable.
_W = [1.6, 1.2, 0.18, -2.2, 1.1, 0.5]
_B = -1.3

_model = None
_model_name = "heuristic-logistic"


def _logistic(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _heuristic_proba(x: list[float]) -> float:
    z = _B + sum(w * xi for w, xi in zip(_W, x))
    return _logistic(z)


def _try_train_sklearn():
    """Train a tiny deterministic LogisticRegression on synthetic samples."""
    global _model, _model_name
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
    except Exception:  # sklearn/numpy absent -> heuristic fallback
        return None

    rng = np.random.default_rng(42)
    n = 600
    obligations = rng.uniform(0, 0.9, n)
    deduction = rng.uniform(0.05, 0.35, n)
    arrears = rng.integers(0, 10, n).astype(float)
    on_time = rng.uniform(0.3, 1.0, n)
    unemployed = rng.integers(0, 2, n).astype(float)
    dependents = rng.uniform(0, 1, n)
    X = np.column_stack([obligations, deduction, arrears / 12.0, on_time, unemployed, dependents])

    # Label from the auditable heuristic + small deterministic noise.
    z = _B + X @ np.array(_W)
    p = 1 / (1 + np.exp(-z))
    y = (p + rng.normal(0, 0.05, n) > 0.5).astype(int)

    clf = LogisticRegression(max_iter=500)
    clf.fit(X, y)
    _model = clf
    _model_name = "sklearn-logreg"
    return clf


_try_train_sklearn()


def _features(state: CaseState) -> list[float]:
    aff = state.affordability
    obl_ratio = aff.obligations_ratio if aff else 0.5
    ded_ratio = aff.current_deduction_ratio if aff else 0.2
    months_arrears = state.arrears.months_in_arrears if state.arrears else 0
    on_time = state.payment_history.on_time_ratio if state.payment_history else 1.0
    is_unemployed = 1.0 if (
        state.beneficiary and state.beneficiary.employment_status.value == "unemployed"
    ) else 0.0
    dependents = state.family.dependents if state.family else 0
    dependents_norm = min(dependents / 6.0, 1.0)
    return [obl_ratio, ded_ratio, months_arrears / 12.0, on_time, is_unemployed, dependents_norm]


def forecast_risk(state: CaseState) -> RiskScore:
    x = _features(state)
    if _model is not None:
        try:
            import numpy as np

            proba = float(_model.predict_proba(np.array([x]))[0][1])
        except Exception:
            proba = _heuristic_proba(x)
    else:
        proba = _heuristic_proba(x)

    proba = round(max(0.0, min(1.0, proba)), 3)
    band = "high" if proba >= 0.6 else "medium" if proba >= 0.35 else "low"

    drivers: list[str] = []
    if x[4] >= 1.0:
        drivers.append("currently unemployed")
    if x[0] >= 0.5:
        drivers.append("high external obligations")
    if x[2] * 12 >= 3:
        drivers.append(f"{int(x[2] * 12)} months in arrears")
    if x[3] < 0.7:
        drivers.append("weak payment history")
    if not drivers:
        drivers.append("stable repayment profile")

    return RiskScore(
        redefault_probability=proba,
        band=band,
        drivers=drivers,
        model_name=_model_name,
    )
