import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_engineering.ml_scoring.model_features import FEATURES, derive_features  # noqa: E402

DATA_DIR = Path("data/processed")

def load_data():
    apps = pd.read_csv(DATA_DIR / "applications.csv")
    txns = pd.read_csv(DATA_DIR / "transactions.csv")
    return apps, txns

def derive_default_flag(df: pd.DataFrame) -> pd.Series:
    # Target: applicants flagged as decline recommended
    return (df["expected_verdict"] == "DECLINE_RECOMMENDED").astype(int)

def aggregate_transactions(txns: pd.DataFrame) -> pd.DataFrame:
    grouped = txns.groupby("applicant_id").agg(
        monthly_inflows=("amount", lambda x: x[txns.loc[x.index, "type"] == "CREDIT"].sum()),
        monthly_outflows=("amount", lambda x: x[txns.loc[x.index, "type"] == "DEBIT"].sum()),
        gambling_spend=("amount", lambda x: x[txns.loc[x.index, "category"] == "GAMBLING"].sum()),
        anomaly_count=("flagged_anomaly", "sum"),
        txn_count=("amount", "count"),
        avg_txn_amount=("amount", "mean"),
    )
    return grouped.reset_index()

def build_features(apps: pd.DataFrame, txns_agg: pd.DataFrame, txns: pd.DataFrame) -> pd.DataFrame:
    """Applicants with transactions (inner join, as before) plus the model features.

    The 20 features come from ai_engineering.ml_scoring.model_features.derive_features, the same
    function the live engine uses to score a case, so training and scoring cannot drift apart.
    """
    df = apps.merge(txns_agg, on="applicant_id", how="inner")
    by_applicant = {key: group.to_dict("records") for key, group in txns.groupby("applicant_id")}

    features = pd.DataFrame(
        [derive_features(row, by_applicant[row["applicant_id"]]) for row in df.to_dict("records")],
        columns=list(FEATURES),
        index=df.index,
    )
    for column in FEATURES:
        df[column] = features[column]
    return df, features

def main():
    apps, txns = load_data()
    txns_agg = aggregate_transactions(txns)

    df, X = build_features(apps, txns_agg, txns)

    df["default_flag"] = derive_default_flag(df)
    y = df["default_flag"]

    df.to_csv(DATA_DIR / "ml_training_view.csv", index=False)
    X.to_csv(DATA_DIR / "ml_features.csv", index=False)
    y.to_csv(DATA_DIR / "ml_labels.csv", index=False)

    print("Saved ml_training_view.csv, ml_features.csv, ml_labels.csv")

if __name__ == "__main__":
    main()
