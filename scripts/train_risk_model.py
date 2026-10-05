import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from xgboost import XGBClassifier
import joblib

DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

def load_ml_data():
    X = pd.read_csv(DATA_DIR / "ml_features.csv")
    y = pd.read_csv(DATA_DIR / "ml_labels.csv").squeeze()
    return X, y

def train_and_evaluate():
    X, y = load_ml_data()

    print("X shape:", X.shape)
    print("y shape:", y.shape)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    #  FIX: handle class imbalance
    model = XGBClassifier(
        max_depth=4,
        learning_rate=0.05,
        n_estimators=300,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=5   
    )

    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = {
        "auc_roc": roc_auc_score(y_test, y_prob),
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_importance": dict(zip(X.columns, model.feature_importances_.tolist())),
    }

    joblib.dump(model, MODEL_DIR / "risk_model.pkl")

    print("Model saved to models/risk_model.pkl")
    print("Metrics:")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    pd.DataFrame.from_dict(metrics["feature_importance"], orient="index", columns=["importance"])\
        .sort_values("importance", ascending=False)\
        .to_csv(MODEL_DIR / "feature_importance.csv")

if __name__ == "__main__":
    train_and_evaluate()
