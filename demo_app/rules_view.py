"""Display layer for the 14 policy rules: threshold text, plain-English reasons, bars and analyst actions.

The rule evaluator only returns labels ("FLAG_FOR_REVIEW", "Tier 2", ...). This module turns a label plus the
applicant's numbers into text a person can read. It never decides anything: statuses come from the engine.
The numeric limits below mirror policy_evaluator.py and data/policies/*.md; tests/test_demo_app.py checks them
against the real evaluator at every boundary, so a change there cannot silently leave this text wrong.
"""

from __future__ import annotations

from ai_engineering.orchestrator.orchestrator import _KNOCKOUTS
from ai_engineering.policy_engine.policy_evaluator import ndi_buffer

# Limits as the evaluator applies them (see policy_evaluator.evaluate_policies).
DTI_BANDS = (35, 43, 50)            # <=35 clean, <=43 conditional, <=50 referral, >50 decline
LTI_CAPS = {"Tier 1": 0.35, "Tier 2": 0.30, "Tier 3": 0.25, "Tier 4": 0.20}  # + 0.05 review band
LTI_REVIEW_MARGIN = 0.05
INC_BANDS = (10, 25)                # <=10 clean, <=25 review, >25 high risk
GAMBLING_BANDS = (3, 10)            # <3 clean, <=10 review, >10 decline
MIN_INCOME = 2000
MIN_TENURE_MONTHS = 6
AGE_RANGE = (21, 68)

_PASS = {"SATISFIED", "CLEAN", "HEALTHY", "Tier 1", "Tier 2"}


def outcome(code: str, status: str) -> str:
    """pass | review | fail | missing (fail = NOT_SATISFIED or a decline-class state)."""
    if status in _PASS:
        return "pass"
    if status == "MISSING_DATA":
        return "missing"
    if status in _KNOCKOUTS.get(code, set()) or status in {"NOT_SATISFIED", "CRITICAL_DISTRESS", "KNOCKOUT", "HIGH_RISK"}:
        return "fail"
    return "review"


def is_decline_class(code: str, status: str) -> bool:
    return status in _KNOCKOUTS.get(code, set())


def _money(v, suffix=""):
    return "not available" if v is None else f"{'-' if v < 0 else ''}${abs(v):,.0f}{suffix}"


def _money2(v, suffix=""):
    return "not available" if v is None else f"{'-' if v < 0 else ''}${abs(v):,.2f}{suffix}"


def _pct(v, digits=1):
    return "not available" if v is None else f"{v:.{digits}f}%"


def _num(app, *keys):
    for key in keys:
        value = app.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _bar(value, lo, hi, marks, direction):
    """A small gauge: `value` between lo and hi with labelled marks; direction says which side is good."""
    if value is None:
        return None
    return {"min": lo, "max": round(max(hi, value * 1.08), 2), "value": round(value, 2), "direction": direction,
            "marks": [{"at": at, "label": label} for at, label in marks]}


def describe_rule(code: str, status: str, app: dict, fin: dict, txn: dict, gaps: dict) -> dict:
    """{"actual", "actual_num", "threshold", "reason", "bar"} for one rule."""
    d = _DESCRIBERS.get(code)
    base = {"actual": "n/a", "actual_num": None, "threshold": "", "reason": f"The rule returned {status}.", "bar": None}
    if d is None:
        return base
    out = {**base, **d(status, app, fin, txn)}
    if status == "MISSING_DATA":
        missing = gaps.get(code)
        out["reason"] = ("Not enough data to evaluate this rule" + (f" (missing: {', '.join(missing)})" if missing else "")
                         + ". An analyst needs to obtain it.")
    return out


# ---------------------------------------------------------------- one describer per rule


def _elg001(status, app, fin, txn):
    age = _num(app, "age")
    return {"actual": "n/a" if age is None else f"{age:.0f} years", "actual_num": age, "threshold": "21 to 68 years",
            "reason": (f"Age {age:.0f} is within the 21 to 68 range." if status == "SATISFIED"
                       else f"Age {age:.0f} is outside the 21 to 68 range.") if age is not None else "Age is missing.",
            "bar": _bar(age, 15, 75, [(21, "21"), (68, "68")], "range")}


def _elg002(status, app, fin, txn):
    income = _num(app, "declared_monthly_net_income", "income")
    ok = status == "SATISFIED"
    return {"actual": _money(income, "/month"), "actual_num": income, "threshold": "at least $2,000 per month",
            "reason": f"Declared monthly net income of {_money(income)} " + ("meets" if ok else "is below") + " the $2,000 minimum.",
            "bar": _bar(income, 0, 10000, [(MIN_INCOME, "$2,000")], "higher")}


def _elg003(status, app, fin, txn):
    months = _num(app, "employment_length_months")
    if months is None:
        reason = "Employment length is missing."
    elif status == "SATISFIED":
        reason = f"{months:.0f} months with the current employer meets the 6 month minimum."
    elif status == "FLAG_FOR_REVIEW":
        reason = f"{months:.0f} months is under the 6 month minimum, so an analyst confirms probation status and job history."
    else:
        reason = "Under 1 month with the current employer: employment history is not established."
    return {"actual": "n/a" if months is None else f"{months:.0f} months", "actual_num": months,
            "threshold": "at least 6 months with the current employer", "reason": reason,
            "bar": _bar(months, 0, 36, [(MIN_TENURE_MONTHS, "6 mo")], "higher")}


def _scr001(status, app, fin, txn):
    score = _num(app, "credit_score")
    reasons = {
        "Tier 1": f"Score {score:.0f} is Tier 1 (prime): fast-track standard underwriting." if score else "",
        "Tier 2": f"Score {score:.0f} is Tier 2 (near-prime): standard underwriting with full cash-flow checks." if score else "",
        "Tier 3": f"Score {score:.0f} is Tier 3 (subprime): mandatory credit investigation." if score else "",
        "Tier 4": f"Score {score:.0f} is Tier 4 (high risk), below 600: policy decline, exception only." if score else "",
    }
    return {"actual": "n/a" if score is None else f"{score:.0f} ({status})", "actual_num": score,
            "threshold": "720+ Tier 1, 660 to 719 Tier 2, 600 to 659 Tier 3, below 600 decline",
            "reason": reasons.get(status) or "Credit score is missing.",
            "bar": _bar(score, 300, 850, [(600, "600"), (660, "660"), (720, "720")], "higher")}


def _scr002(status, app, fin, txn):
    bankruptcies = _num(app, "bankruptcies_count") or 0
    liens = _num(app, "tax_liens_count") or 0
    ok = status == "SATISFIED"
    return {"actual": f"{bankruptcies:.0f} bankruptcies, {liens:.0f} tax liens", "actual_num": bankruptcies + liens,
            "threshold": "none on file",
            "reason": ("No bankruptcies or tax liens on file." if ok else
                       f"{bankruptcies:.0f} bankruptcy record(s) and {liens:.0f} tax lien(s) on file. Policy treats active records as a knockout.")}


def _dti001(status, app, fin, txn):
    v = fin.get("dti_pct")
    texts = {
        "SATISFIED": f"Debt payments are {_pct(v)} of income, within the 35% clean limit.",
        "CONDITIONAL": f"{_pct(v)} is in the 35 to 43% band: conditional pass, verify stable employment and a 3 month savings buffer.",
        "FLAG_FOR_REVIEW": f"{_pct(v)} is in the 43 to 50% band: mandatory referral to a senior underwriter.",
        "NOT_SATISFIED": f"{_pct(v)} is above 50%: automatic policy decline.",
    }
    return {"actual": _pct(v), "actual_num": v, "threshold": "35% or less clean, 43% conditional, 50% referral, above 50% decline",
            "reason": texts.get(status, "DTI could not be calculated."),
            "bar": _bar(v, 0, 60, [(35, "35%"), (43, "43%"), (50, "50%")], "lower")}


def _lti001(status, app, fin, txn):
    v = fin.get("lti_ratio")
    tier = _tier_of(app)
    cap = LTI_CAPS.get(tier)
    texts = {
        "SATISFIED": f"Loan is {v:.2f}x annual income, within the {cap}x cap for {tier}." if v is not None and cap else "",
        "FLAG_FOR_REVIEW": f"Loan is {v:.2f}x annual income, slightly above the {cap}x cap for {tier}." if v is not None and cap else "",
        "NOT_SATISFIED": f"Loan is {v:.2f}x annual income, well above the {cap}x cap for {tier}." if v is not None and cap else "",
    }
    return {"actual": "n/a" if v is None else f"{v:.2f}x annual income", "actual_num": v,
            "threshold": f"engine cap {cap}x for {tier}" if cap else "cap depends on credit tier",
            "reason": texts.get(status) or "Loan-to-income could not be calculated.",
            "bar": _bar(v, 0, 0.6, [(cap, f"{cap}x")] if cap else [], "lower")}


def _ndi001(status, app, fin, txn):
    v = fin.get("ndi_amount")
    deps = _num(app, "dependents_count")
    buffer = ndi_buffer(deps)
    who = "single applicant" if not deps else f"{deps:.0f} dependent(s)"
    texts = {
        "SATISFIED": f"{_money2(v)} is left each month after all commitments, above the {_money(buffer)} buffer.",
        "FLAG_FOR_REVIEW": f"{_money2(v)} left each month is below the {_money(buffer)} buffer: marginal liquidity, so an analyst reviews it.",
        "NOT_SATISFIED": f"{_money2(v)} left each month is negative: the applicant cannot afford the loan.",
    }
    return {"actual": _money2(v, "/month"), "actual_num": v,
            "threshold": "at least " + ("n/a" if buffer is None else _money(buffer)) + f" per month ({who})",
            "reason": texts.get(status, "Net disposable income could not be calculated."),
            "bar": _bar(v, 0, (buffer or 500) * 2, [(buffer, _money(buffer))] if buffer else [], "higher")}


def _inc001(status, app, fin, txn):
    v = fin.get("income_variance_pct")
    texts = {
        "SATISFIED": f"Declared income and bank deposits differ by {_pct(v)}, within the 10% tolerance.",
        "REVIEW_REQUIRED": f"Declared income and bank deposits differ by {_pct(v)} (10 to 25%): ask for recent payslips or an employer letter.",
        "HIGH_RISK": f"Declared income and bank deposits differ by {_pct(v)}, more than the 25% limit: the declared income is not supported by the deposits.",
    }
    return {"actual": _pct(v) + " gap", "actual_num": v, "threshold": "10% or less clean, up to 25% review, above 25% high risk",
            "reason": texts.get(status, "Income variance could not be calculated."),
            "bar": _bar(v, 0, 40, [(10, "10%"), (25, "25%")], "lower")}


def _txn001(status, app, fin, txn):
    v = txn.get("gambling_pct_of_income")
    if status == "SATISFIED":
        reason = "No gambling spend found." if not v else f"Gambling spend is {_pct(v)} of income, under the 3% clean limit."
    elif status == "FLAG_FOR_REVIEW":
        reason = f"Gambling spend is {_pct(v)} of income (3 to 10%): monitor."
    else:
        reason = f"Gambling spend is {_pct(v)} of income, above the 10% limit."
    return {"actual": _pct(v) + " of income", "actual_num": v, "threshold": "under 3% clean, 3 to 10% review, above 10% decline",
            "reason": reason, "bar": _bar(v, 0, 15, [(3, "3%"), (10, "10%")], "lower")}


def _txn002(status, app, fin, txn):
    n = txn.get("nsf_event_count")
    texts = {
        "CLEAN": "No overdraft or NSF events in the statement window.",
        "CAUTION": "One isolated overdraft or NSF event: tolerable, noted.",
        "FLAG_FOR_REVIEW": f"{n} overdraft or NSF events (2 to 3): needs review.",
        "KNOCKOUT": f"{n} overdraft or NSF events: 4 or more is a knockout.",
    }
    return {"actual": "n/a" if n is None else f"{n} events", "actual_num": n,
            "threshold": "none clean, 1 caution, 2 to 3 review, 4 or more knockout", "reason": texts.get(status, "Event count is missing."),
            "bar": _bar(n, 0, 6, [(1, "1"), (2, "2"), (4, "4")], "lower")}


def _txn003(status, app, fin, txn):
    v = txn.get("undisclosed_debt_total")
    shadow = fin.get("shadow_dti_pct")
    texts = {
        "SATISFIED": "All recurring debt payments match the debts declared on the application.",
        "FLAG_FOR_REVIEW": f"{_money(v)} a month of recurring payments to lenders was found in the bank statement but not declared. It must be added to the debt ratio.",
        "NOT_SATISFIED": (f"{_money(v)} a month of recurring payments to lenders or buy-now-pay-later providers was found in the bank "
                          f"statement but not declared. Including it, DTI rises to {_pct(shadow)}."),
    }
    return {"actual": _money(v, "/month undisclosed"), "actual_num": v,
            "threshold": "none allowed (policy: not satisfied above $250 a month)", "reason": texts.get(status, "Undisclosed debt could not be measured."),
            "bar": _bar(v, 0, 400, [(250, "$250")], "lower")}


def _txn004(status, app, fin, txn):
    events = txn.get("window_dressing_events")
    n = len(events) if isinstance(events, list) else None
    return {"actual": "n/a" if n is None else f"{n} event(s)", "actual_num": n,
            "threshold": "no unexplained deposit above 50% of monthly income shortly before applying",
            "reason": ("No unexplained large deposits shortly before applying." if status == "SATISFIED"
                       else f"{n} large non-payroll deposit(s) above 50% of monthly income with no documented source.")}


def _txn005(status, app, fin, txn):
    texts = {"HEALTHY": "The balance stays healthy between paydays.", "VULNERABLE": "The balance drops very low before payday.",
             "CRITICAL_DISTRESS": "The balance repeatedly runs out before payday."}
    return {"actual": status.replace("_", " ").capitalize(), "threshold": "balance stays positive between paydays",
            "reason": texts.get(status, "Balance pattern is missing.")}


def _tier_of(app):
    score = _num(app, "credit_score")
    if score is None:
        return None
    return "Tier 1" if score >= 720 else "Tier 2" if score >= 660 else "Tier 3" if score >= 600 else "Tier 4"


_DESCRIBERS = {
    "POL-ELG-001": _elg001, "POL-ELG-002": _elg002, "POL-ELG-003": _elg003, "POL-SCR-001": _scr001,
    "POL-SCR-002": _scr002, "POL-DTI-001": _dti001, "POL-LTI-001": _lti001, "POL-NDI-001": _ndi001,
    "POL-INC-001": _inc001, "POL-TXN-001": _txn001, "POL-TXN-002": _txn002, "POL-TXN-003": _txn003,
    "POL-TXN-004": _txn004, "POL-TXN-005": _txn005,
}

# ---------------------------------------------------------------- analyst actions (from the policy documents)

ACTIONS = {
    "POL-ELG-001": "Check the date of birth against the ID: age must be 21 to 68 at loan maturity.",
    "POL-ELG-002": "Corroborate income with a payslip or bank statement (minimum $2,000 net per month).",
    "POL-ELG-003": "Confirm length of employment and probation status with the employer.",
    "POL-SCR-001": "Follow the credit tier procedure: Tier 3 needs a mandatory credit investigation; Tier 4 needs Senior Credit Committee sign-off.",
    "POL-SCR-002": "Check the bankruptcy and tax lien records: dates, status and amounts.",
    "POL-DTI-001": "Verify stable employment and savings; for DTI above 43% refer to a senior underwriter and look for compensating factors.",
    "POL-LTI-001": "Check the requested amount against the cap for the credit tier.",
    "POL-NDI-001": "Check the applicant's living expenses and dependents; confirm the income left after the new payment.",
    "POL-INC-001": "Request recent payslips or an employer verification letter and reconcile them with the bank deposits.",
    "POL-TXN-001": "Review the gambling transactions and ask the applicant about them.",
    "POL-TXN-002": "Review the overdraft and NSF events: dates, amounts and causes.",
    "POL-TXN-003": "Ask the applicant about the undisclosed lenders and recalculate the debt ratio with those payments.",
    "POL-TXN-004": "Ask for the source of the large deposits (bonus slip, tax refund, asset sale) and check for rapid outflows.",
    "POL-TXN-005": "Review the balance pattern between paydays for signs of reliance on emergency credit.",
}
