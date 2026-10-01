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


def evaluate_policies(input_data, financial, transactions):
    try:
        app = input_data["application"]; _, errors = load_policies(input_data.get("policies"))
        age, income, employment = number(app.get("age")), number(first(app, "income", "declared_monthly_net_income"), False), number(app.get("employment_length_months"))
        score = number(app.get("credit_score")); adverse = (number(app.get("bankruptcies_count")) or 0) > 0 or (number(app.get("tax_liens_count")) or 0) > 0
        dti, lti, ndi, variance = (financial.get(k) for k in ("dti_pct", "lti_ratio", "ndi_amount", "income_variance_pct"))
        gambling, nsf, debt, windows, burn = (transactions.get(k) for k in ("gambling_pct_of_income", "nsf_event_count", "undisclosed_debt_total", "window_dressing_events", "burn_rate_status"))
        caps = {"Tier 1": .35, "Tier 2": .30, "Tier 3": .25, "Tier 4": .20}; tier = credit_tier(score)
        flags = {"POL-ELG-001": "MISSING_DATA" if age is None else "SATISFIED" if 21 <= age <= 68 else "NOT_SATISFIED", "POL-ELG-002": "MISSING_DATA" if income is None else "SATISFIED" if income >= 2000 else "NOT_SATISFIED", "POL-ELG-003": "MISSING_DATA" if employment is None else "SATISFIED" if employment >= 6 else "FLAG_FOR_REVIEW" if employment >= 1 else "NOT_SATISFIED", "POL-SCR-001": tier or "MISSING_DATA", "POL-SCR-002": "MISSING_DATA" if score is None else "NOT_SATISFIED" if adverse else "SATISFIED", "POL-DTI-001": _status(dti, [35, 43, 50], ["SATISFIED", "CONDITIONAL", "FLAG_FOR_REVIEW", "NOT_SATISFIED"]), "POL-LTI-001": "MISSING_DATA" if lti is None or tier is None else "SATISFIED" if lti <= caps[tier] else "FLAG_FOR_REVIEW" if lti <= caps[tier] + .05 else "NOT_SATISFIED", "POL-NDI-001": _status(ndi, [299, 499], ["NOT_SATISFIED", "FLAG_FOR_REVIEW", "SATISFIED"]), "POL-INC-001": _status(variance, [10, 25], ["SATISFIED", "REVIEW_REQUIRED", "HIGH_RISK"]), "POL-TXN-001": _status(gambling, [3, 10], ["SATISFIED", "FLAG_FOR_REVIEW", "NOT_SATISFIED"]), "POL-TXN-002": "MISSING_DATA" if nsf is None else "CLEAN" if nsf == 0 else "CAUTION" if nsf == 1 else "FLAG_FOR_REVIEW" if nsf <= 3 else "KNOCKOUT", "POL-TXN-003": "MISSING_DATA" if debt is None else "SATISFIED" if debt == 0 else "FLAG_FOR_REVIEW" if debt < 100 else "NOT_SATISFIED", "POL-TXN-004": "MISSING_DATA" if windows is None else "FLAG_FOR_REVIEW" if windows else "SATISFIED", "POL-TXN-005": burn or "MISSING_DATA"}
        evidence = [build_evidence("EV-POL-" + key, "policy_violation", key, "Policy rule evaluated.", "policy_evaluator", {"rule": key, "status": value}, "critical" if value in {"NOT_SATISFIED", "KNOCKOUT", "HIGH_RISK"} else "medium") for key, value in flags.items() if value not in {"SATISFIED", "CLEAN"}]
        return module_result("policy_evaluator", flags, evidence, errors)
    except Exception as exc:
        return module_result("policy_evaluator", {}, [], [log_error("policy_failure", str(exc), "policy_evaluator")], "fallback")
