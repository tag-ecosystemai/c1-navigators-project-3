from ai_engineering.orchestrator.orchestrator import investigate
import pandas as pd
import joblib
from pathlib import Path

# --- Helper to add PD scores ---
def add_pd_scores():
    DATA_DIR = Path("data/processed")
    MODEL_PATH = Path("models/risk_model.pkl")

    # Load trained model
    model = joblib.load(MODEL_PATH)

    # Load features
    X = pd.read_csv(DATA_DIR / "ml_features.csv")

    # Predict probabilities (PD = probability of default)
    pd_scores = model.predict_proba(X)[:, 1]

    # Attach predictions to applicants
    training_view = pd.read_csv(DATA_DIR / "ml_training_view.csv")
    training_view["predicted_pd"] = pd_scores

    # Save enriched view
    training_view.to_csv(DATA_DIR / "ml_predictions.csv", index=False)

    # Return a preview dataframe
    return training_view[["applicant_id", "expected_verdict", "default_flag", "predicted_pd"]]

# --- Sample orchestrator input ---
sample_input = {
    "application": {
        "income": 5000,
        "expenses": 2000,
        "loan_amount": 15000,
        "tenure_months": 24
    },
    "transactions": [],
    "policies": []
}

# --- Run orchestrator ---
result = investigate(sample_input)
print("Orchestrator result:")
print(result)

# --- Run PD scoring ---
pd_results = add_pd_scores()
print("\nRisk predictions with PD scores:")
print(pd_results.head(10))
