import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

def load_data():
    apps = pd.read_csv(DATA_DIR / "applications.csv")
    txns = pd.read_csv(DATA_DIR / "transactions.csv")
    return apps, txns

def derive_default_flag(df: pd.DataFrame) -> pd.Series:
    # FINAL FIX: Respect generator's verdict only
    return (df["expected_verdict"] == "DECLINE_RECOMMENDED").astype(int)

def aggregate_transactions(txns: pd.DataFrame) -> pd.DataFrame:
    grouped = txns.groupby("applicant_id").agg(
        monthly_inflows=("amount", lambda x: x[txns.loc[x.index, "type"] == "CREDIT"].sum()),
        monthly_outflows=("amount", lambda x: x[txns.loc[x.index, "type"] == "DEBIT"].sum()),
        gambling_spend=("amount", lambda x: x[txns.loc[x.index, "category"] == "GAMBLING"].sum()),
        anomaly_count=("flagged_anomaly", "sum"),
    )
    return grouped.reset_index()

def build_features(apps: pd.DataFrame, txns_agg: pd.DataFrame) -> pd.DataFrame:
    df = apps.merge(txns_agg, on="applicant_id", how="inner")

    df["dti"] = df["calculated_dti_pct"]
    df["income_stability"] = (df["declared_monthly_net_income"] - df["actual_monthly_salary"]).abs() / df["actual_monthly_salary"]
    df["gambling_ratio"] = df["gambling_spend"] / df["actual_monthly_salary"]
    df["variance_score"] = df["income_stability"]
    df["savings_rate"] = (
        df["actual_monthly_salary"]
        - df["declared_existing_monthly_debt"]
        - df["declared_monthly_housing_expense"]
    ) / df["actual_monthly_salary"]
    df["anomaly_score"] = df["anomaly_count"]

    feature_cols = [
        "dti",
        "income_stability",
        "gambling_ratio",
        "variance_score",
        "monthly_inflows",
        "monthly_outflows",
        "savings_rate",
        "anomaly_score",
    ]

    X = df[feature_cols].fillna(0.0)
    return df, X

def main():
    apps, txns = load_data()
    txns_agg = aggregate_transactions(txns)

    df, X = build_features(apps, txns_agg)

    # FIX: compute default_flag using generator's verdict
    df["default_flag"] = derive_default_flag(df)

    y = df["default_flag"]

    df.to_csv(DATA_DIR / "ml_training_view.csv", index=False)
    X.to_csv(DATA_DIR / "ml_features.csv", index=False)
    y.to_csv(DATA_DIR / "ml_labels.csv", index=False)

    print("Saved ml_training_view.csv, ml_features.csv, ml_labels.csv")

if __name__ == "__main__":
    main()
