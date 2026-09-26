# Retail Banking Credit Underwriting Policy
## Document Code: POL-RET-2026-02: Affordability & Debt Service Standards
**Classification:** Internal Risk & Underwriting Standard  
**Target Product:** Unsecured Personal Loans  
**Effective Date:** January 1, 2026  
**Audience:** Credit Underwriters, Risk Analysts, AI Credit-Risk Investigation System

---

### 1. Purpose & Scope
This document sets forth the quantitative affordability formulas, debt-to-income benchmarks, and disposable income rules required to assess a borrower's capacity to service debt without experiencing severe financial distress.

---

### 2. Debt-to-Income (DTI) Standards

#### Rule POL-DTI-001: Total Debt-to-Income (DTI) Ratio Benchmark
The Total Debt-to-Income ratio evaluates monthly gross or net debt commitments against gross or net monthly income.

$$\text{DTI} = \frac{\text{Total Monthly Debt Commitments (Existing Debt + Proposed New Loan Payment)}}{\text{Gross Monthly Income}} \times 100\%$$

* **Threshold Tiers:**
  * **Low Risk ($\le$ 35.0%):** Satisfied. Standard approval corridor.
  * **Moderate Risk (35.1% – 43.0%):** Conditional pass. Requires verification of stable employment and minimum 3 months of emergency savings buffer.
  * **High Risk / Policy Exception (43.1% – 50.0%):** **Mandatory Referral to Senior Underwriter.** Strict compensating factors required (e.g., Tier 1 credit score > 740, verified liquid assets > $15,000).
  * **Critical Breach (> 50.0%):** **Automatic Policy Decline.** Strictly prohibited under responsible lending criteria.

* **Compliance Status for Agent:**
  * **Satisfied:** DTI $\le$ 35.0%.
  * **Satisfied with Condition:** DTI between 35.1% and 43.0%.
  * **Flag for Review:** DTI between 43.1% and 50.0%.
  * **Not Satisfied (Decline):** DTI > 50.0%.

---

### 3. Loan-to-Income (LTI) & Debt Sizing Caps

#### Rule POL-LTI-001: Maximum Loan-to-Income (LTI) Multiplier
To prevent over-indebtedness, total unsecured borrowing from the bank is capped by gross annual income:

$$\text{LTI} = \frac{\text{Total Requested Loan Principal}}{\text{Gross Annual Income}}$$

* **Policy Multiplier Caps:**
  * **Tier 1 (Prime, Score 720+):** Maximum LTI of **4.5x** gross annual income (or max loan cap of $50,000).
  * **Tier 2 (Near-Prime, Score 660–719):** Maximum LTI of **3.5x** gross annual income (or max loan cap of $35,000).
  * **Tier 3 (Subprime, Score 600–659):** Maximum LTI of **2.0x** gross annual income (or max loan cap of $15,000).
* **Compliance Status:**
  * **Satisfied:** Requested loan is within the applicable LTI multiplier.
  * **Not Satisfied:** Requested loan exceeds the LTI ceiling for the applicant's credit tier.

---

### 4. Cash Flow & Net Disposable Income (NDI)

#### Rule POL-NDI-001: Net Disposable Income & Minimum Living Buffer
Applicants must retain sufficient uncommitted cash flow after deducting all housing costs, living expenses, existing debt service, and the proposed new loan repayment.

$$\text{Net Disposable Income (NDI)} = \text{Net Monthly Income} - (\text{Rent/Mortgage} + \text{Living Expenses} + \text{Existing Debt Repayments} + \text{Proposed Loan Installment})$$

* **Living Allowance Buffer Standards:**
  * **Single Applicant:** Minimum required NDI buffer of **$500.00 USD/month**.
  * **Applicant with Dependents:** Minimum required NDI buffer of **$800.00 USD/month** + $200 per additional dependent child.
* **Compliance Status:**
  * **Satisfied:** Projected NDI exceeds the minimum living allowance buffer.
  * **Flag for Review:** Projected NDI is between $0 and $499 (marginal liquidity).
  * **Not Satisfied:** Projected NDI is negative (< $0), indicating immediate default risk upon origination.

---

### 5. Income Verification & Discrepancy Tolerance

#### Rule POL-INC-001: Stated vs. Actual Inflow Variance Check
The AI agent must compare the gross or net income declared on the credit application against the 90-day annualized or monthly average salary deposits identified in the bank statement transactions.

$$\text{Variance \%} = \frac{|\text{Declared Monthly Net Income} - \text{Verified Average Monthly Bank Inflows}|}{\text{Declared Monthly Net Income}} \times 100\%$$

* **Tolerance Standards:**
  * **Variance $\le$ 10.0%:** Acceptable. Minor variances due to tax withholding fluctuations, statutory deductions, or overtime are accepted.
  * **Variance between 10.1% and 25.0%:** **Review Required.** Analyst must request recent pay stubs or employer verification letter.
  * **Variance > 25.0%:** **High Risk / Suspected Misrepresentation.** Bank deposits fail to support declared earnings. Application must be escalated for forensic fraud and income re-assessment.
