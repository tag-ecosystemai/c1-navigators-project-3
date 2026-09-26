# Lending Policies Knowledge Base (RAG & Underwriting Rules)

## Overview
This directory contains the formal credit underwriting guidelines and regulatory standards for the **Banking: AI Credit-Risk Investigation Agent** (TAG Bootcamp Project 3).

These documents serve as the **ground-truth knowledge base** for:
1. **AI Layer (Gabriel & Hannah):** Ingested, chunked, and embedded into the Vector Database (e.g. ChromaDB, FAISS, or Azure AI Search) to empower the RAG-enabled Policy Check tool.
2. **Backend (Ruffy):** Reference rules for validation schemas and automated financial threshold calculations.
3. **Frontend (Danny):** Reference for building the Policy Checklist UI widget (Satisfied, Flagged, Not Satisfied).

---

## Document Index & Rule Codes

| Document | File | Key Rule Identifiers | Focus Area |
|---|---|---|---|
| **01. General Eligibility** | [`01_general_credit_eligibility_policy.md`](01_general_credit_eligibility_policy.md) | `POL-ELG-001` to `003`, `POL-SCR-001` to `002`, `POL-PRD-001` | Age, minimum income ($2k/mo), employment tenure, credit score tiers (Tier 1 to 4), bankruptcies. |
| **02. Affordability & DTI** | [`02_affordability_and_debt_service_policy.md`](02_affordability_and_debt_service_policy.md) | `POL-DTI-001`, `POL-LTI-001`, `POL-NDI-001`, `POL-INC-001` | DTI caps (35%, 43%, 50%), LTI caps, Net Disposable Income buffers ($500 single, $800 family), income variance tolerance (10%). |
| **03. Transaction & Red Flags** | [`03_bank_statement_and_transaction_investigation_policy.md`](03_bank_statement_and_transaction_investigation_policy.md) | `POL-TXN-001` to `005` | Gambling limits (<3% safe, >10% breach), NSF/overdraft count, undisclosed debts (BNPL/loans), window dressing inflows, burn rate. |
| **04. Decision & Report Matrix** | [`04_underwriting_referral_and_exception_matrix.md`](04_underwriting_referral_and_exception_matrix.md) | Outcome Classification Matrix | Standard Approval vs. Review Required vs. Decline Knockouts, and mandatory report sections. |

---

## Instructions for AI Engineering (RAG Ingestion)

When chunking these documents for the vector store:
* **Recommended Chunking Strategy:** Markdown section-based or recursive character chunking with chunk size $\approx$ 500–800 tokens and 100 token overlap.
* **Metadata Extraction:** Store metadata with each chunk:
  ```json
  {
    "document": "03_bank_statement_and_transaction_investigation_policy.md",
    "policy_code": "POL-TXN-001",
    "topic": "gambling_risk",
    "section": "Transaction Red Flags"
  }
  ```
* This allows the AI agent to cite exact policy codes (e.g., `POL-TXN-001` or `POL-DTI-001`) in the final investigation report.
