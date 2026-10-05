import pandas as pd
from pathlib import Path

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

def build_features(apps: pd.DataFrame, txns_agg: pd.DataFrame) -> pd.DataFrame:
    df = apps.merge(txns_agg, on="applicant_id", how="inner")

    # Financial capacity
    df["dti"] = df["calculated_dti_pct"]
    df["loan_to_income"] = df["requested_loan_amount"] / (df["declared_monthly_net_income"] + 1e-6)
    df["expense_to_income"] = df["declared_monthly_housing_expense"] / (df["declared_monthly_net_income"] + 1e-6)
    df["debt_to_income"] = df["declared_existing_monthly_debt"] / (df["declared_monthly_net_income"] + 1e-6)

    # Creditworthiness
    df["credit_score"] = df["credit_score"]
    df["credit_score_tier_num"] = df["credit_score_tier"].map({
        "TIER_1_PRIME": 1,
        "TIER_2_NEAR_PRIME": 2,
        "TIER_3_SUBPRIME": 3,
        "TIER_4_HIGH_RISK": 4
    }).fillna(0)

    # Behavioral risk
    df["income_stability"] = (df["declared_monthly_net_income"] - df["actual_monthly_salary"]).abs() / (df["actual_monthly_salary"] + 1e-6)
    df["gambling_ratio"] = df["gambling_spend"] / (df["actual_monthly_salary"] + 1e-6)
    df["savings_rate"] = (
        df["actual_monthly_salary"]
        - df["declared_existing_monthly_debt"]
        - df["declared_monthly_housing_expense"]
    ) / (df["actual_monthly_salary"] + 1e-6)

    # Repayment burden
    df["monthly_payment_ratio"] = df["estimated_monthly_payment"] / (df["declared_monthly_net_income"] + 1e-6)
    df["lti_ratio"] = df["calculated_lti_ratio"]

    # Transactional dynamics
    df["anomaly_score"] = df["anomaly_count"]
    df["txn_density"] = df["txn_count"] / df["loan_term_months"].clip(lower=1)
    df["avg_txn_amount"] = df["avg_txn_amount"]

    # Demographic / structural
    df["dependents_count"] = df["dependents_count"]
    df["bankruptcies_count"] = df["bankruptcies_count"]
    df["tax_liens_count"] = df["tax_liens_count"]
    df["employment_length_months"] = df["employment_length_months"]

    feature_cols = [
        "dti",
        "loan_to_income",
        "expense_to_income",
        "debt_to_income",
        "credit_score",
        "credit_score_tier_num",
        "income_stability",
        "gambling_ratio",
        "savings_rate",
        "monthly_payment_ratio",
        "lti_ratio",
        "monthly_inflows",
        "monthly_outflows",
        "anomaly_score",
        "txn_density",
        "avg_txn_amount",
        "dependents_count",
        "bankruptcies_count",
        "tax_liens_count",
        "employment_length_months",
    ]

    X = df[feature_cols].fillna(0.0)
    return df, X

def main():
    apps, txns = load_data()
    txns_agg = aggregate_transactions(txns)

    df, X = build_features(apps, txns_agg)

    df["default_flag"] = derive_default_flag(df)
    y = df["default_flag"]

    df.to_csv(DATA_DIR / "ml_training_view.csv", index=False)
    X.to_csv(DATA_DIR / "ml_features.csv", index=False)
    y.to_csv(DATA_DIR / "ml_labels.csv", index=False)

    print("Saved ml_training_view.csv, ml_features.csv, ml_labels.csv")

if __name__ == "__main__":
    main()
