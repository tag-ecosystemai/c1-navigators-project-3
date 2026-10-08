from ..utils.error_handler import log_error, module_result
from .model_features import FEATURES, derive_features


def build_features(input_data, financial, transactions, anomalies):
    # The 20 features risk_model.pkl was trained on (see model_features.py). They are derived from the raw
    # application and transactions, the same way as at training time; the engine's own financial metrics
    # are only a fallback for fields the application does not carry precomputed.
    features = derive_features(input_data.get("application", {}), input_data.get("transactions", []), financial)
    return {"model_name": input_data.get("ml", {}).get("model_name", ""), "features": features, "metadata": {"applicant_id": input_data.get("application", {}).get("applicant_id", ""), "request_id": input_data.get("context", {}).get("request_id", ""), "timestamp": input_data.get("context", {}).get("timestamp", "")}}


def feature_result(input_data, financial, transactions, anomalies):
    try: return module_result("feature_builder", build_features(input_data, financial, transactions, anomalies))
    except Exception as exc: return module_result("feature_builder", {}, [], [log_error("ml_failure", str(exc), "feature_builder")], "fallback")
