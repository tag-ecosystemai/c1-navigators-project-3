"""The 20 features models/risk_model.pkl was trained on.

One definition, used both to build the training data (scripts/build_ml_dataset.py) and to score a live
case in the engine (feature_builder.py), so the two can never drift apart. Pure Python (no pandas).

Quirks of the training recipe that are kept on purpose, because the model learned them:
  * monthly_inflows / monthly_outflows are sums over ALL transactions in the window (not per month);
  * anomaly_score is the NUMBER of transactions flagged as anomalies, not the engine's 0-100 score;
  * ratios are divided by (denominator + 1e-6); a missing value becomes 0.0 (the script's fillna).
"""

from __future__ import annotations

import math

from ..utils.validation import first, number

# Column order of data/processed/ml_features.csv, which is the order the model was trained with.
FEATURES = (
    "dti", "loan_to_income", "expense_to_income", "debt_to_income", "credit_score", "credit_score_tier_num",
    "income_stability", "gambling_ratio", "savings_rate", "monthly_payment_ratio", "lti_ratio",
    "monthly_inflows", "monthly_outflows", "anomaly_score", "txn_density", "avg_txn_amount",
    "dependents_count", "bankruptcies_count", "tax_liens_count", "employment_length_months",
)

TIER_NUM = {"TIER_1_PRIME": 1, "TIER_2_NEAR_PRIME": 2, "TIER_3_SUBPRIME": 3, "TIER_4_HIGH_RISK": 4}


def _num(value):
    """float, or None for missing / NaN / non-numeric (bools are not numbers)."""
    result = number(value)
    return result


def _ratio(numerator, denominator):
    return None if numerator is None or denominator is None else numerator / (denominator + 1e-6)


def _flagged(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value) and not (isinstance(value, float) and math.isnan(value))


def _tier_num(app, score):
    tier = TIER_NUM.get(str(app.get("credit_score_tier", "")))
    if tier is not None:
        return float(tier)
    if score is None:
        return 0.0
    return 1.0 if score >= 720 else 2.0 if score >= 660 else 3.0 if score >= 600 else 4.0


def derive_features(app: dict, transactions: list[dict], financial: dict | None = None) -> dict[str, float]:
    """The 20 model features for one applicant, from the raw application and raw transactions.

    `financial` (the engine's financial metrics) is only a fallback for the precomputed application
    columns calculated_dti_pct / calculated_lti_ratio / estimated_monthly_payment.
    """
    financial = financial or {}
    net = _num(first(app, "declared_monthly_net_income", "income"))
    actual = _num(app.get("actual_monthly_salary"))
    housing = _num(first(app, "declared_monthly_housing_expense", "housing_expense"))
    debt = _num(first(app, "declared_existing_monthly_debt", "existing_monthly_debt"))
    loan = _num(first(app, "requested_loan_amount", "requested_amount"))
    term = _num(app.get("loan_term_months"))
    score = _num(app.get("credit_score"))

    rows = [t for t in transactions if isinstance(t, dict)]
    amounts = [(_num(t.get("amount")), t) for t in rows]
    amounts = [(a, t) for a, t in amounts if a is not None]
    inflows = sum(a for a, t in amounts if t.get("type") == "CREDIT")
    outflows = sum(a for a, t in amounts if t.get("type") == "DEBIT")
    gambling = sum(a for a, t in amounts if t.get("category") == "GAMBLING")
    values = {
        "dti": _num(app.get("calculated_dti_pct")) if _num(app.get("calculated_dti_pct")) is not None else financial.get("dti_pct"),
        "loan_to_income": _ratio(loan, net),
        "expense_to_income": _ratio(housing, net),
        "debt_to_income": _ratio(debt, net),
        "credit_score": score,
        "credit_score_tier_num": _tier_num(app, score),
        "income_stability": _ratio(None if net is None or actual is None else abs(net - actual), actual),
        "gambling_ratio": _ratio(gambling, actual),
        "savings_rate": _ratio(None if None in (actual, debt, housing) else actual - debt - housing, actual),
        "monthly_payment_ratio": _ratio(
            _num(app.get("estimated_monthly_payment")) if _num(app.get("estimated_monthly_payment")) is not None
            else financial.get("proposed_monthly_payment"), net),
        "lti_ratio": _num(app.get("calculated_lti_ratio")) if _num(app.get("calculated_lti_ratio")) is not None else financial.get("lti_ratio"),
        "monthly_inflows": inflows,
        "monthly_outflows": outflows,
        "anomaly_score": float(sum(_flagged(t.get("flagged_anomaly")) for t in rows)),
        "txn_density": None if term is None else len(amounts) / max(term, 1.0),
        "avg_txn_amount": (sum(a for a, _ in amounts) / len(amounts)) if amounts else None,
        "dependents_count": _num(app.get("dependents_count")),
        "bankruptcies_count": _num(app.get("bankruptcies_count")),
        "tax_liens_count": _num(app.get("tax_liens_count")),
        "employment_length_months": _num(app.get("employment_length_months")),
    }
    return {name: 0.0 if values[name] is None else float(values[name]) for name in FEATURES}
