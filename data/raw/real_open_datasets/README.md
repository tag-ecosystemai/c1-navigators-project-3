# Real Open Credit Benchmark Dataset: UCI Statlog (German Credit Data)

## 1. Dataset Overview & Academic Source
* **Title:** German Credit Data (Statlog Project)
* **Original Repository:** [UCI Machine Learning Repository (Dataset ID: 144)](https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data)
* **Author / Donor:** Prof. Dr. Hans Hofmann, Institut für Statistik und Ökonometrie, Universität Hamburg
* **File Location:** [`data/raw/real_open_datasets/uci_german_credit.csv`](uci_german_credit.csv)
* **Records:** 1,000 real individual banking loan records
* **Attributes:** 20 predictor attributes (7 numerical, 13 categorical) + 1 target variable (`credit_risk`)

---

## 2. Pedagogical Purpose: Predictive ML vs. Generative AI

This dataset perfectly illustrates the division of labor in modern AI banking architectures:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               AI BANKING ARCHITECTURE                                  │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│      1. PREDICTIVE ML (Supervised)       │       2. GENERATIVE AI (LLM / RAG)          │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ • Trained on: Historical tabular credit  │ • Grounded on: Official public regulatory   │
│   datasets (e.g., UCI German Credit).    │   statutes (CFPB, FCA, OCC guidelines).     │
│ • Algorithm: Logistic Regression,        │ • Architecture: RAG (Vector DB) + Agent     │
│   Random Forest, XGBoost, LightGBM.      │   Function/Tool Calling.                    │
│ • Output: Quantitative Probability of     │ • Output: Contextual analysis, transaction  │
│   Default (PD), credit risk score (0/1). │   red-flag synthesis, narrative audit report│
│ • Strengths: Fast statistical risk       │ • Strengths: Interprets complex text rules, │
│   classification, calibrated scoring.    │   detects nuances, explains evidence to human│
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 3. Data Dictionary: `uci_german_credit.csv`

| Column | Type | Description | Values / Categories |
|---|---|---|---|
| `status` | Categorical | Status of existing checking account | `< 100 DM`, `0 <= ... < 200 DM`, `>= 200 DM`, `no checking account` |
| `duration` | Numerical | Duration of the loan in months | 4 to 72 months |
| `credit_history` | Categorical | Past credit repayment history | `critical account/other credits`, `existing credits paid back duly`, `delay in paying off in the past`, `all credits paid back duly` |
| `purpose` | Categorical | Purpose of the credit | `car (new)`, `car (used)`, `domestic appliances`, `radio/television`, `repairs`, `education`, `business`, `retraining` |
| `amount` | Numerical | Credit amount in Deutsche Mark (DM) | 250 to 18,424 DM |
| `savings` | Categorical | Savings account balance / bonds | `< 100 DM`, `100 <= ... < 500 DM`, `500 <= ... < 1000 DM`, `>= 1000 DM`, `unknown/no savings` |
| `employment_duration` | Categorical | Present employment duration | `< 1 year`, `1 <= ... < 4 years`, `4 <= ... < 7 years`, `>= 7 years`, `unemployed` |
| `installment_rate` | Numerical | Installment rate in % of disposable income | 1%, 2%, 3%, 4% |
| `personal_status_sex` | Categorical | Gender and marital status | `male : single`, `male : married/widowed`, `female : divorced/separated/married`, `male : divorced/separated` |
| `other_debtors` | Categorical | Other debtors or guarantors | `none`, `co-applicant`, `guarantor` |
| `present_residence` | Numerical | Present residence duration in years | 1 to 4 years |
| `property` | Categorical | Real estate / life insurance / car / no property | `real estate`, `building society savings/life insurance`, `car or other`, `unknown / no property` |
| `age` | Numerical | Age in years | 19 to 75 years |
| `other_installment_plans` | Categorical | Other installment plans at banks or stores | `bank`, `stores`, `none` |
| `housing` | Categorical | Housing situation | `own`, `rent`, `for free` |
| `number_credits` | Numerical | Number of existing credits at this bank | 1 to 4 |
| `job` | Categorical | Employment skill classification | `unemployed/unskilled - non-resident`, `unskilled - resident`, `skilled employee/official`, `management/self-employed/highly qualified` |
| `people_liable` | Numerical | Number of people being liable for maintenance | 1 or 2 |
| `telephone` | Categorical | Registered telephone number | `yes`, `no` |
| `foreign_worker` | Categorical | Foreign worker status | `yes`, `no` |
| **`credit_risk`** | **Target (Binary)** | **Ground Truth Credit Classification** | **`1 = Good Credit (No Default)`**, **`0 = Bad Credit (Default / High Risk)`** |

---

## 4. Quick-Start for AI Engineering (Predictive ML Model)

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# 1. Load real open credit dataset
df = pd.read_csv("data/raw/real_open_datasets/uci_german_credit.csv")

# 2. Separate features and target
X = pd.get_dummies(df.drop("credit_risk", axis=1), drop_first=True)
y = df["credit_risk"]

# 3. Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 4. Train predictive credit risk model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
```
