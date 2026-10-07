# Data Dictionary & Team Handoff Guide
**Project:** AI Credit-Risk Investigation Agent (Team Navigators)  
**Lead / Prepared By:** Dainty (Data Sourcing)  
**Date:** March 2026  

---

## 1. Overview of Data Deliverables
This repository contains a complete, production-grade data suite designed specifically to fulfill all requirements outlined in **Section 8** and **Section 11** of the PRD.

```text
Credit-Risk/
├── data/
│   ├── DATA_DICTIONARY.md           <-- You are here
│   ├── policies/                    <-- For Gabriel & Hannah (Vector DB / RAG)
│   │   ├── 01_general_credit_eligibility_policy.md
│   │   ├── 02_affordability_and_debt_service_policy.md
│   │   ├── 03_bank_statement_and_transaction_investigation_policy.md
│   │   ├── 04_underwriting_referral_and_exception_matrix.md
│   │   └── README.md
│   ├── processed/                   <-- For Ruffy (DB/API) & Danny (Frontend UI)
│   │   ├── applications.csv         (50 applicants)
│   │   ├── applications.json
│   │   ├── transactions.csv         (3,590 90-day bank transactions)
│   │   └── transactions.json
│   └── test_cases/
│       └── golden_demo_cases.json   <-- 5 Flagship Personas for Live Demos
└── scripts/
    └── generate_synthetic_data.py   <-- Standalone generator (no external dependencies)
```

---

## 2. Table Schema: `applications.csv`

| Column Name | Type | Description | PRD Feature / Usage |
|---|---|---|---|
| `applicant_id` | String | Unique customer identifier (`CUST-1001`, `CUST-GOLD-001`) | Primary Key for Customer Profile |
| `application_id` | String | Unique loan application identifier (`APP-2026-001`) | Case Management / Investigation ID |
| `full_name` | String | Applicant full legal name | Frontend display & report header |
| `age` | Integer | Applicant age in years | Rule `POL-ELG-001` (21 - 68 yrs) |
| `email` / `phone` | String | Contact information | Contact & identity verification |
| `address` | String | Residential address | KYC address check |
| `housing_status` | Enum | `RENT`, `MORTGAGE`, `OWN` | Financial commitment analysis |
| `employment_status` | Enum | `EMPLOYED_FULL_TIME`, `PART_TIME`, `SELF_EMPLOYED` | Rule `POL-ELG-003` |
| `employer_name` | String | Current employer | Payroll match verification |
| `job_title` | String | Role / occupation | Income stability assessment |
| `employment_length_months` | Integer | Tenure with current employer | Rule `POL-ELG-003` (min 6 months) |
| `declared_annual_income` | Float | Stated gross annual income | Affordability calculations |
| `declared_monthly_net_income` | Float | Stated take-home monthly salary | Rule `POL-ELG-002` (min $2,000/mo) |
| `actual_monthly_salary` | Float | True recurring salary verified in bank statement | Ground truth for Rule `POL-INC-001` variance |
| `credit_score` | Integer | Primary credit bureau score (300 - 850) | Rule `POL-SCR-001` Tiers (1 to 4) |
| `credit_score_tier` | Enum | `TIER_1_PRIME`, `TIER_2_NEAR_PRIME`, `TIER_3_SUBPRIME`, `TIER_4_HIGH_RISK` | Underwriting speed & loan cap matrix |
| `requested_loan_amount` | Float | Requested principal ($2,000 to $50,000) | Loan sizing & LTI evaluation |
| `loan_purpose` | Enum | `DEBT_CONSOLIDATION`, `HOME_IMPROVEMENT`, `MAJOR_PURCHASE`, etc. | Policy permissible use check |
| `loan_term_months` | Integer | 12, 24, 36, 48, or 60 months | Amortization schedule |
| `interest_rate_pct` | Float | Annual percentage rate (APR) | Debt service calculation |
| `estimated_monthly_payment` | Float | Calculated monthly installment | Rule `POL-DTI-001` |
| `declared_existing_monthly_debt` | Float | Stated existing debts (auto, cards) | Declared DTI component |
| `declared_monthly_housing_expense` | Float | Rent or mortgage monthly payment | Net Disposable Income buffer check |
| `declared_monthly_living_expenses` | Float (optional) | Stated monthly living costs (food, utilities, transport), excluding housing and debt payments. Not present in `applications.csv`; the 5 golden personas carry synthetic values (about 25–40% of net income) pending confirmation by the data owner. If absent, `POL-NDI-001` is reported as `MISSING_DATA` (no default is assumed) | Net Disposable Income, Rule `POL-NDI-001` |
| `dependents_count` | Integer | Number of dependent children/relatives | Rule `POL-NDI-001` living allowance |
| `bankruptcies_count` | Integer | Adverse public records | Rule `POL-SCR-002` knockout |
| `tax_liens_count` | Integer | Outstanding government liens | Rule `POL-SCR-002` knockout |
| `calculated_dti_pct` | Float | Stated Debt-to-Income ratio (%) | Rule `POL-DTI-001` |
| `calculated_lti_ratio` | Float | Loan-to-Income multiplier | Rule `POL-LTI-001` |
| `persona_type` | String | `GOLDEN_*` or `STANDARD_SYNTHETIC` | Test suite categorization |
| `expected_verdict` | Enum | `ELIGIBLE_FOR_APPROVAL`, `FURTHER_REVIEW_REQUIRED`, `DECLINE_RECOMMENDED` | Benchmark evaluation for AI Agent |
| `notes` | String | Human analyst explanation of the case | Ground truth summary |

---

## 3. Table Schema: `transactions.csv`

| Column Name | Type | Description | PRD Feature / Usage |
|---|---|---|---|
| `transaction_id` | String | Unique transaction record ID (`TXN-CUST-1001-0001`) | Primary Key |
| `applicant_id` | String | Foreign key linking directly to `applications.csv` | Cross-source query & investigation |
| `account_id` | String | Customer bank checking account number | Account metadata |
| `date` | Date (`YYYY-MM-DD`) | Transaction execution timestamp (90-day time series) | Temporal cash flow trends |
| `type` | Enum | `CREDIT` (deposit/inflow) or `DEBIT` (withdrawal/outflow) | Balance accounting |
| `category` | Enum | `PAYROLL`, `HOUSING_RENT`, `MORTGAGE`, `UTILITIES`, `GROCERIES`, `FOOD_DINING`, `TRANSPORTATION`, `DEBT_SERVICE_DECLARED`, `DEBT_SERVICE_UNDISCLOSED`, `GAMBLING`, `BANK_FEE`, `CASH_DEPOSIT_UNUSUAL`, `TRANSFER_OUT` | Category-based risk investigation |
| `amount` | Float | Transaction amount in USD | Numerical analysis |
| `running_balance` | Float | True ledger balance after each transaction | Rule `POL-TXN-005` (burn rate / overdraft) |
| `merchant_or_description` | String | Raw text description (e.g., "DraftKings Interactive", "Klarna Installment #2", "Apex Healthcare - DIRECT DEP PAYROLL") | Natural Language / Tool query matching |
| `flagged_anomaly` | Boolean | Ground truth flag (`True`/`False`) indicating policy breach | Anomaly Detection evaluation metric |
| `anomaly_reason` | String | Policy rule breached (e.g. `GAMBLING_EXCESSIVE`, `NSF_RETURNED_ITEM_FEE`, `UNDISCLOSED_DEBT_OBLIGATION`, `WINDOW_DRESSING_DEPOSIT`) | Ground truth audit label |

---

## 4. The 5 Golden Demo Personas (For Live Presentations & Testing)

These 5 personas are pre-configured to showcase each distinct feature of the AI Agent:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. CUST-GOLD-001: Sarah Jenkins (Prime Low-Risk Approval)                              │
│    • Credit Score: 760 (Tier 1 Prime)                                                  │
│    • Income: $5,000/mo verified exactly with 2x $2,500 semi-monthly deposits           │
│    • DTI: 18.3% (Well below 35% cap)                                                   │
│    • Transactions: 0 NSF fees, $0 gambling, healthy $12,500 balance                       │
│    • Expected Verdict: ELIGIBLE_FOR_APPROVAL                                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. CUST-GOLD-002: Marcus Vance (Income Falsification & Window Dressing)                 │
│    • Declared Income: $7,500/mo ($90k/yr)                                              │
│    • Verified Bank Deposits: Only $3,200/mo (57% Discrepancy! Breaches POL-INC-001)   │
│    • Window Dressing: $15,000 unverified wire deposit 12 days before loan application   │
│    • Expected Verdict: FURTHER_REVIEW_REQUIRED / SUSPECTED_MISREPRESENTATION          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. CUST-GOLD-003: Chloe Bennett (Hidden Behavioral Risk: Gambling & Overdraft Spiral) │
│    • Credit Score: 655 (Appears acceptable on surface)                                 │
│    • Gambling: 14 gambling transactions in 90 days (>35% of income! Breaches TXN-001) │
│    • Overdrafts: 4 NSF fees of $35 in 60 days; chronic negative balance breaches       │
│    • Expected Verdict: DECLINE_RECOMMENDED / SEVERE_BEHAVIORAL_RISK                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. CUST-GOLD-004: David O'Connor (Shadow Debt / Undisclosed BNPL Stacking)             │
│    • Stated DTI: 19.2% (Appears healthy with only a $350 car loan declared)            │
│    • Bank Transactions Reveal: $740/mo in recurring undisclosed debt: Klarna ($180),   │
│      Affirm ($140), and Avant Online Credit ($420)                                     │
│    • True Shadow DTI: Breaches 48.2% (Violates POL-TXN-003 & POL-DTI-001)             │
│    • Expected Verdict: FURTHER_REVIEW_REQUIRED / SHADOW_DTI_BREACH                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. CUST-GOLD-005: Elena Rostova (Policy Knockout Breach)                               │
│    • Credit Score: 540 (Below 600 Knockout, POL-SCR-001)                               │
│    • Income: $1,500/mo (Below $2,000 threshold, POL-ELG-002)                           │
│    • Recent bankruptcy record + DTI > 55%                                              │
│    • Expected Verdict: DECLINE_RECOMMENDED (POLICY_KNOCKOUT)                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Team Integration Quick-Start

### For Gabriel & Hannah (AI Engineering)
* **Policy RAG:** Load the markdown files in `data/policies/` into your Vector Store (ChromaDB / Azure AI Search). Chunk by policy section.
* **Anomaly Tool:** Test your prompt-based or rule-based transaction anomaly detector against `transactions.csv` using the `flagged_anomaly` and `anomaly_reason` columns to calculate precision/recall.
* **Report Generation:** Pass the applicant JSON from `data/processed/applications.json` and linked transactions from `transactions.json` into the agent to produce the structured report.

### For Ruffy (Backend)
* Import `applications.csv` and `transactions.csv` directly into your SQLite / PostgreSQL database using SQLAlchemy or FastAPI startup seeds.
* Foreign key: `transactions.applicant_id` $\rightarrow$ `applications.applicant_id`.

### For Danny (Frontend)
* Use the 5 golden personas in `data/test_cases/golden_demo_cases.json` to populate the application selector dropdown in the analyst dashboard.
