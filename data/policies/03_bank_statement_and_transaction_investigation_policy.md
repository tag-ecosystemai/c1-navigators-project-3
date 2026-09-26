# Retail Banking Credit Underwriting Policy
## Document Code: POL-RET-2026-03: Bank Statement & Transaction Investigation Standards
**Classification:** Internal Risk & Underwriting Standard  
**Target Product:** Unsecured Personal Loans  
**Effective Date:** January 1, 2026  
**Audience:** Credit Underwriters, Risk Analysts, AI Anomaly Detection & Investigation Agents

---

### 1. Purpose & Scope
This policy establishes explicit rules and anomaly thresholds for investigating bank account transaction histories (minimum 90-day to 180-day window). The AI agent must run transaction queries and automated anomaly detection against these standards to uncover latent borrower credit risk.

---

### 2. Transaction Red Flags & Behavioral Risk Rules

#### Rule POL-TXN-001: Gambling & High-Risk Speculation
* **Definition:** Debits categorized under betting houses, online casinos, bookmakers, lottery syndicates, or high-risk crypto platforms.
* **Evaluation Metrics (over 90-day review period):**
  * **Low / Acceptable:** Total gambling expenditure $< 3.0\%$ of monthly net income with no consecutive daily losses.
  * **Moderate / Monitor:** Gambling between $3.0\%$ and $10.0\%$ of monthly net income.
  * **High Risk / Policy Violation (Mandatory Review):**
    * Cumulative gambling spend exceeds **$10.0\%$ of net monthly income**, OR
    * More than **4 discrete gambling transactions** per calendar month, OR
    * Any single gambling transaction exceeding **$500 USD**.
* **Compliance Status:**
  * **Satisfied:** No gambling or gambling $< 3\%$.
  * **Flag for Review:** High gambling frequency or spend between $3.1\%$ and $10.0\%$.
  * **Not Satisfied (Decline / Critical Risk):** Gambling spend $> 10\%$ of income or evident signs of gambling-induced distress.

#### Rule POL-TXN-002: Overdrafts, NSF Fees & Returned Items
* **Definition:** Account balance breaching zero into unauthorized overdraft, returned item fees, Non-Sufficient Funds (NSF) charges, or failed automated direct debits.
* **Evaluation Metrics (past 90 days):**
  * **Satisfied (Clean):** 0 unauthorized overdraft events and 0 NSF fees.
  * **Caution (Tolerable):** Exactly 1 isolated NSF or temporary overdraft occurrence occurring more than 60 days prior.
  * **High Risk / Flag for Review:** **2 to 3 NSF / returned payment events** in the last 90 days.
  * **Not Satisfied (Knockout / Severe Distress):** **$\ge$ 4 NSF events** in 90 days, or persistent unauthorized negative balance for more than 5 consecutive banking days.

#### Rule POL-TXN-003: Undisclosed Debt Obligations & Hidden Borrowing
* **Definition:** Recurring debit payments to third-party financial institutions, micro-lenders, payday loan apps, peer-to-peer lenders, or Buy Now Pay Later (BNPL) providers (e.g., Klarna, Affirm, Afterpay) that were **not declared** in the initial credit application.
* **Policy Rule:**
  * The agent must aggregate all unlisted loan/credit payments detected in bank transactions.
  * These monthly payments must be factored into a **recalculated "Shadow DTI"**.
* **Compliance Status:**
  * **Satisfied:** All recurring debt payments correspond to declared liabilities.
  * **Flag for Review:** Undisclosed recurring commitments detected totaling $< \$250/\text{month}$, and revised DTI remains $\le 43\%$.
  * **Not Satisfied / Escalation Required:** Undisclosed debt exceeds $\$250/\text{month}$, OR causes revised DTI to breach the $43\%$ threshold, indicating deliberate non-disclosure.

#### Rule POL-TXN-004: "Window Dressing" & Irregular Large Cash Inflows
* **Definition:** Unexplained, non-payroll lump-sum deposits occurring within 30 to 45 days prior to the credit application submission date.
* **Risk Context:** Applicants frequently borrow money from friends or informal lenders to temporarily inflate account balances before applying for a loan ("window dressing").
* **Policy Rule:**
  * Any single non-payroll credit inflow exceeding **$50\%$ of declared monthly income** must have a documented audit trail (e.g., bonus slip, tax refund, asset sale).
  * If the funds are immediately followed by rapid outflows, it indicates pass-through manipulation.
* **Compliance Status:**
  * **Satisfied:** Inflows strictly match regular payroll and customary income patterns.
  * **Flag for Review:** Unexplained lump-sum deposit $> 50\%$ of monthly income without verified source.

#### Rule POL-TXN-005: Account Balance Burn Rate & Payday Depletion
* **Definition:** The trajectory of the applicant's account balance between regular payroll deposit cycles.
* **Evaluation Metric:**
  * **Healthy:** Average end-of-day balance remains positive; minimum balance prior to next salary credit remains $\ge 15\%$ of net salary.
  * **Vulnerable (Living Paycheck to Paycheck):** Balance consistently drops below $\$50.00$ within 7 days before next salary deposit.
  * **Critical Distress:** Balance drops below zero repeatedly prior to payday, requiring emergency credit reliance.
