# ai_engineering/ml_scoring/ml_integration.py
from ..utils.error_handler import log_error, module_result
import joblib
import numpy as np
from pathlib import Path

from .model_features import FEATURES

# Absolute, so scoring works from any working directory.
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "risk_model.pkl"
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

def level_for(prob):
    return "HIGH_RISK" if prob > 0.7 else "MEDIUM_RISK" if prob > 0.4 else "LOW_RISK"


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
        # The 20 named features, in the column order the model was trained with.
        features = feature_vector["features"]
        order = list(getattr(model, "feature_names_in_", FEATURES))
        x = np.array([features[name] for name in order], dtype=float).reshape(1, -1)

        prob = float(model.predict_proba(x)[0][1])
        risk_level = level_for(prob)

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
