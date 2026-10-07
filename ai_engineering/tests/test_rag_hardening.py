"""Offline tests for auto-ingest, the doctor command, Azure error messages and the orchestrator wiring."""

from __future__ import annotations

import logging

import pytest

from ai_engineering.rag import tools
from ai_engineering.rag.azure_errors import AzureCallError, call_azure, explain_azure_error
from ai_engineering.rag.cli import main


class _Err(Exception):
    def __init__(self, message="", status_code=None, code=None):
        super().__init__(message)
        self.status_code, self.code = status_code, code


def test_deployment_not_found_message():
    msg = explain_azure_error(_Err(status_code=404, code="DeploymentNotFound"), "my-chat", "chat")
    assert "my-chat" in msg and "AZURE_OPENAI_CHAT_DEPLOYMENT" in msg


def test_401_and_429_messages():
    assert "AZURE_OPENAI_API_KEY" in explain_azure_error(_Err(status_code=401), "d", "embedding")
    assert "rate limit" in explain_azure_error(_Err(status_code=429), "d", "chat").lower()


def test_call_azure_wraps_and_hides_raw_error():
    def boom():
        raise _Err("secret-looking raw text", status_code=401)

    with pytest.raises(AzureCallError) as info:
        call_azure(boom, "d", "chat")
    assert "secret-looking" not in str(info.value)


def _local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_EMBEDDINGS", "local")
    monkeypatch.setenv("RAG_LLM", "local")
    monkeypatch.setenv("RAG_STORE", "local")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "index"))
    tools.get_retriever.cache_clear()


def test_get_retriever_builds_missing_index(monkeypatch, tmp_path, caplog):
    _local_env(monkeypatch, tmp_path)
    with caplog.at_level(logging.WARNING):
        retriever = tools.get_retriever()
    assert (tmp_path / "index" / "manifest.json").exists()
    assert "built automatically" in caplog.text
    assert retriever.index_exists()
    tools.get_retriever.cache_clear()


def test_get_retriever_does_not_rebuild_existing_index(monkeypatch, tmp_path, caplog):
    _local_env(monkeypatch, tmp_path)
    tools.get_retriever()
    tools.get_retriever.cache_clear()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        tools.get_retriever()
    assert "built automatically" not in caplog.text
    tools.get_retriever.cache_clear()


def test_doctor_reports_failures_without_keys(monkeypatch, tmp_path, capsys):
    _local_env(monkeypatch, tmp_path)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as info:
        main(["doctor"])
    out = capsys.readouterr().out
    assert info.value.code == 1
    assert "[FAIL] env AZURE_OPENAI_API_KEY: unset" in out
    assert "[WARN] policy index" in out and "built automatically" in out
    assert "[FAIL] RAG_EMBEDDINGS: local" in out and "fix:" in out


def test_doctor_never_prints_secret_values(monkeypatch, tmp_path, capsys):
    _local_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://secret-host.example/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-super-secret")
    tools.get_retriever()  # builds the local index so the index check passes
    tools.get_retriever.cache_clear()
    main(["doctor", "--allow-offline"])  # all applicable checks pass: exits normally
    out = capsys.readouterr().out
    assert "[PASS] env AZURE_OPENAI_API_KEY: set" in out
    assert "sk-super-secret" not in out and "secret-host" not in out


_APP = {"application": {"declared_monthly_net_income": 5000, "credit_score": 700, "age": 40,
                        "employment_length_months": 24, "declared_annual_income": 60000,
                        "requested_loan_amount": 10000, "loan_term_months": 36, "interest_rate_pct": 8,
                        "declared_existing_monthly_debt": 300}, "transactions": []}


def test_investigate_unaffected_by_rag_failure(monkeypatch):
    from ai_engineering.orchestrator.orchestrator import investigate

    def broken(app):
        raise RuntimeError("Azure down")

    monkeypatch.setattr(tools, "check_policy_compliance", lambda app: {"results": []})
    baseline = investigate(_APP)
    monkeypatch.setattr(tools, "check_policy_compliance", broken)
    result = investigate(_APP)

    assert result["report"]["policy_cross_check"]["available"] is False
    assert result["report"]["final_decision"] == baseline["report"]["final_decision"]
    assert result["system"]["status"] == baseline["system"]["status"]
    assert result["system"]["modules_failed"] == baseline["system"]["modules_failed"]
    assert result["system"]["errors"] == baseline["system"]["errors"]
