# ai_engineering/ml_scoring/ml_integration.py
from ..utils.error_handler import log_error, module_result
import joblib
import numpy as np
from pathlib import Path

MODEL_PATH = Path("models") / "risk_model.pkl"
_model = None

def _load_model():
    global _model
    if _model is None:
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception as exc:
            _model = None
            print(f"Failed to load ML model: {exc}")
    return _model

def integrate_ml(input_data, feature_vector):
    config = input_data.get("ml", {})
    if not config.get("enabled", False):
        return module_result(
            "ml_integration",
            {"risk_score": None, "risk_level": "unknown", "feature_importance": None, "status": "fallback"},
            [],
            [],
            "fallback",
        )

    model = _load_model()
    if model is None:
        return module_result(
            "ml_integration",
            {"risk_score": None, "risk_level": "unknown", "feature_importance": None, "status": "fallback"},
            [],
            [log_error("ml_failure", "ML model unavailable", "ml_integration")],
            "fallback",
        )

    try:
        # feature_vector["features"] should match the 8 features in order
        features = feature_vector["features"]
        x = np.array([
            features["dti"],
            features["income_stability"],
            features["gambling_ratio"],
            features["variance_score"],
            features["monthly_inflows"],
            features["monthly_outflows"],
            features["savings_rate"],
            features["anomaly_score"],
        ], dtype=float).reshape(1, -1)

        prob = float(model.predict_proba(x)[0][1])
        if prob > 0.7:
            risk_level = "HIGH_RISK"
        elif prob > 0.4:
            risk_level = "MEDIUM_RISK"
        else:
            risk_level = "LOW_RISK"

        # Optional: load feature importance from file if you want to expose it
        return module_result(
            "ml_integration",
            {
                "risk_score": prob,
                "risk_level": risk_level,
                "feature_importance": None,  # or load from feature_importance.csv
                "status": "ok",
            },
            [],
        )
    except Exception as exc:
        return module_result(
            "ml_integration",
            {"risk_score": None, "risk_level": "unknown", "feature_importance": None, "status": "fallback"},
            [],
            [log_error("ml_failure", str(exc), "ml_integration")],
            "fallback",
        )
