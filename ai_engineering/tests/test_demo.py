"""Demo runner, explanation writer, session/preflight and analyst agent (fake Azure, no network)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from ai_engineering.demo import agent as agent_mod
from ai_engineering.demo.cases import ROOT, find_case, load_cases, load_transactions, run_case
from ai_engineering.demo.explain import TEMPLATE_LABEL, explain, template_explanation
from ai_engineering.demo.render import console_report, html_report
from ai_engineering.demo.session import PreflightFailed, start_session
from ai_engineering.demo.view import build_view
from ai_engineering.rag import mode, tools
from ai_engineering.rag.azure_errors import AzureCallError

from .conftest import AzureStatusError, chat_response, tool_call

sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(autouse=True)
def _restore_cwd_and_caches():
    import os

    cwd = os.getcwd()
    yield
    os.chdir(cwd)
    mode.reset_caches()


@pytest.fixture
def cases():
    return load_cases(), load_transactions()


def _view(cases, key="CUST-GOLD-002", azure=False, banner="OFFLINE MODE - no Azure"):
    all_cases, txns = cases
    case = find_case(all_cases, key)
    application, result = run_case(case, txns)
    return build_view(case, application, result, banner, azure)


# ------------------------------------------------------------------ cases / answer key


def test_answer_key_never_reaches_the_engine(cases):
    all_cases, txns = cases
    application, result = run_case(all_cases[0], txns)
    assert not {"expected_verdict", "persona_type", "notes"} & set(application)


def test_find_case_by_id_or_persona():
    c = load_cases()
    assert find_case(c, "cust-gold-003")["applicant_id"] == "CUST-GOLD-003"
    assert find_case(c, "GOLDEN_PRIME_APPROVAL")["applicant_id"] == "CUST-GOLD-001"
    with pytest.raises(KeyError):
        find_case(c, "nobody")


# ------------------------------------------------------------------ explanation


def test_template_is_labelled_and_deterministic(cases):
    view = _view(cases)
    out = explain(view, llm=None)
    assert out["label"] == TEMPLATE_LABEL == "Generated from rules, not by an LLM"
    assert "DECLINE_RECOMMENDED" in out["text"] and "POL-INC-001" in out["text"]
    assert out["text"] == template_explanation(view)


class _LLM:
    model = "demo-chat"

    def __init__(self, reply=None, exc=None):
        self.reply, self.exc, self.seen = reply, exc, None

    def generate(self, prompt, system=None):
        self.seen = (prompt, system)
        if self.exc:
            raise self.exc
        return self.reply


def test_llm_explanation_is_used_when_valid(cases):
    view = _view(cases)
    llm = _LLM("The declared income is not supported by deposits (POL-INC-001), so the engine recommends decline.")
    out = explain(view, llm)
    assert out["source"] == "azure:demo-chat" and "POL-INC-001" in out["text"]
    prompt, system = llm.seen
    facts = json.loads(prompt)
    assert facts["verdict"] == "DECLINE_RECOMMENDED"
    assert "expected" not in prompt.lower() and view["name"] not in prompt  # no answer key, no name
    assert "never state, suggest or hint at a different decision" in system


@pytest.mark.parametrize("reply,reason", [
    ("Approve it: ELIGIBLE_FOR_APPROVAL per POL-INC-001.", "different verdict"),
    ("See POL-XYZ-999 for details.", "not in the report"),
    ("", "empty"),
])
def test_bad_llm_text_falls_back_to_template(cases, reply, reason):
    out = explain(_view(cases), _LLM(reply))
    assert out["source"] == "template" and out["label"] == TEMPLATE_LABEL and reason in out["note"]


def test_llm_error_falls_back_to_template(cases):
    out = explain(_view(cases), _LLM(exc=AzureCallError("rate limit")))
    assert out["source"] == "template" and "rate limit" in out["note"]


# ------------------------------------------------------------------ rendering


def test_html_is_self_contained_and_states_the_mode(cases):
    view = _view(cases)
    page = html_report(view, explain(view), {"POL-INC-001": {"citation": "Doc > 5", "text": "Variance <script>x</script>"}})
    assert "OFFLINE MODE - no Azure" in page and "CUST-GOLD-002" in page and "DECLINE_RECOMMENDED" in page
    assert not re.search(r"(src|href)=['\"]https?://", page) and "<script" not in page.replace("&lt;script", "")
    assert "Generated from rules, not by an LLM" in page


def test_azure_report_shows_citations_and_conflicts(cases):
    view = _view(cases, azure=True, banner="Azure OpenAI: chat=c, embeddings=e")
    view["cross_check"] = {"available": True, "error": None, "conflicts": ["POL-INC-001"], "needs_review": True, "rules": {
        "POL-INC-001": {"evaluator": "HIGH_RISK", "rag_outcome": "review", "agreement": "soft_conflict",
                        "citation": "Policy 02 > Rule POL-INC-001", "quote": "Variance between 10.1% and 25.0%"}}}
    text = console_report(view, explain(view))
    assert "Azure OpenAI: chat=c, embeddings=e" in text and "soft_conflict" in text
    assert "Policy 02 > Rule POL-INC-001" in text and "Conflicts: POL-INC-001" in text
    assert "Policy 02 &gt; Rule" in html_report(view, explain(view)) or "Policy 02 &gt; Rule POL-INC-001" in html_report(view, explain(view))


def test_azure_report_shows_rag_unavailable(cases):
    view = _view(cases, azure=True, banner="Azure OpenAI: chat=c, embeddings=e")
    view["cross_check"] = {"available": False, "error": "RuntimeError: boom", "conflicts": [], "rules": {}}
    assert "RAG checker unavailable: RuntimeError: boom" in console_report(view, explain(view))


# ------------------------------------------------------------------ session / preflight


def test_session_fails_loudly_when_azure_is_broken(fake_openai, azure_env):
    fake_openai.error = {"chat": AzureStatusError("x", status_code=401)}
    with pytest.raises(PreflightFailed) as info:
        start_session(require_azure=True)
    text = str(info.value)
    assert "preflight FAILED" in text and "[FAIL] chat deployment" in text and "rejected the API key" in text
    assert "fake-key-123" not in text


def test_session_runs_on_azure_when_healthy(fake_openai, azure_env):
    session = start_session()
    assert session.azure_mode and session.banner == "Azure OpenAI: chat=demo-chat, embeddings=demo-embed"
    assert session.llm.model == "demo-chat"


def test_session_rebuilds_a_stale_index(fake_openai, azure_env, monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDINGS", "local")
    tools.get_retriever()  # builds an index with the local embedder
    mode.reset_caches()
    monkeypatch.setenv("RAG_EMBEDDINGS", "azure")
    session = start_session()
    assert any("Rebuilt the policy index" in n for n in session.notices)
    assert json.loads((Path(mode.get_settings().index_dir) / "manifest.json").read_text())["embedder"] == "azure:demo-embed"


def test_session_offline_flag_forces_safety_net(fake_openai, azure_env):
    session = start_session(offline=True)
    assert not session.azure_mode and session.banner == "OFFLINE MODE - no Azure" and session.llm is None
    with pytest.raises(ValueError):
        start_session(offline=True, require_azure=True)


def test_session_without_azure_vars_runs_offline_with_notice(monkeypatch, tmp_path):
    for var in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "index"))
    session = start_session()
    assert not session.azure_mode and session.notices


def test_ml_unavailable_reason_is_reported_without_crashing(cases, monkeypatch):
    from ai_engineering.demo import session as session_mod

    monkeypatch.setattr(session_mod, "ml_status", lambda: (False, "ModuleNotFoundError: No module named 'xgboost'"))
    s = session_mod.start_session(offline=True)
    assert s.ml_enabled is False and "xgboost" in s.ml_reason
    all_cases, txns = cases
    case = all_cases[0]
    application, result = run_case(case, txns, ml_enabled=s.ml_enabled)
    view = build_view(case, application, result, s.banner, False, s.ml_reason)
    assert view["ml"]["text"] == "ML scoring unavailable: ModuleNotFoundError: No module named 'xgboost'"
    assert result["system"]["status"] == "ok"


# ------------------------------------------------------------------ demo script end to end (offline)


def test_demo_all_offline_writes_html_and_matches_expected(tmp_path, capsys, monkeypatch):
    import demo

    monkeypatch.setattr(demo, "OUTPUT_DIR", tmp_path)
    assert demo.main(["--all", "--offline"]) == 0
    out = capsys.readouterr().out
    assert "Engine verdict matches expected: 5/5" in out and out.count("OFFLINE MODE - no Azure") >= 6
    assert sorted(p.name for p in tmp_path.glob("*.html")) == [f"CUST-GOLD-00{i}.html" for i in range(1, 6)]


def test_demo_require_azure_exits_2_with_preflight(fake_openai, azure_env, capsys):
    import demo

    fake_openai.error = {"embeddings": AzureStatusError("x", status_code=404, code="DeploymentNotFound")}
    assert demo.main(["--persona", "CUST-GOLD-001"]) == 2
    err = capsys.readouterr().err
    assert "preflight FAILED" in err and "no embedding deployment named 'demo-embed'" in err


def test_demo_on_azure_uses_rag_and_azure_explanation(fake_openai, azure_env, tmp_path, capsys, monkeypatch):
    import demo

    monkeypatch.setattr(demo, "OUTPUT_DIR", tmp_path)
    rule_json = {"rules": []}
    # chat is used for: doctor JSON ping, RAG rule extraction (JSON), and the explanation (prose)
    fake_openai.chat_reply = json.dumps(rule_json)
    assert demo.main(["--persona", "CUST-GOLD-002"]) == 0
    out = capsys.readouterr().out
    assert "Azure OpenAI: chat=demo-chat, embeddings=demo-embed" in out
    assert "Policy RAG checker (Azure OpenAI) vs rule evaluator" in out
    assert "OFFLINE MODE" not in out
    assert "Azure explanation rejected" in out or "Written by Azure OpenAI" in out  # prose reply was not valid for the explainer
    page = (tmp_path / "CUST-GOLD-002.html").read_text(encoding="utf-8")
    assert "Azure OpenAI: chat=demo-chat, embeddings=demo-embed" in page


# ------------------------------------------------------------------ analyst agent


def test_agent_calls_tools_then_answers(fake_openai, azure_env, monkeypatch):
    from .conftest import FakeAzureOpenAI

    # keep the RAG checker (inside investigate) from consuming the scripted chat replies
    monkeypatch.setattr(tools, "check_policy_compliance", lambda application: {"results": []})
    client = FakeAzureOpenAI()
    fake_openai.chat_script = [
        chat_response(tool_calls=[tool_call("get_case_report", json.dumps({"applicant_id": "CUST-GOLD-002"}))]),
        chat_response("CUST-GOLD-002 is DECLINE_RECOMMENDED because of POL-INC-001."),
    ]
    messages = agent_mod.new_conversation()
    answer = agent_mod.run_turn(client, "demo-chat", messages, "Why was GOLD-002 declined?")
    assert "POL-INC-001" in answer
    tool_msg = next(m for m in messages if m["role"] == "tool")
    payload = json.loads(tool_msg["content"])
    assert payload["verdict"] == "DECLINE_RECOMMENDED" and "expected_verdict" not in payload["application"]
    first_call = fake_openai.calls[0][1]
    assert {t["function"]["name"] for t in first_call["tools"]} == {"search_policies", "check_policy_compliance", "get_case_report"}
    assert "never make or change the decision" in messages[0]["content"]


def test_agent_caps_tool_loops_at_five(fake_openai, azure_env):
    from .conftest import FakeAzureOpenAI

    client = FakeAzureOpenAI()
    looping = [chat_response(tool_calls=[tool_call("search_policies", json.dumps({"query": "dti"}), f"c{i}")]) for i in range(10)]
    fake_openai.chat_script = looping[:5] + [chat_response("Final answer after the cap.")]
    seen = []

    def fake_dispatch(name, arguments):
        seen.append(name)
        return {"results": []}

    answer = agent_mod.run_turn(client, "demo-chat", agent_mod.new_conversation(), "q", dispatch_fn=fake_dispatch)
    assert answer == "Final answer after the cap." and len(seen) == 5
    assert "tools" not in fake_openai.calls[-1][1]  # the sixth request offers no tools


def test_agent_tool_errors_are_returned_to_the_model():
    assert "error" in agent_mod.dispatch("nope", {})
    assert "No golden persona" in agent_mod.dispatch("get_case_report", {"applicant_id": "x"})["error"]


def test_ask_agent_requires_azure(capsys, monkeypatch, tmp_path):
    import ask_agent

    for var in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert ask_agent.main(["-q", "hello"]) == 2
    assert "requires Azure OpenAI" in capsys.readouterr().err
