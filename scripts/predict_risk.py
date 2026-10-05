import pandas as pd
import joblib
from pathlib import Path

# Paths
DATA_DIR = Path("data/processed")
MODEL_PATH = Path("models/risk_model.pkl")

# Load trained model
model = joblib.load(MODEL_PATH)

# Load features (X) and labels (y) if you want to test on training data
X = pd.read_csv(DATA_DIR / "ml_features.csv")
y = pd.read_csv(DATA_DIR / "ml_labels.csv")

# Predict probabilities (PD = probability of default)
pd_scores = model.predict_proba(X)[:, 1]  # column 1 = probability of class "1" (default)

# Attach predictions to applicants
training_view = pd.read_csv(DATA_DIR / "ml_training_view.csv")
training_view["predicted_pd"] = pd_scores

# Show a few results
print(training_view[["applicant_id", "expected_verdict", "default_flag", "predicted_pd"]].head(10))

# Save predictions for inspection
training_view.to_csv(DATA_DIR / "ml_predictions.csv", index=False)
print("Predictions saved to ml_predictions.csv")
