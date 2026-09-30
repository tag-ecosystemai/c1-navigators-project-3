"""Offline tests for the policy RAG pipeline, run against the real Navigators policy files
in data/policies/. No Azure keys needed.

Run from the repo root:  python -m pytest ai_engineering/tests -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ai_engineering.rag.config import REPO_ROOT, RAGSettings
from ai_engineering.rag.embeddings import HashingEmbedder
from ai_engineering.rag.loaders import detect_heading_level
from ai_engineering.rag.policy_checker import PolicyChecker, compare
from ai_engineering.rag.retriever import PolicyRetriever
from ai_engineering.rag.stores import LocalVectorStore

POLICY_DIR = REPO_ROOT / "data" / "policies"


@pytest.fixture()
def retriever(tmp_path: Path) -> PolicyRetriever:
    settings = RAGSettings(policy_dir=POLICY_DIR, index_dir=tmp_path / "index", embeddings_backend="local")
    r = PolicyRetriever(settings, embedder=HashingEmbedder(), store=LocalVectorStore(settings.index_dir))
    r.ingest()
    return r


class FakeLLM:
    """Stands in for Azure OpenAI: returns rules for the clauses it can see in the prompt.

    Field names and values match data/test_cases/sample_application.json, which follows the
    applications.csv schema in DATA_DICTIONARY.md. Thresholds are the real ones from
    data/policies/01-04*.md.
    """

    name = "fake"

    # (rule_id, requirement, clause, field, operator, threshold, unit, severity, quote)
    RULES = [
        ("pol_elg_003", "Employed at least 6 months", "POL-ELG-003", "employment_length_months", ">=", 6, "months", "requirement", "Minimum **6 months** continuous service"),
        # POL-DTI-001 has four bands; expressed as three boundary rules by severity
        ("pol_dti_001_decline", "DTI at most 50%", "POL-DTI-001", "calculated_dti_pct", "<=", 50, "percent", "requirement", "Critical Breach (> 50.0%)"),
        ("pol_dti_001_referral", "DTI at most 43%", "POL-DTI-001", "calculated_dti_pct", "<=", 43, "percent", "referral", "Mandatory Referral to Senior Underwriter"),
        ("pol_dti_001_condition", "DTI at most 35%", "POL-DTI-001", "calculated_dti_pct", "<=", 35, "percent", "risk_indicator", "Low Risk (<= 35.0%)"),
        ("pol_lti_001", "Loan within LTI cap for credit tier", "POL-LTI-001", "calculated_lti_ratio", "<=", 3.5, "ratio", "requirement", "Maximum LTI of **3.5x**"),
        ("pol_scr_002", "No bankruptcies on file", "POL-SCR-002", "bankruptcies_count", "==", 0, None, "requirement", "Open bankruptcy proceedings"),
        ("pol_prd_001", "Loan purpose is not restricted", "POL-PRD-001", "loan_purpose", "not_in", ["GAMBLING", "CRYPTO_PURCHASE", "DAY_TRADING"], None, "requirement", "Restricted Loan Purposes"),
        ("pol_ndi_001", "Net disposable income meets living buffer", "POL-NDI-001", "housing_status", "qualitative", None, None, "requirement", "Minimum required NDI buffer"),
        ("pol_inc_001", "Declared income matches verified inflows", "POL-INC-001", "notes", "qualitative", None, None, "requirement", "Variance % ="),
        ("valid_id", "Identity document verified", "POL-ELG-001", None, "qualitative", None, None, "requirement", "Valid government-issued photo ID"),
        ("bad_cite", "Invented rule", "POL-XXX-999", "credit_score", ">=", 900, None, "requirement", "not in policy"),
    ]

    def complete_json(self, system: str, user: str) -> dict:
        clause_to_chunk = {}
        # the rule code usually lives in the heading, which is part of "source:", not the body
        for m in re.finditer(r"=== EXCERPT chunk_id: ([0-9a-f]+)\n(.*?)\n=== END", user, re.S):
            for clause in re.findall(r"\bPOL-[A-Z]{2,4}-\d{2,4}\b", m.group(2)):
                clause_to_chunk.setdefault(clause, m.group(1))
        rules = []
        for rid, req, clause, fld, op, thr, unit, sev, quote in self.RULES:
            rules.append(
                {
                    "rule_id": rid, "requirement": req, "clause": clause,
                    "chunk_id": clause_to_chunk.get(clause, "not-a-real-chunk"),
                    "quote": quote, "field": fld, "operator": op, "threshold": thr, "unit": unit, "severity": sev,
                }
            )
        return {"rules": rules}


# ------------------------------------------------------------------ loading & chunking

def test_heading_detection():
    assert detect_heading_level("3 Affordability") == 1
    assert detect_heading_level("3.2 DTI referral band") == 2
    assert detect_heading_level("Article 5 Creditworthiness assessment") == 1
    assert detect_heading_level("3.1 Debt-to-income ratio. DTI must not exceed 40%.") is None


def test_document_title_promotes_specific_heading(retriever: PolicyRetriever):
    """All 4 files share a generic H1; the distinctive 'Document Code: POL-...' line should win."""
    titles = {c.title for c in retriever.store.chunks}
    assert "Retail Banking Credit Underwriting Policy" not in titles
    assert any(t.startswith("Document Code: POL-RET-2026-02") for t in titles)


def test_chunks_carry_rule_code_citations(retriever: PolicyRetriever):
    chunks = retriever.store.chunks
    assert chunks, "no chunks indexed"
    dti_chunk = next(c for c in chunks if "POL-DTI-001" in c.clauses)
    assert "Affordability" in dti_chunk.title
    assert "POL-DTI-001" in dti_chunk.citation


# ------------------------------------------------------------------ retrieval

@pytest.mark.parametrize(
    "query,clause",
    [
        ("minimum age to apply for a loan", "POL-ELG-001"),
        ("what credit score tiers exist", "POL-SCR-001"),
        ("gambling spend red flag threshold", "POL-TXN-001"),
        ("undisclosed BNPL debt shadow DTI", "POL-TXN-003"),
        ("net disposable income living buffer", "POL-NDI-001"),
    ],
)
def test_retrieval_finds_clause(retriever: PolicyRetriever, query: str, clause: str):
    top = retriever.search(query, k=3)
    assert any(clause in r.chunk.clauses for r in top), [r.chunk.citation for r in top]


def test_index_reloads_from_disk(retriever: PolicyRetriever):
    fresh = PolicyRetriever(
        retriever.settings, embedder=HashingEmbedder(), store=LocalVectorStore(retriever.settings.index_dir)
    )
    assert any(c.startswith("POL-SCR") for c in fresh.search("credit score tiers", k=1)[0].chunk.clauses)


def test_embedder_mismatch_is_caught(retriever: PolicyRetriever):
    other = PolicyRetriever(
        retriever.settings, embedder=HashingEmbedder(n_features=512), store=LocalVectorStore(retriever.settings.index_dir)
    )
    with pytest.raises(RuntimeError, match="Re-run ingest"):
        other.search("anything")


# ------------------------------------------------------------------ comparison logic

def test_compare_handles_units_and_types():
    assert compare(38, "<=", 40, "percent") is True
    assert compare(43, "<=", 40, "percent") is False
    assert compare(0.38, "<=", 40, "percent") is True  # fraction vs percent threshold, rescaled
    assert compare(650, "between", [600, 659]) is True
    assert compare("yes", "==", True) is True
    assert compare("GAMBLING", "not_in", ["GAMBLING", "CRYPTO_PURCHASE"]) is False
    assert compare("abc", ">=", 5) is None  # cannot compare -> unclear


# ------------------------------------------------------------------ policy checker

def test_policy_check_statuses(retriever: PolicyRetriever):
    import json

    app = json.loads((REPO_ROOT / "data/test_cases/sample_application.json").read_text())
    result = PolicyChecker(retriever, FakeLLM()).check(app, use_cache=False)
    by_id = {r.rule_id: r for r in result.results}

    assert "bad_cite" not in by_id  # rule citing a chunk that was not retrieved is dropped

    assert by_id["pol_elg_003"].status == "not_satisfied"  # 4 months < 6
    assert by_id["pol_dti_001_decline"].status == "satisfied"  # 43.0 <= 50
    assert by_id["pol_dti_001_referral"].status == "satisfied"  # 43.0 <= 43
    assert by_id["pol_dti_001_condition"].status == "not_satisfied"  # 43.0 > 35 -> conditional band
    assert by_id["pol_lti_001"].status == "satisfied"  # 0.35 <= 3.5
    assert by_id["pol_scr_002"].status == "satisfied"  # 0 bankruptcies
    assert by_id["pol_prd_001"].status == "satisfied"  # DEBT_CONSOLIDATION not restricted
    assert by_id["pol_ndi_001"].status == "unclear"  # qualitative, value present ("RENT")
    assert by_id["pol_inc_001"].status == "missing"  # field exists ("notes") but value is null
    assert by_id["valid_id"].status == "missing"  # no matching field at all
    assert by_id["pol_dti_001_decline"].quote_verified is True

    assert result.requires_review is True
    assert result.results[0].status == "not_satisfied"  # worst findings first


def test_rules_are_cached(retriever: PolicyRetriever):
    class CountingLLM(FakeLLM):
        calls = 0

        def complete_json(self, system, user):
            CountingLLM.calls += 1
            return super().complete_json(system, user)

    checker = PolicyChecker(retriever, CountingLLM())
    app = {"calculated_dti_pct": 30, "credit_score": 700}
    checker.check(app)
    checker.check(app)
    assert CountingLLM.calls == 1
