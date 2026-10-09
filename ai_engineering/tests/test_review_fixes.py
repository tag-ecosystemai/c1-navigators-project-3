"""Three review fixes: 'compared' wording, POL-TXN-003 severity, ASCII-safe terminal output."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering.demo.cases import ROOT, find_case, load_cases, load_transactions, run_case
from ai_engineering.demo.explain import _check_llm_text, checker_status, explain, facts_for, template_explanation
from ai_engineering.demo.render import ascii_safe, console_report, html_report
from ai_engineering.demo.view import build_view
from ai_engineering.rag import policy_checker, tools
from ai_engineering.rag.chunking import Chunk
from ai_engineering.rag.cross_check import compare
from ai_engineering.rag.policy_checker import PolicyChecker, PolicyRule, repair_severity
from ai_engineering.rag.stores import SearchResult

POLICIES = ROOT / "data" / "policies"


@pytest.fixture(autouse=True)
def _no_rag(monkeypatch):
    monkeypatch.setattr(tools, "check_policy_compliance", lambda application: {"results": []})


# ============================================================ 1. "agreed on all rules it compared"


def _rules(n_agree=3, n_evaluator_only=2, n_not_compared=1, conflicts=()):
    rules = {f"POL-A-{i:03d}": {"agreement": "agree"} for i in range(n_agree)}
    rules.update({f"POL-E-{i:03d}": {"agreement": "evaluator_only"} for i in range(n_evaluator_only)})
    rules.update({f"POL-N-{i:03d}": {"agreement": "not_compared"} for i in range(n_not_compared)})
    for code in conflicts:
        rules[code] = {"agreement": "soft_conflict"}
    return {"available": True, "error": None, "conflicts": list(conflicts), "rules": rules}


def _view(cross, persona="CUST-GOLD-002"):
    case = find_case(load_cases(), persona)
    application, result = run_case(case, load_transactions())
    view = build_view(case, application, result, "banner", True)
    view["cross_check"] = cross
    return view


def test_only_really_compared_rules_are_counted():
    check = checker_status(_view(_rules()))
    assert check["compared"] == 3 and check["total_rules"] == 6  # evaluator_only / not_compared are not compared
    assert checker_status(_view(_rules(conflicts=["POL-INC-001"])))["compared"] == 4
    assert facts_for(_view(_rules()))["policy_checker"]["compared"] == 3


@pytest.mark.parametrize("sentence", [
    "The policy checker agreed with the rule engine on all rules.",
    "The policy checker agreed with the rule engine on every rule.",
    "The checker and the rule engine agreed on all policy rules.",
    "The policy checker agreed with the rule engine on each rule.",
    "The policy checker agreed with the rule engine on all other rules.",
])
def test_claiming_agreement_on_all_rules_is_rejected(sentence):
    reason = _check_llm_text(f"Based on POL-INC-001. {sentence}", _view(_rules()))
    assert reason and "overstates" in reason and "compared" in reason
    out = explain(_view(_rules()), SimpleNamespace(model="m", generate=lambda prompt, system=None: f"Based on POL-INC-001. {sentence}"))
    assert out["source"] == "template" and "overstates" in out["note"]


@pytest.mark.parametrize("sentence", [
    "The policy checker agreed with the rule engine on all rules it compared.",
    "The policy checker agreed with the rule engine on every rule it compared.",
    "The policy checker agreed with the rule engine on all 3 rules it compared.",
    "The policy checker agreed with the rule engine on 3 of 6 rules.",
])
def test_compared_wording_is_accepted(sentence):
    assert _check_llm_text(f"Based on POL-INC-001. {sentence}", _view(_rules())) is None


def test_disagreement_sentences_must_not_overstate_either():
    view = _view(_rules(conflicts=["POL-INC-001"]))
    ok = "The policy checker disagreed with the rule engine on POL-INC-001 and agreed on the other rules it compared."
    assert _check_llm_text(ok, view) is None
    bad = "The policy checker disagreed with the rule engine on POL-INC-001 and agreed on all other rules."
    assert "overstates" in _check_llm_text(bad, view)


def test_prompt_and_template_use_the_compared_wording():
    from ai_engineering.demo.explain import SYSTEM_PROMPT

    assert "on all rules it compared" in SYSTEM_PROMPT and "never say it agreed on 'all rules'" in SYSTEM_PROMPT
    view = _view(_rules())
    text = template_explanation(view)
    assert "agreed with the rule engine on all 3 rules it compared (3 others could not be compared)" in text
    assert _check_llm_text(text, view) is None
    disagreed = template_explanation(_view(_rules(conflicts=["POL-INC-001"])))
    assert "It compared 4 of 7 rules." in disagreed


def test_not_run_is_unaffected():
    view = _view({"available": False, "error": "offline mode", "conflicts": [], "rules": {}})
    assert _check_llm_text("Based on POL-INC-001. The policy checker was not run (offline mode).", view) is None


# ============================================================ 2. POL-TXN-003: undisclosed debt $740 > $250


def _section(file: str, code: str) -> str:
    text = (POLICIES / file).read_text(encoding="utf-8")
    start = text.index(f"#### Rule {code}")
    end = text.find("#### Rule", start + 10)
    return text[start:end if end != -1 else None]


TXN_003 = _section("03_bank_statement_and_transaction_investigation_policy.md", "POL-TXN-003")
TXN_001 = _section("03_bank_statement_and_transaction_investigation_policy.md", "POL-TXN-001")
DTI_001 = _section("02_affordability_and_debt_service_policy.md", "POL-DTI-001")


def _rule(**kw):
    base = {"rule_id": "r", "requirement": "x", "chunk_id": "c1", "clause": "POL-TXN-003", "quote": "", "field": None,
            "operator": "<=", "threshold": 0, "unit": None, "severity": "requirement"}
    base.update(kw)
    return PolicyRule.model_validate(base)


def _evaluate(tmp_path, rule, application, text):
    chunk = Chunk(chunk_id="c1", text=text, source="p.md", title="Policy", category="internal", section="s", clauses=[rule.clause])
    checker = PolicyChecker(SimpleNamespace(settings=SimpleNamespace(index_dir=tmp_path)), None)
    return checker.evaluate([rule], application, [SearchResult(chunk, 1.0)])


def test_the_policy_text_really_calls_over_250_not_satisfied():
    assert "Flag for Review" in TXN_003 and "Not Satisfied" in TXN_003 and "$250" in TXN_003


def test_a_250_limit_tagged_referral_is_raised_to_requirement_so_740_fails(tmp_path):
    """The live CUST-GOLD-004 case: the limit was tagged 'referral' (it sits beside 'Flag for Review'), so the
    cross-check turned not_satisfied into 'review'. The policy calls > $250 'Not Satisfied'."""
    rule = _rule(rule_id="debt", requirement="Undisclosed debt payments must not exceed $250 per month",
                 field="undisclosed_debt_total", threshold=250, unit="currency", severity="referral")
    r = _evaluate(tmp_path, rule, {"undisclosed_debt_total": 740.0}, TXN_003).results[0]
    assert (r.status, r.severity) == ("not_satisfied", "requirement") and "raised from referral" in r.note
    # the cross-check now sees a failure, which agrees with the evaluator's NOT_SATISFIED
    assert compare({"POL-TXN-003": "NOT_SATISFIED"}, {"results": [r.__dict__]})["rules"]["POL-TXN-003"]["agreement"] == "agree"
    # without the repair it was 'review' (soft conflict)
    unrepaired = {**r.__dict__, "severity": "referral"}
    assert compare({"POL-TXN-003": "NOT_SATISFIED"}, {"results": [unrepaired]})["rules"]["POL-TXN-003"]["agreement"] == "soft_conflict"


def test_within_the_limit_still_passes(tmp_path):
    rule = _rule(requirement="Undisclosed debt must not exceed $250 per month", field="undisclosed_debt_total",
                 threshold=250, severity="referral")
    assert _evaluate(tmp_path, rule, {"undisclosed_debt_total": 100.0}, TXN_003).results[0].status == "satisfied"


def test_the_revised_dti_limit_is_also_a_requirement(tmp_path):
    rule = _rule(requirement="Revised DTI must remain at or below 43%", field="shadow_dti_pct", threshold=43.0,
                 unit="percent", severity="referral")
    over = _evaluate(tmp_path, rule, {"shadow_dti_pct": 48.2}, TXN_003).results[0]
    assert (over.status, over.severity) == ("not_satisfied", "requirement")
    assert _evaluate(tmp_path, rule, {"shadow_dti_pct": 36.9}, TXN_003).results[0].status == "satisfied"


def test_gambling_over_10_percent_is_a_requirement_too(tmp_path):
    rule = _rule(clause="POL-TXN-001", requirement="Gambling must not exceed 10% of income", field="g", threshold=10,
                 severity="risk_indicator")
    r = _evaluate(tmp_path, rule, {"g": 12.0}, TXN_001).results[0]
    assert (r.status, r.severity) == ("not_satisfied", "requirement")


def test_genuine_referral_thresholds_are_left_alone(tmp_path):
    # DTI 43% is the REFERRAL boundary in the DTI text (not-satisfied is 50%): severity must stay referral
    rule = _rule(clause="POL-DTI-001", requirement="DTI at most 43%", field="d", threshold=43, unit="percent", severity="referral")
    assert repair_severity(rule, DTI_001) == ("referral", None)
    assert _evaluate(tmp_path, rule, {"d": 47.0}, DTI_001).results[0].severity == "referral"
    # the 50% boundary is the decline line: a referral-tagged 50 would be raised
    decline = _rule(clause="POL-DTI-001", requirement="DTI at most 50%", field="d", threshold=50, unit="percent", severity="referral")
    assert repair_severity(decline, DTI_001)[0] == "requirement"
    # a number that only appears as part of another number does not match (43 vs 43.1 / 143)
    assert repair_severity(_rule(threshold=14, field="x", severity="referral"), "Not Satisfied: value exceeds 143 or 14.5") == ("referral", None)


def test_severity_repair_needs_a_decline_wording_and_a_numeric_threshold():
    text = "Flag for Review: totals under $250 a month."
    assert repair_severity(_rule(field="x", threshold=250, severity="referral"), text) == ("referral", None)
    assert repair_severity(_rule(field="x", operator="between", threshold=[1, 2], severity="referral"), "Not Satisfied > 1") == ("referral", None)
    assert repair_severity(_rule(field=None, threshold=250, severity="referral"), "Not Satisfied: exceeds $250") == ("referral", None)
    assert repair_severity(_rule(field="x", threshold="abc", severity="referral"), "Not Satisfied: exceeds abc") == ("referral", None)
    assert repair_severity(_rule(field="x", threshold=250, severity="requirement"), "Not Satisfied: exceeds $250") == ("requirement", None)


def test_the_prompt_tells_the_llm_how_severity_follows_the_wording():
    prompt = policy_checker.SYSTEM_PROMPT
    for needle in ("severity follows the policy's own wording", "Not Satisfied", "Flag for Review", "any undisclosed debt"):
        assert needle in prompt, needle


# ============================================================ 3. ASCII-safe terminal output, intact HTML


def test_source_has_no_mojibake_and_citations_use_a_real_section_sign(tmp_path):
    src = Path(policy_checker.__file__).read_text(encoding="utf-8")
    assert "Â" not in src and "â€" not in src
    rule = _rule(requirement="x", field="a", threshold=1)
    r = _evaluate(tmp_path, rule, {"a": 0}, "text").results[0]
    assert r.citation == "Policy §POL-TXN-003"


def test_ascii_safe_transliterates():
    assert ascii_safe("Policy §POL-DTI-001") == "Policy Sec. POL-DTI-001"
    assert ascii_safe("35.1% – 43.0% ≤ 35 “x” …") == '35.1% - 43.0% <= 35 "x" ...'
    assert ascii_safe("café").isascii()


def test_console_report_is_pure_ascii_but_html_keeps_the_section_sign():
    case = find_case(load_cases(), "CUST-GOLD-002")
    application, result = run_case(case, load_transactions())
    view = build_view(case, application, result, "Azure OpenAI: chat=c, embeddings=e", True)
    view["cross_check"] = {"available": True, "error": None, "conflicts": ["POL-INC-001"], "needs_review": True, "rules": {
        "POL-INC-001": {"evaluator": "HIGH_RISK", "rag_outcome": "review", "agreement": "soft_conflict",
                        "citation": "Policy §POL-INC-001", "quote": "Variance 10.1% – 25.0%"}}}
    explanation = explain(view)
    console = console_report(view, explanation)
    assert console.isascii() and "Policy Sec. POL-INC-001" in console and "Â" not in console
    page = html_report(view, explanation)
    assert "Policy §POL-INC-001" in page and "10.1% – 25.0%" in page  # HTML unchanged


def test_whole_offline_demo_output_is_ascii(tmp_path, capsys, monkeypatch):
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import demo

    monkeypatch.setattr(demo, "OUTPUT_DIR", tmp_path)
    assert demo.main(["--persona", "CUST-GOLD-002", "--offline"]) == 0
    out = capsys.readouterr().out
    assert out.isascii() and "VERDICT: DECLINE_RECOMMENDED" in out
    assert (tmp_path / "CUST-GOLD-002.html").exists()  # the HTML report is still written (UTF-8, not ASCII-folded)
