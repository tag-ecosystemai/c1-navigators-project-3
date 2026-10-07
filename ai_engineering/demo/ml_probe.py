"""Can the ML model be used here? The demo enables ML scoring only if this says yes."""

from __future__ import annotations

import csv

from ..ml_scoring.ml_integration import MODEL_PATH, level_for
from ..ml_scoring.model_features import FEATURES
from .cases import ROOT

PRECOMPUTED_PATH = ROOT / "data" / "processed" / "ml_predictions.csv"


def precomputed_prediction(applicant_id: str) -> dict | None:
    """The row for this applicant in data/processed/ml_predictions.csv (a batch run), or None."""
    try:
        with open(PRECOMPUTED_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("applicant_id") == applicant_id and row.get("predicted_pd") not in (None, ""):
                    score = float(row["predicted_pd"])
                    return {"score": score, "level": level_for(score)}
    except (OSError, ValueError):
        pass
    return None


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
