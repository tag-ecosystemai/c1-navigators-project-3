from .income_expense_analysis import proposed_payment, verified_monthly_inflows, income_variance, net_disposable_income
from .ratio_analysis import dti, lti
from ..utils.error_handler import log_error, module_result
from ..utils.evidence_builder import build_evidence


def analyse_financials(input_data):
    errors, evidence = [], []
    try:
        app, txns = input_data["application"], input_data["transactions"]
        payment = proposed_payment(app); verified = verified_monthly_inflows(txns)
        values = {"proposed_monthly_payment": payment, "verified_monthly_inflows": verified,
                  "dti_pct": dti(app, payment), "lti_ratio": lti(app),
                  "ndi_amount": net_disposable_income(app, payment), "income_variance_pct": income_variance(app, txns)}
        if any(values[key] is None for key in ("dti_pct", "lti_ratio", "ndi_amount", "income_variance_pct")):
            errors.append(log_error("missing_data", "one or more financial metrics could not be calculated", "financial_summary"))
        for key in ("dti_pct", "lti_ratio", "ndi_amount", "income_variance_pct"):
            if values[key] is not None: evidence.append(build_evidence("EV-FIN-" + key, "financial_metric", key, "Calculated financial metric.", "financial_summary", {key: values[key]}, "low"))
        return module_result("financial_summary", values, evidence, errors)
    except Exception as exc:
        return module_result("financial_summary", {}, [], [log_error("analysis_failure", str(exc), "financial_summary")], "fallback")
