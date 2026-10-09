"""Policy checker: variant selection, polarity, and status validation (LLM reads, Python applies)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai_engineering.rag import policy_checker
from ai_engineering.rag.chunking import Chunk
from ai_engineering.rag.policy_checker import (
    PolicyChecker, PolicyRule, applies_to, repair_polarity, validate_result,
)
from ai_engineering.rag.stores import SearchResult

# The applicant from the real Azure run: salaried, 14 months, Tier 2 (690), single, nothing flagged.
APPLICANT = {
    "employment_status": "EMPLOYED_FULL_TIME", "employment_length_months": 14,
    "credit_score": 690, "credit_score_tier": "TIER_2_NEAR_PRIME", "dependents_count": 0,
    "gambling_pct_of_income": 0.0, "nsf_event_count": 0, "ndi_amount": 2921.92, "lti_ratio": 0.2778,
    "declared_monthly_net_income": 7500,
}


def _chunk():
    return Chunk(chunk_id="c1", text="policy text", source="p.md", title="Policy", category="internal",
                 section="s", clauses=["POL-X-001"])


def _checker(tmp_path, llm=None):
    retriever = SimpleNamespace(settings=SimpleNamespace(index_dir=tmp_path))
    return PolicyChecker(retriever, llm)


def _rule(**kw):
    base = {"rule_id": "r", "requirement": "x", "chunk_id": "c1", "clause": "POL-X-001", "quote": "policy text",
            "field": None, "operator": "<=", "threshold": 0, "unit": None, "severity": "requirement"}
    base.update(kw)
    return PolicyRule.model_validate(base)


def _run(tmp_path, rules, application=APPLICANT):
    return _checker(tmp_path).evaluate(rules, application, [SearchResult(_chunk(), 1.0)])


def _by_id(result):
    return {r.rule_id: r for r in result.results}


SALARIED = {"field": "employment_status", "operator": "in", "value": ["EMPLOYED_FULL_TIME", "PART_TIME"]}
SELF_EMPLOYED = {"field": "employment_status", "operator": "==", "value": "SELF_EMPLOYED"}


# ------------------------------------------------------------------ 1. variant selection


def test_salaried_applicant_is_judged_on_the_salaried_clause_not_the_self_employed_one(tmp_path):
    salaried = _rule(rule_id="salaried", field="employment_length_months", operator=">=", threshold=6, applies_when=[SALARIED])
    selfemp = _rule(rule_id="self_employed", field="employment_length_months", operator=">=", threshold=24, applies_when=[SELF_EMPLOYED])
    result = _run(tmp_path, [salaried, selfemp])
    assert [r.rule_id for r in result.results] == ["salaried"] and result.results[0].status == "satisfied"
    assert [n["rule_id"] for n in result.not_applicable] == ["self_employed"]
    assert "SELF_EMPLOYED" in result.not_applicable[0]["reason"] or "EMPLOYED_FULL_TIME" in result.not_applicable[0]["reason"]
    # control: without applies_when the self-employed clause wrongly fails a 14-month salaried applicant
    ungated = _run(tmp_path, [_rule(rule_id="self_employed", field="employment_length_months", operator=">=", threshold=24)])
    assert ungated.results[0].status == "not_satisfied"


def test_tier_2_applicant_gets_the_tier_2_lti_cap_only(tmp_path):
    tiers = [
        _rule(rule_id="t1", field="lti_ratio", operator="<=", threshold=4.5, applies_when=[{"field": "credit_score", "operator": ">=", "value": 720}]),
        _rule(rule_id="t2", field="lti_ratio", operator="<=", threshold=3.5, applies_when=[{"field": "credit_score", "operator": "between", "value": [660, 719]}]),
        _rule(rule_id="t3", field="lti_ratio", operator="<=", threshold=0.25, applies_when=[{"field": "credit_score", "operator": "between", "value": [600, 659]}]),
    ]
    result = _run(tmp_path, tiers)
    assert [(r.rule_id, r.status) for r in result.results] == [("t2", "satisfied")]
    assert sorted(n["rule_id"] for n in result.not_applicable) == ["t1", "t3"]


def test_single_applicant_gets_the_single_buffer_not_the_dependents_one(tmp_path):
    rules = [
        _rule(rule_id="single", field="ndi_amount", operator=">=", threshold=500, applies_when=[{"field": "dependents_count", "operator": "==", "value": 0}]),
        _rule(rule_id="dependents", field="ndi_amount", operator=">=", threshold=3500, applies_when=[{"field": "dependents_count", "operator": ">", "value": 0}]),
    ]
    result = _run(tmp_path, rules)
    assert [(r.rule_id, r.status) for r in result.results] == [("single", "satisfied")]
    assert [n["rule_id"] for n in result.not_applicable] == ["dependents"]


def test_with_dependents_the_other_variant_applies(tmp_path):
    rules = [
        _rule(rule_id="single", field="ndi_amount", operator=">=", threshold=500, applies_when=[{"field": "dependents_count", "operator": "==", "value": 0}]),
        _rule(rule_id="dependents", field="ndi_amount", operator=">=", threshold=3500, applies_when=[{"field": "dependents_count", "operator": ">", "value": 0}]),
    ]
    result = _run(tmp_path, rules, {**APPLICANT, "dependents_count": 2})
    assert [(r.rule_id, r.status) for r in result.results] == [("dependents", "not_satisfied")]


def test_unknown_variant_is_unclear_not_silently_dropped(tmp_path):
    rule = _rule(rule_id="salaried", field="employment_length_months", operator=">=", threshold=6, applies_when=[SALARIED])
    app = {k: v for k, v in APPLICANT.items() if k != "employment_status"}
    result = _run(tmp_path, [rule], app)
    assert result.results[0].status == "unclear" and "employment_status" in result.results[0].explanation
    assert applies_to(rule, app)[0] is None


def test_not_applicable_is_reported_in_to_dict(tmp_path):
    rule = _rule(rule_id="self_employed", field="employment_length_months", operator=">=", threshold=24, applies_when=[SELF_EMPLOYED])
    assert _run(tmp_path, [rule]).to_dict()["not_applicable"][0]["rule_id"] == "self_employed"


# ------------------------------------------------------------------ 2. polarity: LLM extracts, Python applies


@pytest.mark.parametrize("value,expected", [(0.0, "satisfied"), (10.0, "satisfied"), (10.1, "not_satisfied"), (35.0, "not_satisfied")])
def test_gambling_breach_threshold_is_not_a_requirement(tmp_path, value, expected):
    rule = _rule(rule_id="gambling", field="gambling_pct_of_income", operator=">", threshold=10, polarity="breach_if")
    result = _run(tmp_path, [rule], {**APPLICANT, "gambling_pct_of_income": value})
    assert result.results[0].status == expected


@pytest.mark.parametrize("value,expected", [(0, "satisfied"), (3, "satisfied"), (4, "not_satisfied"), (6, "not_satisfied")])
def test_nsf_breach_threshold(tmp_path, value, expected):
    rule = _rule(rule_id="nsf", field="nsf_event_count", operator=">=", threshold=4, polarity="breach_if")
    assert _run(tmp_path, [rule], {**APPLICANT, "nsf_event_count": value}).results[0].status == expected


def test_breach_level_mislabelled_as_must_meet_is_repaired(tmp_path):
    """The failure from the real run: '> 10' extracted as a requirement fails a 0% gambler."""
    wrong = _rule(rule_id="gambling", requirement="Gambling spend exceeds 10% of monthly income (high risk)",
                  field="gambling_pct_of_income", operator=">", threshold=10)  # polarity left as must_meet
    result = _run(tmp_path, [wrong])
    r = result.results[0]
    assert r.status == "satisfied" and r.polarity == "breach_if" and "breach level" in r.note
    knockout = _rule(rule_id="nsf", requirement="4 or more NSF events in 90 days is a knockout",
                     field="nsf_event_count", operator=">=", threshold=4)
    r = _run(tmp_path, [knockout]).results[0]
    assert r.status == "satisfied" and r.polarity == "breach_if"
    # and a real breach is still caught
    assert _run(tmp_path, [knockout], {**APPLICANT, "nsf_event_count": 5}).results[0].status == "not_satisfied"


@pytest.mark.parametrize("requirement,op,threshold,value,expected", [
    ("Minimum verifiable monthly net income of $2,000", ">=", 2000, 1500, "not_satisfied"),
    ("Applicant must be at least 21 years old", ">=", 21, 34, "satisfied"),
    ("Credit score of 660 or higher", ">=", 660, 690, "satisfied"),
])
def test_genuine_minimums_are_not_flipped(tmp_path, requirement, op, threshold, value, expected):
    rule = _rule(requirement=requirement, field="x", operator=op, threshold=threshold)
    assert repair_polarity(rule) == ("must_meet", None)
    assert _run(tmp_path, [rule], {"x": value}).results[0].status == expected


# risk bands: triggered by falling INSIDE them (the real run failed 0% gamblers and 0-NSF applicants on these)

@pytest.mark.parametrize("field,requirement,band,severity,value,expected", [
    ("gambling_pct_of_income", "Moderate / Monitor: gambling between 3.0% and 10.0% of monthly net income", [3, 10], "risk_indicator", 0.0, "satisfied"),
    ("gambling_pct_of_income", "Moderate / Monitor: gambling between 3.0% and 10.0% of monthly net income", [3, 10], "risk_indicator", 5.0, "not_satisfied"),
    ("nsf_event_count", "2 to 3 NSF / returned payment events in the last 90 days", [2, 3], "referral", 0, "satisfied"),
    ("nsf_event_count", "2 to 3 NSF / returned payment events in the last 90 days", [2, 3], "referral", 2, "not_satisfied"),
    ("dti_pct", "Moderate Risk (35.1% - 43.0%): conditional pass", [35.1, 43.0], "risk_indicator", 16.4, "satisfied"),
    ("dti_pct", "Moderate Risk (35.1% - 43.0%): conditional pass", [35.1, 43.0], "risk_indicator", 40.0, "not_satisfied"),
    ("dti_pct", "Moderate Risk (35.1% - 43.0%): conditional pass", [35.1, 43.0], "requirement", 16.4, "satisfied"),  # band wording alone
])
@pytest.mark.parametrize("polarity", [None, "must_meet", "breach_if"])
def test_risk_bands_are_triggered_by_falling_inside_them(tmp_path, field, requirement, band, severity, value, expected, polarity):
    rule = _rule(rule_id="band", requirement=requirement, field=field, operator="between", threshold=band,
                 severity=severity, polarity=polarity)
    assert _run(tmp_path, [rule], {**APPLICANT, field: value}).results[0].status == expected


@pytest.mark.parametrize("value,expected", [(34, "satisfied"), (21, "satisfied"), (20, "not_satisfied"), (70, "not_satisfied")])
def test_a_real_between_requirement_is_not_flipped(tmp_path, value, expected):
    rule = _rule(rule_id="age", requirement="Applicant age must be between 21 and 68", field="age", operator="between", threshold=[21, 68])
    assert repair_polarity(rule) == ("must_meet", None)
    assert _run(tmp_path, [rule], {"age": value}).results[0].status == expected


# the opposite mistake seen in the real run: "must not exceed" + "<=" labelled breach_if

@pytest.mark.parametrize("requirement,op,threshold,field,value,expected", [
    ("Undisclosed debt payments must not exceed $250 per month", "<=", 250, "u", 0, "satisfied"),
    ("Undisclosed debt payments must not exceed $250 per month", "<=", 250, "u", 300, "not_satisfied"),
    ("Single non-payroll deposit must not exceed 50% of income", "<=", 0.5, "w", 0.0, "satisfied"),
    ("Applicant income must be at least $2,000 per month", ">=", 2000, "i", 5000, "satisfied"),
    ("Applicant income must be at least $2,000 per month", ">=", 2000, "i", 1500, "not_satisfied"),
])
def test_a_breach_if_label_that_contradicts_must_not_exceed_wording_is_corrected(tmp_path, requirement, op, threshold, field, value, expected):
    rule = _rule(requirement=requirement, field=field, operator=op, threshold=threshold, polarity="breach_if")
    polarity, note = repair_polarity(rule)
    assert polarity == "must_meet" and "corrected" in note
    assert _run(tmp_path, [rule], {field: value}).results[0].status == expected


@pytest.mark.parametrize("requirement,op,threshold,value,expected", [
    ("Credit score below 600 is a decline", "<", 600, 690, "satisfied"),
    ("Credit score below 600 is a decline", "<", 600, 550, "not_satisfied"),
    ("Gambling above 10% of income is a violation", ">", 10, 0, "satisfied"),
    ("Gambling above 10% of income is a violation", ">", 10, 12, "not_satisfied"),
])
def test_genuine_breach_if_rules_are_kept(tmp_path, requirement, op, threshold, value, expected):
    rule = _rule(requirement=requirement, field="x", operator=op, threshold=threshold, polarity="breach_if")
    assert repair_polarity(rule) == ("breach_if", None)
    assert _run(tmp_path, [rule], {"x": value}).results[0].status == expected


# ------------------------------------------------------------------ 3. validation of statuses


def test_not_satisfied_is_invalid_when_the_value_does_not_breach_the_threshold():
    breach = _rule(field="g", operator=">", threshold=10, polarity="breach_if")
    status, note = validate_result(breach, 0, "not_satisfied")
    assert status == "satisfied" and "contradicted" in note
    meet = _rule(field="g", operator="<=", threshold=10)
    assert validate_result(meet, 5, "not_satisfied")[0] == "satisfied"


def test_satisfied_is_invalid_when_the_value_breaches_the_threshold():
    breach = _rule(field="g", operator=">", threshold=10, polarity="breach_if")
    assert validate_result(breach, 15, "satisfied")[0] == "not_satisfied"
    meet = _rule(field="g", operator="<=", threshold=10)
    assert validate_result(meet, 15, "satisfied")[0] == "not_satisfied"


def test_consistent_statuses_pass_untouched_and_other_statuses_are_left_alone():
    meet = _rule(field="g", operator="<=", threshold=10)
    assert validate_result(meet, 5, "satisfied") == ("satisfied", None)
    assert validate_result(meet, 15, "not_satisfied") == ("not_satisfied", None)
    assert validate_result(meet, 5, "missing") == ("missing", None)


def test_an_uncomparable_value_cannot_support_a_hard_status():
    meet = _rule(field="g", operator="<=", threshold=10)
    status, note = validate_result(meet, "abc", "not_satisfied")
    assert status == "unclear" and "cannot be compared" in note


def test_a_status_volunteered_by_the_llm_is_never_used(tmp_path):
    rule = _rule(rule_id="gambling", field="gambling_pct_of_income", operator="<=", threshold=10, status="not_satisfied")
    r = _run(tmp_path, [rule]).results[0]
    assert r.status == "satisfied" and "the LLM claimed 'not_satisfied'" in r.note


# ------------------------------------------------------------------ prompt, extraction, cache


class _CapturingLLM:
    name = "capture"

    def __init__(self, rules):
        self.rules, self.calls = rules, []

    def complete_json(self, system, user):
        self.calls.append((system, user))
        return {"rules": self.rules}


def test_prompt_teaches_polarity_and_variants_and_extraction_keeps_them(tmp_path):
    raw = [{"rule_id": "elg", "requirement": "Salaried tenure of at least 6 months", "chunk_id": "c1", "clause": "POL-ELG-003",
            "quote": "policy text", "field": "employment_length_months", "operator": ">=", "threshold": 6,
            "applies_when": [SALARIED], "polarity": "must_meet"},
           {"rule_id": "bad", "requirement": "x", "chunk_id": "c1", "operator": "<=", "threshold": 1,
            "applies_when": [{"operator": "==", "value": 1}]}]  # condition without a field: invalid, dropped
    llm = _CapturingLLM(raw)
    checker = _checker(tmp_path, llm)
    rules = checker.extract_rules([SearchResult(_chunk(), 1.0)], APPLICANT, use_cache=False)
    system, user = llm.calls[0]
    for needle in ("polarity", "breach_if", "RISK BAND", "ONE rule per condition", "set field to null", "applies_when", "SELF_EMPLOYED", "credit_score", "dependents_count", "Do NOT include any verdict"):
        assert needle in system, needle
    assert "FIELD VALUE NOTES" in user and "SELF_EMPLOYED" in user
    assert [r.rule_id for r in rules] == ["elg"] and rules[0].applies_when[0].field == "employment_status"


def test_cache_key_changes_with_the_prompt(tmp_path, monkeypatch):
    llm = _CapturingLLM([])
    checker = _checker(tmp_path, llm)
    clauses = [SearchResult(_chunk(), 1.0)]
    checker.extract_rules(clauses, APPLICANT)
    monkeypatch.setattr(policy_checker, "SYSTEM_PROMPT", policy_checker.SYSTEM_PROMPT + "\nextra")
    checker.extract_rules(clauses, APPLICANT)
    assert len(list(checker.cache_dir.glob("*.json"))) == 2 and len(llm.calls) == 2  # old cached rules not reused
