"""ML features: the engine builds exactly the 20 features the model was trained on."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from ai_engineering.ml_scoring import ml_integration
from ai_engineering.ml_scoring.feature_builder import feature_result
from ai_engineering.ml_scoring.model_features import FEATURES, derive_features

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def _optional(module: str):
    """Import an optional heavy dependency, or skip. Catches any failure, not only ImportError: a blocked DLL
    (Windows Application Control) can leave a half-initialised module that raises AttributeError later."""
    import importlib

    try:
        return importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{module} cannot be imported here: {type(exc).__name__}")


def _load():
    features = list(csv.DictReader(open(PROCESSED / "ml_features.csv", encoding="utf-8")))
    apps = json.loads((PROCESSED / "applications.json").read_text(encoding="utf-8"))
    txns: dict[str, list] = {}
    for t in json.loads((PROCESSED / "transactions.json").read_text(encoding="utf-8")):
        txns.setdefault(t["applicant_id"], []).append(t)
    return features, apps, txns


def test_feature_names_and_order_match_the_training_file():
    header = next(csv.reader(open(PROCESSED / "ml_features.csv", encoding="utf-8")))
    assert tuple(header) == FEATURES and len(FEATURES) == 20


def test_engine_features_equal_ml_features_csv_for_every_applicant():
    rows, apps, txns = _load()
    assert len(rows) == len(apps) == 50
    for row, app in zip(rows, apps):
        got = derive_features(app, txns[app["applicant_id"]])
        for name in FEATURES:
            assert math.isclose(got[name], float(row[name]), rel_tol=1e-9, abs_tol=1e-9), (app["applicant_id"], name)


def test_missing_inputs_become_zero_like_the_training_fillna():
    got = derive_features({}, [])
    assert set(got) == set(FEATURES) and all(v == 0.0 for v in got.values())


def test_precomputed_application_ratios_fall_back_to_engine_metrics():
    got = derive_features({}, [], {"dti_pct": 21.5, "lti_ratio": 0.3, "proposed_monthly_payment": 400.0})
    assert got["dti"] == 21.5 and got["lti_ratio"] == 0.3
    got = derive_features({"declared_monthly_net_income": 4000}, [], {"proposed_monthly_payment": 400.0})
    assert got["monthly_payment_ratio"] == pytest.approx(400.0 / 4000.0, rel=1e-6)


def test_feature_result_feeds_the_model_in_its_trained_order(monkeypatch):
    _, apps, txns = _load()
    app = apps[0]
    case = {"application": app, "transactions": txns[app["applicant_id"]], "ml": {"enabled": True}}
    built = feature_result(case, {}, {}, {})
    assert built["status"] == "ok" and list(built["data"]["features"]) == list(FEATURES)

    seen = {}

    class FakeModel:
        feature_names_in_ = np.array(list(reversed(FEATURES)))  # a different order: must be respected

        def predict_proba(self, x):
            seen["x"] = x
            return np.array([[0.2, 0.8]])

    monkeypatch.setattr(ml_integration, "_load_model", lambda: FakeModel())
    out = ml_integration.integrate_ml(case, built["data"])
    assert out["data"]["risk_score"] == pytest.approx(0.8) and out["data"]["risk_level"] == "HIGH_RISK"
    assert seen["x"].shape == (1, 20)
    assert seen["x"][0][0] == built["data"]["features"][FEATURES[-1]]  # first column = model's first name


def test_risk_levels():
    assert [ml_integration.level_for(p) for p in (0.1, 0.4, 0.5, 0.7, 0.9)] == [
        "LOW_RISK", "LOW_RISK", "MEDIUM_RISK", "MEDIUM_RISK", "HIGH_RISK"]


def test_training_script_uses_the_shared_features():
    pd = _optional("pandas")
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_ml_dataset as script

    apps, txns = script.load_data()
    df, X = script.build_features(apps, script.aggregate_transactions(txns), txns)
    reference = pd.read_csv(PROCESSED / "ml_features.csv")
    assert list(X.columns) == list(reference.columns)
    assert np.allclose(X.values, reference.values, rtol=1e-9, atol=1e-9)


def test_live_scores_match_ml_predictions_csv():
    """Ground truth: the stored batch predictions. Skipped where xgboost is not installed."""
    _optional("xgboost")
    try:
        import joblib

        joblib.load(ml_integration.MODEL_PATH)
    except Exception as exc:  # noqa: BLE001 - e.g. scikit-learn blocked on this machine
        pytest.skip(f"model cannot be loaded here: {type(exc).__name__}")
    from ai_engineering.orchestrator.orchestrator import investigate
    from ai_engineering.rag import mode

    mode.force_offline()
    expected = {r["applicant_id"]: float(r["predicted_pd"]) for r in csv.DictReader(open(PROCESSED / "ml_predictions.csv", encoding="utf-8"))}
    _, apps, txns = _load()
    for app in apps:
        got = investigate({"application": app, "transactions": txns[app["applicant_id"]], "ml": {"enabled": True}})["ml"]
        assert got["risk_score"] == pytest.approx(expected[app["applicant_id"]], abs=1e-6), app["applicant_id"]
        assert got["risk_level"] == ml_integration.level_for(expected[app["applicant_id"]])
