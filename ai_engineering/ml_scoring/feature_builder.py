from ..utils.error_handler import log_error, module_result

FEATURES = ("dti", "income_stability", "gambling_ratio", "variance_score", "monthly_inflows", "monthly_outflows", "savings_rate", "anomaly_score")


def build_features(input_data, financial, transactions, anomalies):
    values = {"dti": financial.get("dti_pct"), "income_stability": financial.get("income_variance_pct"), "gambling_ratio": transactions.get("gambling_pct_of_income"), "variance_score": financial.get("income_variance_pct"), "monthly_inflows": financial.get("verified_monthly_inflows"), "monthly_outflows": None, "savings_rate": None, "anomaly_score": anomalies.get("anomaly_score")}
    return {"model_name": input_data.get("ml", {}).get("model_name", ""), "features": {key: values[key] for key in FEATURES}, "metadata": {"applicant_id": input_data.get("application", {}).get("applicant_id", ""), "request_id": input_data.get("context", {}).get("request_id", ""), "timestamp": input_data.get("context", {}).get("timestamp", "")}}


def feature_result(input_data, financial, transactions, anomalies):
    try: return module_result("feature_builder", build_features(input_data, financial, transactions, anomalies))
    except Exception as exc: return module_result("feature_builder", {}, [], [log_error("ml_failure", str(exc), "feature_builder")], "fallback")
