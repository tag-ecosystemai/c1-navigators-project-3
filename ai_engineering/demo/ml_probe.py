"""Can the ML model be used here? The demo enables ML scoring only if this says yes."""

from __future__ import annotations

from ..ml_scoring.feature_builder import FEATURES
from .cases import ROOT

MODEL_PATH = ROOT / "models" / "risk_model.pkl"


def ml_status() -> tuple[bool, str]:
    """(usable, reason). Never raises."""
    try:
        import joblib

        model = joblib.load(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001 - report whatever stopped the model loading
        return False, f"{type(exc).__name__}: {exc}"
    expected = getattr(model, "n_features_in_", None)
    if expected is not None and expected != len(FEATURES):
        return False, (f"models/risk_model.pkl expects {expected} features but the engine's feature_builder "
                       f"supplies {len(FEATURES)}")
    return True, "model loaded"
