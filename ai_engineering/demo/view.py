"""Turn an investigate() result into a flat, display-ready view (shared by console, HTML and the agent)."""

from __future__ import annotations

from ..policy_engine.policy_evaluator import ndi_buffer
from ..utils.validation import first
from .ml_probe import precomputed_prediction

RULE_TITLES = {
    "POL-ELG-001": "Age & legal capacity",
    "POL-ELG-002": "Minimum income",
    "POL-ELG-003": "Employment tenure",
    "POL-SCR-001": "Credit score tier",
    "POL-SCR-002": "Adverse public records",
    "POL-DTI-001": "Debt-to-income",
    "POL-LTI-001": "Loan-to-income",
    "POL-NDI-001": "Net disposable income",
    "POL-INC-001": "Stated vs actual income",
    "POL-TXN-001": "Gambling",
    "POL-TXN-002": "Overdrafts / NSF",
    "POL-TXN-003": "Undisclosed debt",
    "POL-TXN-004": "Window dressing",
    "POL-TXN-005": "Balance burn rate",
}


def _money(v, suffix=""):
    return "n/a" if v is None else f"${v:,.2f}{suffix}"


def _num(v, fmt, suffix=""):
    return "n/a" if v is None else format(v, fmt) + suffix


def rule_value(code: str, app: dict, report: dict) -> str:
    fin, txn = report["financial_assessment"], report["transaction_assessment"]
    if code == "POL-ELG-001": return str(app.get("age", "n/a"))
    if code == "POL-ELG-002": return _money(first(app, "income", "declared_monthly_net_income"), "/month")
    if code == "POL-ELG-003": return f"{app.get('employment_length_months', 'n/a')} months"
    if code in ("POL-SCR-001",): return str(app.get("credit_score", "n/a"))
    if code == "POL-SCR-002": return f"bankruptcies={app.get('bankruptcies_count', 'n/a')}, tax liens={app.get('tax_liens_count', 'n/a')}"
    if code == "POL-DTI-001": return _num(fin.get("dti_pct"), ".1f", "%")
    if code == "POL-LTI-001": return _num(fin.get("lti_ratio"), ".2f", "x")
    if code == "POL-NDI-001":
        buffer = ndi_buffer(app.get("dependents_count"))
        base = _money(fin.get("ndi_amount"))
        return base if buffer is None else f"{base} (buffer ${buffer:,.0f})"
    if code == "POL-INC-001": return _num(fin.get("income_variance_pct"), ".1f", "%")
    if code == "POL-TXN-001": return _num(txn.get("gambling_pct_of_income"), ".1f", "% of income")
    if code == "POL-TXN-002": return f"{txn.get('nsf_event_count', 'n/a')} events"
    if code == "POL-TXN-003": return _money(txn.get("undisclosed_debt_total"), "/month")
    if code == "POL-TXN-004": return f"{len(txn.get('window_dressing_events') or [])} event(s)"
    if code == "POL-TXN-005": return str(txn.get("burn_rate_status", "n/a"))
    return "n/a"


def ml_summary(result: dict, ml_reason: str | None, applicant_id: str | None = None) -> dict:
    ml = result.get("ml") or {}
    if ml.get("risk_score") is not None:
        return {"available": True, "precomputed": False, "score": ml["risk_score"], "level": ml.get("risk_level"),
                "text": f"ML risk score {ml['risk_score']:.3f} ({ml.get('risk_level')}) - live model"}
    reason = ml_reason
    if reason is None:
        errors = [e["message"] for e in result["system"]["errors"] if e["category"] == "ml_failure"]
        reason = errors[-1] if errors else "ML scoring was not enabled"
    # Live scoring failed: show the stored batch prediction, clearly labelled, if this applicant has one.
    row = precomputed_prediction(applicant_id) if applicant_id else None
    if row:
        return {"available": True, "precomputed": True, "score": row["score"], "level": row["level"],
                "text": (f"ML risk score {row['score']:.3f} ({row['level']}) - precomputed batch prediction "
                         f"(data/processed/ml_predictions.csv); live scoring unavailable: {reason}")}
    return {"available": False, "precomputed": False, "score": None, "level": None,
            "text": f"ML scoring unavailable: {reason}"}


def build_view(case: dict, application: dict, result: dict, banner: str, azure_mode: bool,
               ml_reason: str | None = None) -> dict:
    report = result["report"]
    policy = report["policy_assessment"]
    rules = [{"code": code, "title": RULE_TITLES.get(code, code), "status": status,
              "value": rule_value(code, application, report)} for code, status in policy.items()]
    return {
        "applicant_id": case["applicant_id"],
        "name": case.get("full_name", ""),
        "loan": f"${application.get('requested_loan_amount', 0):,.0f} over {application.get('loan_term_months', '?')} months",
        "expected_verdict": case.get("expected_verdict"),  # shown only after the run, never given to the engine
        "verdict": report["final_decision"]["verdict"],
        "driver": report["final_decision"]["primary_driver"],
        "driver_title": RULE_TITLES.get(report["final_decision"]["primary_driver"], ""),
        "rules": rules,
        "data_gaps": report.get("data_gaps", []),
        "ml": ml_summary(result, ml_reason, case["applicant_id"]),
        "evidence": result["evidence"],
        "cross_check": report.get("policy_cross_check", {}),
        "system": result["system"],
        "banner": banner,
        "azure_mode": azure_mode,
        "financial": report["financial_assessment"],
        "transactions": report["transaction_assessment"],
    }
