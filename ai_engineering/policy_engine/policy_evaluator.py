from .policy_loader import load_policies
from ..financial_analysis.ratio_analysis import credit_tier
from ..utils.error_handler import log_error, module_result
from ..utils.evidence_builder import build_evidence
from ..utils.validation import first, number


def _status(value, boundaries, labels):
    if value is None: return "MISSING_DATA"
    for limit, label in zip(boundaries, labels):
        if value <= limit: return label
    return labels[-1]


def gambling_status(pct):
    # POL-TXN-001: "< 3%" is low risk, so exactly 3.0% is already in the 3-10% review band.
    if pct is None: return "MISSING_DATA"
    return "SATISFIED" if pct < 3 else "FLAG_FOR_REVIEW" if pct <= 10 else "NOT_SATISFIED"


def ndi_buffer(dependents):
    """Required monthly NDI buffer from POL-NDI-001, implemented as written: $500 for a single
    applicant; with dependents, $800 plus $200 per ADDITIONAL dependent (the first is covered by
    the $800). None if the number of dependents is unknown (no default is invented)."""
    if dependents is None: return None
    return 500.0 if dependents <= 0 else 800.0 + 200.0 * (dependents - 1)


def ndi_status(ndi, dependents):
    # POL-NDI-001: negative NDI fails; from 0 up to the buffer is marginal (review); at/above passes.
    buffer = ndi_buffer(dependents)
    if ndi is None or buffer is None: return "MISSING_DATA"
    return "NOT_SATISFIED" if ndi < 0 else "FLAG_FOR_REVIEW" if ndi < buffer else "SATISFIED"


# Inputs each rule needs. A tuple of names = application fields (any alias will do); "fin:" / "txn:"
# name a derived value from the financial / transaction modules.
_INCOME = ("declared_monthly_net_income", "income")
_DEBT = ("declared_existing_monthly_debt", "existing_monthly_debt")
_PAYMENT = [("requested_loan_amount", "requested_amount"), ("loan_term_months",), ("interest_rate_pct",)]
RULE_INPUTS = {
    "POL-ELG-001": [("age",)],
    "POL-ELG-002": [_INCOME],
    "POL-ELG-003": [("employment_length_months",)],
    "POL-SCR-001": [("credit_score",)],
    "POL-SCR-002": [("credit_score",)],
    "POL-DTI-001": [_INCOME, _DEBT] + _PAYMENT,
    "POL-LTI-001": [("requested_loan_amount", "requested_amount"), ("declared_annual_income",), ("credit_score",)],
    "POL-NDI-001": [_INCOME, ("declared_monthly_housing_expense", "housing_expense"),
                    ("declared_monthly_living_expenses", "living_expenses"), _DEBT, ("dependents_count",)] + _PAYMENT,
    "POL-INC-001": [_INCOME, "fin:verified_monthly_inflows"],
    "POL-TXN-001": [_INCOME],
    "POL-TXN-002": ["txn:nsf_event_count"],
    "POL-TXN-003": ["txn:undisclosed_debt_total"],
    "POL-TXN-004": [_INCOME, "txn:window_dressing_events"],
    "POL-TXN-005": ["txn:burn_rate_status"],
}


def find_data_gaps(input_data, financial, transactions, flags):
    """For every rule that came back MISSING_DATA, name the input(s) it lacked. This is a finding
    for the analyst (the data was not supplied), not a system failure."""
    app = input_data.get("application", {}) if isinstance(input_data, dict) else {}
    sources = {"fin": financial or {}, "txn": transactions or {}}

    def present(spec):
        if isinstance(spec, str):
            source, key = spec.split(":")
            value = sources[source].get(key)
            return value is not None and value != "MISSING_DATA"
        return first(app, *spec) is not None

    gaps = []
    for code, value in (flags or {}).items():
        if value != "MISSING_DATA": continue
        missing = [(spec if isinstance(spec, str) else spec[0]) for spec in RULE_INPUTS.get(code, []) if not present(spec)]
        gaps.append({"rule": code, "missing_fields": missing or ["(derived value could not be calculated)"]})
    return gaps


def evaluate_policies(input_data, financial, transactions):
    try:
        app = input_data["application"]; _, errors = load_policies(input_data.get("policies"))
        age, income, employment = number(app.get("age")), number(first(app, "income", "declared_monthly_net_income"), False), number(app.get("employment_length_months"))
        score = number(app.get("credit_score")); adverse = (number(app.get("bankruptcies_count")) or 0) > 0 or (number(app.get("tax_liens_count")) or 0) > 0
        dti, lti, ndi, variance = (financial.get(k) for k in ("dti_pct", "lti_ratio", "ndi_amount", "income_variance_pct"))
        gambling, nsf, debt, windows, burn = (transactions.get(k) for k in ("gambling_pct_of_income", "nsf_event_count", "undisclosed_debt_total", "window_dressing_events", "burn_rate_status"))
        caps = {"Tier 1": .35, "Tier 2": .30, "Tier 3": .25, "Tier 4": .20}; tier = credit_tier(score)
        flags = {"POL-ELG-001": "MISSING_DATA" if age is None else "SATISFIED" if 21 <= age <= 68 else "NOT_SATISFIED", "POL-ELG-002": "MISSING_DATA" if income is None else "SATISFIED" if income >= 2000 else "NOT_SATISFIED", "POL-ELG-003": "MISSING_DATA" if employment is None else "SATISFIED" if employment >= 6 else "FLAG_FOR_REVIEW" if employment >= 1 else "NOT_SATISFIED", "POL-SCR-001": tier or "MISSING_DATA", "POL-SCR-002": "MISSING_DATA" if score is None else "NOT_SATISFIED" if adverse else "SATISFIED", "POL-DTI-001": _status(dti, [35, 43, 50], ["SATISFIED", "CONDITIONAL", "FLAG_FOR_REVIEW", "NOT_SATISFIED"]), "POL-LTI-001": "MISSING_DATA" if lti is None or tier is None else "SATISFIED" if lti <= caps[tier] else "FLAG_FOR_REVIEW" if lti <= caps[tier] + .05 else "NOT_SATISFIED", "POL-NDI-001": ndi_status(ndi, number(app.get("dependents_count"))), "POL-INC-001": _status(variance, [10, 25], ["SATISFIED", "REVIEW_REQUIRED", "HIGH_RISK"]), "POL-TXN-001": gambling_status(gambling), "POL-TXN-002": "MISSING_DATA" if nsf is None else "CLEAN" if nsf == 0 else "CAUTION" if nsf == 1 else "FLAG_FOR_REVIEW" if nsf <= 3 else "KNOCKOUT", "POL-TXN-003": "MISSING_DATA" if debt is None else "SATISFIED" if debt == 0 else "FLAG_FOR_REVIEW" if debt < 100 else "NOT_SATISFIED", "POL-TXN-004": "MISSING_DATA" if windows is None else "FLAG_FOR_REVIEW" if windows else "SATISFIED", "POL-TXN-005": burn or "MISSING_DATA"}
        evidence = [build_evidence("EV-POL-" + key, "policy_violation", key, "Policy rule evaluated.", "policy_evaluator", {"rule": key, "status": value}, "critical" if value in {"NOT_SATISFIED", "KNOCKOUT", "HIGH_RISK"} else "medium") for key, value in flags.items() if value not in {"SATISFIED", "CLEAN"}]
        return module_result("policy_evaluator", flags, evidence, errors)
    except Exception as exc:
        return module_result("policy_evaluator", {}, [], [log_error("policy_failure", str(exc), "policy_evaluator")], "fallback")
