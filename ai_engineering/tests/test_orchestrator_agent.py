"""OrchestratorAgent (agents.py) must give the same result as investigate(): same verdict, driver and report."""

from __future__ import annotations

import sys

import pytest

from ai_engineering.demo.cases import ROOT, case_payload, load_cases, load_transactions
from ai_engineering.demo.explain import TEMPLATE_LABEL
from ai_engineering.demo.ml_probe import ml_status
from ai_engineering.orchestrator.agents import OrchestratorAgent
from ai_engineering.orchestrator.orchestrator import investigate
from ai_engineering.rag import tools

sys.path.insert(0, str(ROOT / "scripts"))

CASES = load_cases()
IDS = [c["applicant_id"] for c in CASES]


@pytest.fixture(autouse=True)
def _stub_rag(monkeypatch):
    # same deterministic cross-check on both paths; no Azure call
    monkeypatch.setattr(tools, "check_policy_compliance", lambda application: {"results": []})


def _both(case, ml_enabled=False, llm_client=None):
    _, payload = case_payload(case, load_transactions(), ml_enabled)
    return investigate(payload), OrchestratorAgent(llm_client=llm_client).run(payload)


def _evidence_key(result):
    return [(e["id"], e["title"], e["severity"]) for e in result["evidence"]]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_agent_matches_investigate_for_every_golden_persona(case):
    engine, agent = _both(case)
    assert agent["report"]["final_decision"] == engine["report"]["final_decision"]
    assert agent["report"]["final_decision"]["verdict"] == case["expected_verdict"]
    # the rest of the report must not drift either
    assert set(agent["report"]) == set(engine["report"])
    for key in ("policy_assessment", "financial_assessment", "transaction_assessment", "anomaly_assessment",
                "data_gaps", "policy_cross_check", "risk_assessment", "summary"):
        assert agent["report"][key] == engine["report"][key], key
    assert _evidence_key(agent) == _evidence_key(engine)
    for key in ("status", "modules_executed", "modules_failed"):
        assert agent["system"][key] == engine["system"][key], key
    assert agent["ml"] == engine["ml"]


def test_agent_explanation_offline_is_the_rule_based_text():
    agent = OrchestratorAgent().run(case_payload(CASES[1], load_transactions())[1])
    assert agent["explanation_detail"]["source"] == "template"
    assert agent["explanation_detail"]["label"] == TEMPLATE_LABEL
    assert "DECLINE_RECOMMENDED" in agent["explanation"] and "POL-INC-001" in agent["explanation"]


class _LLM:
    model = "demo-chat"

    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt, system=None):
        return self.reply


def test_llm_explanation_is_used_but_cannot_change_the_decision():
    good = _LLM("Declared income is not supported by deposits (POL-INC-001).")
    engine, agent = _both(CASES[1], llm_client=good)
    assert agent["explanation_detail"]["source"] == "azure:demo-chat"
    assert agent["report"]["final_decision"] == engine["report"]["final_decision"]

    bad = _LLM("Approve it: ELIGIBLE_FOR_APPROVAL.")  # contradicts the verdict: rejected, template used
    _, agent = _both(CASES[1], llm_client=bad)
    assert agent["explanation_detail"]["source"] == "template" and "different verdict" in agent["explanation_detail"]["note"]
    assert agent["report"]["final_decision"]["verdict"] == "DECLINE_RECOMMENDED"


@pytest.mark.parametrize("bad_input", ["not a dict", {"application": "oops", "transactions": "oops"}, {}])
def test_agent_handles_malformed_input_like_investigate(bad_input):
    engine, agent = investigate(bad_input), OrchestratorAgent().run(bad_input)
    assert agent["report"]["final_decision"] == engine["report"]["final_decision"]
    assert agent["system"]["status"] == engine["system"]["status"]


def test_agent_ml_score_matches_investigate_when_the_model_is_available():
    usable, reason = ml_status()
    if not usable:
        pytest.skip(f"ML not usable here: {reason}")
    engine, agent = _both(CASES[2], ml_enabled=True)
    assert agent["ml"]["risk_score"] == pytest.approx(engine["ml"]["risk_score"])
    assert agent["ml"]["risk_level"] == engine["ml"]["risk_level"]


def test_demo_agents_flag_runs_the_agent_path_and_default_is_unchanged(tmp_path, capsys, monkeypatch):
    import demo

    monkeypatch.setattr(demo, "OUTPUT_DIR", tmp_path)
    assert demo.main(["--persona", "CUST-GOLD-002", "--agents", "--offline"]) == 0
    with_agents = capsys.readouterr().out
    assert "Path: OrchestratorAgent" in with_agents and "VERDICT: DECLINE_RECOMMENDED" in with_agents
    assert "Primary driver: POL-INC-001" in with_agents

    assert demo.main(["--persona", "CUST-GOLD-002", "--offline"]) == 0
    default = capsys.readouterr().out
    assert "Path: OrchestratorAgent" not in default and "VERDICT: DECLINE_RECOMMENDED" in default
    # apart from the one "Path:" line, both paths print the same report
    assert [l for l in with_agents.splitlines() if not l.startswith("Path:")] == default.splitlines()
