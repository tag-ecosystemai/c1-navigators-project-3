"""Azure explanation: what each number means, no 'alignment' for an income gap, honest policy-checker status."""

from __future__ import annotations

import json

import pytest

from ai_engineering.demo.cases import find_case, load_cases, load_transactions, run_case
from ai_engineering.demo.explain import (
    SYSTEM_PROMPT, TEMPLATE_LABEL, VALUE_MEANING, _check_llm_text, checker_status, explain, facts_for,
    template_explanation,
)
from ai_engineering.demo.view import build_view
from ai_engineering.rag import tools

NOT_RUN = {"available": False, "error": "RuntimeError: offline mode (RAG_LLM=local): the Azure RAG checker was not run",
           "conflicts": [], "rules": {}}
RAN_AGREED = {"available": True, "error": None, "conflicts": [], "rules": {}}
RAN_DISAGREED = {"available": True, "error": None, "conflicts": ["POL-INC-001", "POL-ELG-003"], "rules": {}}


@pytest.fixture(autouse=True)
def _no_rag(monkeypatch):
    monkeypatch.setattr(tools, "check_policy_compliance", lambda application: {"results": []})


def _view(persona="CUST-GOLD-002", cross=NOT_RUN):
    cases = load_cases()
    case = find_case(cases, persona)
    application, result = run_case(case, load_transactions())
    view = build_view(case, application, result, "banner", True)
    view["cross_check"] = cross
    return view


class _LLM:
    model = "demo-chat"

    def __init__(self, reply):
        self.reply, self.seen = reply, None

    def generate(self, prompt, system=None):
        self.seen = (prompt, system)
        return self.reply


GOOD_NOT_RUN = ("The rules recommend a decline because the declared income is not supported by the bank deposits: "
                "there is a 57.3% gap (POL-INC-001). The policy checker was not run (offline mode).")


# ------------------------------------------------------------------ B1: what the numbers mean


def test_every_rule_in_the_facts_carries_its_meaning_and_the_prompt_says_gap():
    view = _view()
    facts = facts_for(view)
    assert all(r["meaning"] for r in facts["rules"]) and {r["code"] for r in facts["rules"]} <= set(VALUE_MEANING)
    inc = next(r for r in facts["rules"] if r["code"] == "POL-INC-001")
    assert "GAP" in inc["meaning"] and "NOT supported" in inc["meaning"] and inc["applicant_value"] == "57.3%"
    assert "GAP" in SYSTEM_PROMPT and "alignment" in SYSTEM_PROMPT and "match" in SYSTEM_PROMPT


def test_the_prompt_actually_sent_contains_the_meanings():
    llm = _LLM(GOOD_NOT_RUN)
    explain(_view(), llm)
    sent = json.loads(llm.seen[0])
    assert any("GAP" in r["meaning"] for r in sent["rules"]) and "GAP" in llm.seen[1]


@pytest.mark.parametrize("sentence", [
    "The declared income and the bank deposits show alignment (POL-INC-001).",
    "Declared income matches the verified deposits (POL-INC-001).",
    "The 57.3% income variance is consistent with the declared figure (POL-INC-001).",
    "Income and deposits are in line with each other (POL-INC-001).",
    "Deposits are aligned with the declared income (POL-INC-001).",
])
def test_describing_the_income_gap_as_alignment_or_match_is_rejected(sentence):
    view = _view()
    reason = _check_llm_text(f"{sentence} The policy checker was not run (offline mode).", view)
    assert reason and "alignment/match" in reason
    out = explain(view, _LLM(f"{sentence} The policy checker was not run (offline mode)."))
    assert out["source"] == "template" and out["label"] == TEMPLATE_LABEL and "alignment/match" in out["note"]


@pytest.mark.parametrize("sentence", [
    "Declared income does not match the deposits (POL-INC-001).",
    "The deposits are not aligned with the declared income (POL-INC-001).",
    "There is no alignment between declared income and deposits (POL-INC-001).",
    "The declared income is not supported by deposits: a 57.3% gap (POL-INC-001).",
])
def test_negated_and_correct_wording_is_accepted(sentence):
    assert _check_llm_text(f"{sentence} The policy checker was not run (offline mode).", _view()) is None


def test_alignment_is_fine_when_the_income_really_does_match():
    view = _view("CUST-GOLD-001")  # variance 0%
    assert _check_llm_text("Declared income aligns with the deposits (POL-INC-001). The policy checker was not run (offline mode).", view) is None


# ------------------------------------------------------------------ B2: policy-checker status


def test_checker_status_is_passed_into_the_prompt():
    assert checker_status(_view(cross=NOT_RUN)) == {"status": "not_run", "reason": "offline mode"}
    assert checker_status(_view(cross=RAN_AGREED)) == {"status": "ran", "disagreed_on": [], "compared": 0, "total_rules": 0}
    assert checker_status(_view(cross=RAN_DISAGREED)) == {"status": "ran", "disagreed_on": ["POL-INC-001", "POL-ELG-003"],
                                                          "compared": 0, "total_rules": 0}
    unavailable = {"available": False, "error": "AzureCallError: rate limit", "conflicts": []}
    assert checker_status(_view(cross=unavailable))["reason"] == "it was unavailable"
    assert checker_status({"cross_check": None, "rules": []})["status"] == "not_run"
    llm = _LLM(GOOD_NOT_RUN)
    explain(_view(cross=RAN_DISAGREED), llm)
    assert json.loads(llm.seen[0])["policy_checker"]["disagreed_on"] == ["POL-INC-001", "POL-ELG-003"]


@pytest.mark.parametrize("text", [
    "The decision rests on POL-INC-001. There are no policy text conflicts.",
    "The decision rests on POL-INC-001. There are no conflicts.",
    "The decision rests on POL-INC-001. The policy checker agreed with the rule engine.",
    "The decision rests on POL-INC-001. The policy checker confirmed the result.",
    "The decision rests on POL-INC-001.",  # says nothing about the checker
])
def test_not_run_checker_must_be_reported_as_not_run(text):
    assert _check_llm_text(text, _view(cross=NOT_RUN))


def test_not_run_wording_is_accepted():
    assert _check_llm_text("Based on POL-INC-001. The policy checker was not run (offline mode).", _view(cross=NOT_RUN)) is None
    assert _check_llm_text("Based on POL-INC-001. The policy checker was unavailable.", _view(cross=NOT_RUN)) is None


def test_disagreements_are_described_as_the_checker_disagreeing_with_the_rule_engine():
    view = _view(cross=RAN_DISAGREED)
    good = "The policy checker disagreed with the rule engine on POL-INC-001, POL-ELG-003."
    assert _check_llm_text(good, view) is None
    for bad, why in [
        ("There are policy conflicts on POL-INC-001 and POL-ELG-003.", "policy conflicts"),
        ("The checker disagreed with the engine on POL-INC-001.", "POL-ELG-003"),  # a code is missing
        ("Based on POL-INC-001 and POL-ELG-003.", "disagreed"),  # does not mention the disagreement
        ("The policy checker found conflicting policy text on POL-INC-001 and POL-ELG-003.", "policy conflicts"),
    ]:
        reason = _check_llm_text(bad, view)
        assert reason and why in reason, (bad, reason)


def test_no_disagreement_claim_when_none_exists():
    view = _view(cross=RAN_AGREED)
    assert _check_llm_text("Based on POL-INC-001. The policy checker agreed with the rule engine on every rule it compared.", view) is None
    reason = _check_llm_text("Based on POL-INC-001. The policy checker disagreed with the rule engine.", view)
    assert reason and "did not" in reason
    assert _check_llm_text("Based on POL-INC-001. The policy checker did not disagree with the rule engine.", view) is None


@pytest.mark.parametrize("cross", [NOT_RUN, RAN_AGREED, RAN_DISAGREED], ids=["not_run", "agreed", "disagreed"])
def test_the_rule_based_template_tells_the_truth_and_passes_its_own_checks(cross):
    view = _view(cross=cross)
    text = template_explanation(view)
    assert _check_llm_text(text, view) is None
    if cross is NOT_RUN:
        assert "policy checker was not run (offline mode)" in text and "conflict" not in text.lower()
    elif cross is RAN_AGREED:
        assert "agreed with the rule engine" in text
    else:
        assert "disagreed with the rule engine on POL-INC-001, POL-ELG-003" in text


def test_a_valid_llm_text_is_used_and_cannot_change_the_decision():
    view = _view(cross=NOT_RUN)
    out = explain(view, _LLM(GOOD_NOT_RUN))
    assert out["source"] == "azure:demo-chat" and out["note"] is None
    assert view["verdict"] == "DECLINE_RECOMMENDED"
    bad = explain(view, _LLM(GOOD_NOT_RUN + " You should approve this: ELIGIBLE_FOR_APPROVAL."))
    assert bad["source"] == "template" and "different verdict" in bad["note"]
