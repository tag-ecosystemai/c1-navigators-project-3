"""Tests for the evaluator-vs-RAG cross-check. Pure Python: no Azure key, no index needed."""

from __future__ import annotations

from ai_engineering.rag.cross_check import compare, rag_outcome, run_cross_check


def _res(clause, status, severity="requirement", **extra):
    base = {
        "rule_id": clause.lower().replace("-", "_"),
        "clause": clause,
        "status": status,
        "severity": severity,
        "citation": f"Policy §{clause}",
        "quote": "quoted text",
        "explanation": "why",
        "quote_verified": True,
    }
    base.update(extra)
    return base


def test_severity_mapping():
    assert rag_outcome("satisfied", "requirement") == "pass"
    assert rag_outcome("not_satisfied", "requirement") == "fail"
    assert rag_outcome("not_satisfied", "referral") == "review"
    assert rag_outcome("not_satisfied", "risk_indicator") == "review"
    assert rag_outcome("unclear", "requirement") == "review"
    assert rag_outcome("missing", "requirement") == "missing"


def test_agreement_carries_citation():
    out = compare({"POL-LTI-001": "SATISFIED"}, {"results": [_res("POL-LTI-001", "satisfied")]})
    rule = out["rules"]["POL-LTI-001"]
    assert rule["agreement"] == "agree"
    assert rule["citation"] == "Policy §POL-LTI-001"
    assert out["needs_review"] is False


def test_hard_conflict_pass_vs_fail():
    out = compare({"POL-SCR-002": "SATISFIED"}, {"results": [_res("POL-SCR-002", "not_satisfied")]})
    assert out["rules"]["POL-SCR-002"]["agreement"] == "hard_conflict"
    assert out["conflicts"] == ["POL-SCR-002"]
    assert out["needs_review"] is True


def test_soft_conflict_review_vs_fail():
    # employment of 4 months: evaluator says review, a single-threshold RAG rule says fail
    out = compare({"POL-ELG-003": "FLAG_FOR_REVIEW"}, {"results": [_res("POL-ELG-003", "not_satisfied")]})
    assert out["rules"]["POL-ELG-003"]["agreement"] == "soft_conflict"


def test_dti_bands_agree_when_tiers_line_up():
    # DTI 43%: evaluator -> CONDITIONAL (review). RAG has three band rules; the worst is the
    # 'risk_indicator' band (<=35) failing -> review, so they agree.
    rag = {
        "results": [
            _res("POL-DTI-001", "satisfied", "requirement"),
            _res("POL-DTI-001", "satisfied", "referral"),
            _res("POL-DTI-001", "not_satisfied", "risk_indicator"),
        ]
    }
    out = compare({"POL-DTI-001": "CONDITIONAL"}, rag)
    assert out["rules"]["POL-DTI-001"]["agreement"] == "agree"


def test_missing_on_rag_side_is_not_a_conflict():
    out = compare({"POL-NDI-001": "SATISFIED"}, {"results": [_res("POL-NDI-001", "missing")]})
    assert out["rules"]["POL-NDI-001"]["agreement"] == "evaluator_only"
    assert out["needs_review"] is False


def test_rule_absent_from_rag_and_informational_values():
    out = compare(
        {"POL-TXN-004": "SATISFIED", "POL-SCR-001": "Tier 1"},
        {"results": []},
    )
    assert out["rules"]["POL-TXN-004"]["agreement"] == "evaluator_only"
    assert out["rules"]["POL-SCR-001"]["agreement"] == "not_compared"


def test_rule_code_found_in_rule_id_or_citation():
    r = {"rule_id": "pol_inc_001", "clause": None, "status": "not_satisfied", "severity": "requirement",
         "citation": "Doc §POL-INC-001"}
    out = compare({"POL-INC-001": "HIGH_RISK"}, {"results": [r]})
    assert out["rules"]["POL-INC-001"]["agreement"] == "agree"


def test_run_cross_check_uses_injected_checker():
    seen = {}

    def fake(app):
        seen["app"] = app
        return {"results": [_res("POL-LTI-001", "satisfied")]}

    out = run_cross_check({"credit_score": 700}, {"POL-LTI-001": "SATISFIED"}, check_fn=fake)
    assert out["available"] is True
    assert seen["app"] == {"credit_score": 700}


def test_run_cross_check_survives_rag_failure():
    def broken(app):
        raise RuntimeError("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")

    out = run_cross_check({}, {"POL-LTI-001": "SATISFIED"}, check_fn=broken)
    assert out["available"] is False
    assert "AZURE_OPENAI" in out["error"]
    assert out["needs_review"] is False
