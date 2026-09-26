# Retail Banking Credit Underwriting Policy
## Document Code: POL-RET-2026-04: Underwriting Decision Framework & Referral Matrix
**Classification:** Internal Risk & Underwriting Standard  
**Target Product:** Unsecured Personal Loans  
**Effective Date:** January 1, 2026  
**Audience:** Credit Underwriters, Risk Analysts, AI Credit-Risk Investigation System

---

### 1. Purpose & Scope
This document synthesizes the eligibility, affordability, and transaction investigation rules into an unambiguous decision matrix. It instructs the AI Credit-Risk Agent on how to classify the final investigation outcome into one of three standard recommendations:
1. **Eligible for Approval (Standard / Low Risk)**
2. **Case Requiring Further Review (Referral / Elevated Risk)**
3. **Breach / Recommended for Decline (Policy Knockout)**

> **Crucial Operating Principle:** As specified in Section 1 and Section 7 of the Product Requirements Document (PRD), the system provides **decision support** and synthesizes evidence for the human credit analyst; it does not autonomously execute approvals or declines.

---

### 2. Decision Matrix & Classification Rules

```
                               INVESTIGATION OUTCOME MATRIX
      ┌────────────────────────────────────────────────────────────────────────┐
      │                                                                        │
      │   1. Standard Approval:                                                │
      │      • Credit Score >= 660 (Tier 1 or Tier 2)                          │
      │      • Total DTI <= 35.0%                                              │
      │      • Clean Transactions (0 NSF, Gambling < 3%, No Undisclosed Debt)  │
      │      • Income Variance <= 10.0%                                        │
      │                                                                        │
      │   2. Case Requiring Further Review (REFERRAL):                         │
      │      • DTI between 35.1% and 43.0% (or shadow DTI breach)              │
      │      • Credit Score 600 - 659 (Tier 3)                                 │
      │      • Income discrepancy between 10.1% and 25.0%                      │
      │      • 2 to 3 NSF events OR Gambling between 3% and 10%                │
      │      • Undisclosed micro-loans / BNPL payments detected                │
      │      • Recent job change (< 6 months) or probation status              │
      │                                                                        │
      │   3. Recommended for Decline (KNOCKOUT):                               │
      │      • Credit Score < 600 (Tier 4)                                     │
      │      • Total DTI > 50.0%                                               │
      │      • >= 4 NSF events in 90 days or chronic unauthorized overdraft    │
      │      • Income discrepancy > 25.0% (unsupported declared income)       │
      │      • Active bankruptcy, unpaid court judgments, or tax liens         │
      │      • Gambling expenditure > 10.0% of net monthly income              │
      │                                                                        │
      └────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Investigation Report Requirements

When the AI Agent compiles the structured Investigation Report for the credit analyst (per PRD Section 5.6), the report must format findings across the following mandatory sections:

1. **Executive Summary & Investigation Verdict**:
   * Applicant ID, Full Name, Loan Requested ($), Proposed Term.
   * Clear flag: `APPROVED`, `FURTHER_REVIEW_REQUIRED`, or `DECLINE_RECOMMENDED`.
   * Key primary driver for the recommendation.

2. **Policy Compliance Findings**:
   * Checklist of rules evaluated (`POL-ELG-001` through `POL-TXN-005`).
   * Explicit classification for each rule: `SATISFIED`, `FLAGGED`, `NOT_SATISFIED`, or `MISSING_DATA`.

3. **Financial & Affordability Analysis**:
   * Declared Monthly Net Income vs. Verified Bank Inflow.
   * Total DTI, Recalculated Shadow DTI (including hidden debt).
   * Net Disposable Income (NDI) and living buffer margin.

4. **Transaction Investigation & Behavioral Findings**:
   * Total 90-day debits vs. credits.
   * NSF / Overdraft count and dates.
   * Gambling analysis (total spend and % of net income).
   * Undisclosed debt service items found in bank statement with merchant names and payment cadence.

5. **Evidence Synthesis & Analyst Action Checklist**:
   * Concrete evidence citations (e.g., `"Deposit on 2026-02-14 from Employer ABC: $3,200.00"`).
   * Specific checklist of questions for the analyst to follow up with the applicant prior to final lending sign-off.
