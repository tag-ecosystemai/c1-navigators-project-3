# Retail Banking Credit Underwriting Policy
## Document Code: POL-RET-2026-01: General Credit Eligibility Standards
**Classification:** Internal Risk & Underwriting Standard  
**Target Product:** Unsecured Personal Loans  
**Effective Date:** January 1, 2026  
**Audience:** Credit Underwriters, Risk Analysts, AI Credit-Risk Investigation System

---

### 1. Purpose & Scope
This policy defines the baseline eligibility criteria and underwriting standards for evaluating individual applicants for Unsecured Personal Loans. All credit applications submitted to the bank must be evaluated against these standards. 

When the AI Credit-Risk Investigation Agent audits an application, it must benchmark applicant attributes against the rules, thresholds, and conditions set forth herein.

---

### 2. Core Eligibility Rules

#### Rule POL-ELG-001: Age & Legal Capacity
* **Requirement:** The applicant must be at least 21 years of age and not exceed 68 years of age at the scheduled loan maturity date.
* **Verification:** Valid government-issued photo ID (Passport, National ID, or Driver's License).
* **Compliance Status:**
  * **Satisfied:** Applicant age is between 21 and 68 (inclusive).
  * **Not Satisfied:** Applicant is under 21 or exceeds 68 at maturity.
  * **Unclear / Missing:** Date of birth not provided or identity document unverified.

#### Rule POL-ELG-002: Minimum Income Threshold
* **Requirement:** Minimum verifiable monthly net income of **$2,000 USD** (or annual gross income of **$30,000 USD**).
* **Acceptable Income Sources:**
  * Full-time permanent employment.
  * Verifiable continuous self-employment / contracting (minimum 2 years proven history).
  * Fixed pension or statutory retirement annuity.
* **Excluded Income Sources:** Unemployment benefits, temporary stimulus/grants, one-time gifts, lottery/gambling winnings, and unverified cash earnings.
* **Compliance Status:**
  * **Satisfied:** Verified monthly net income >= $2,000.
  * **Not Satisfied:** Verified monthly net income < $2,000.
  * **Unclear / Missing:** Declared income without bank statement or pay slip corroboration.

#### Rule POL-ELG-003: Employment Stability & Tenure
* **Requirement:**
  * For salaried employees: Minimum **6 months** continuous service with current employer, or minimum **12 months** continuous employment history if current role is between 3 and 6 months.
  * For self-employed applicants: Minimum **24 months** registered business operations with verifiable tax returns.
  * Probationary periods: Applicants currently under probationary employment must be flagged for manual review.
* **Compliance Status:**
  * **Satisfied:** Employment tenure criteria met with full documentation.
  * **Flag for Review:** Applicant in probation period or job change within last 3 months.
  * **Not Satisfied:** Unemployed or unstable employment history (< 3 months without prior continuity).

---

### 3. Credit Bureau & Score Evaluation

#### Rule POL-SCR-001: Credit Bureau Score Tiers
The credit risk classification relies on primary bureau scores (e.g., FICO / VantageScore equivalent):

| Tier | Score Range | Underwriting Action | Max Loan Amount |
|---|---|---|---|
| **Tier 1 (Prime)** | 720 – 850 | Fast-track standard underwriting. Standard policy parameters apply. | Up to $50,000 |
| **Tier 2 (Near-Prime)** | 660 – 719 | Standard underwriting. Full transaction and cash-flow verification required. | Up to $35,000 |
| **Tier 3 (Subprime / Caution)** | 600 – 659 | **Mandatory Credit Investigation.** Enhanced scrutiny of bank statements, DTI, and payment history. | Up to $15,000 |
| **Tier 4 (High Risk / Knockout)** | < 600 | **Decline / Exception Only.** Policy breach; requires Senior Credit Committee sign-off. | $0 |

#### Rule POL-SCR-002: Bureau Delinquency & Adverse Public Records
* **Knockout Conditions (Automatic Decline):**
  * Open bankruptcy proceedings or discharged bankruptcy within the last 24 months.
  * Unsettled court judgments, tax liens, or active charge-offs in excess of $1,000.
* **Adverse History Flag:**
  * Any 30-day delinquency in the past 6 months requires explanation.
  * Any 60-day or 90-day delinquency in the past 12 months triggers mandatory human referral.

---

### 4. Loan Sizing & Terms

#### Rule POL-PRD-001: Permissible Loan Terms
* **Loan Amount Limits:** Minimum $2,000; Maximum $50,000 (subject to credit tier limits).
* **Loan Duration:** 12 months, 24 months, 36 months, 48 months, or 60 months.
* **Restricted Loan Purposes:**
  * Speculative investments, day-trading, cryptocurrency purchases.
  * Gambling, debt refinancing of unauthorized lenders, or illicit transactions.
  * Down payments for secondary secured borrowing without equity disclosure.
