"""Azure code paths against a fake `openai` package (no network, no key)."""

from __future__ import annotations

import json

import pytest

from ai_engineering.orchestrator.llm_client import LLMClient
from ai_engineering.rag import mode
from ai_engineering.rag.azure_errors import AzureCallError
from ai_engineering.rag.cli import main
from ai_engineering.rag.config import get_settings
from ai_engineering.rag.doctor import ok, run_checks
from ai_engineering.rag.embeddings import AzureOpenAIEmbedder
from ai_engineering.rag.llm import AzureChatLLM

from .conftest import AzureStatusError, chat_response


def _by_name(checks):
    return {c.name: c for c in checks}


# ------------------------------------------------------------------ one config for every client


def test_every_client_uses_the_same_env_config(fake_openai, azure_env):
    AzureOpenAIEmbedder(get_settings())
    AzureChatLLM(get_settings())
    LLMClient()
    assert len(fake_openai.instances) == 3
    for client in fake_openai.instances:
        assert client.kwargs["azure_endpoint"] == "https://fake-resource.openai.azure.com/"
        assert client.kwargs["api_key"] == "fake-key-123"
        assert client.kwargs["api_version"] == "2024-10-21"
        assert client.kwargs["max_retries"] == 2 and client.kwargs["timeout"] > 0


def test_llm_client_generate_uses_chat_deployment(fake_openai, azure_env):
    fake_openai.chat_reply = "hello"
    assert LLMClient().generate("hi", system="be brief") == "hello"
    kind, kwargs = fake_openai.calls[-1]
    assert kwargs["model"] == "demo-chat"
    assert [m["role"] for m in kwargs["messages"]] == ["system", "user"]


def test_llm_client_turns_azure_errors_into_plain_english(fake_openai, azure_env):
    fake_openai.error = {"chat": AzureStatusError("raw", status_code=404, code="DeploymentNotFound")}
    with pytest.raises(AzureCallError) as info:
        LLMClient().generate("hi")
    assert "demo-chat" in str(info.value) and "AZURE_OPENAI_CHAT_DEPLOYMENT" in str(info.value)


def test_non_json_chat_reply_is_reported(fake_openai, azure_env):
    fake_openai.chat_reply = "not json"
    with pytest.raises(AzureCallError) as info:
        AzureChatLLM(get_settings()).complete_json("s", "u")
    assert "JSON" in str(info.value)


# ------------------------------------------------------------------ doctor


def _build_index(fake_openai):
    from ai_engineering.rag import tools

    tools.get_retriever()  # auto-ingests with the (fake) Azure embedder
    mode.reset_caches()


def test_doctor_all_green_on_azure(fake_openai, azure_env, capsys):
    _build_index(fake_openai)
    checks = run_checks(get_settings())
    names = _by_name(checks)
    assert ok(checks), [c.line() for c in checks if c.status == "FAIL"]
    assert "demo-embed" in names["embeddings deployment"].detail
    assert names["policy index"].detail == "built with azure:demo-embed"
    assert "chat=demo-chat, embeddings=demo-embed" in names["deployments in use"].detail
    main(["doctor"])
    out = capsys.readouterr().out
    assert "Mode: Azure OpenAI: chat=demo-chat, embeddings=demo-embed" in out
    assert "fake-key-123" not in out and "fake-resource" not in out


@pytest.mark.parametrize("which,status,code,needle", [
    ("embeddings", 404, "DeploymentNotFound", "no embedding deployment named 'demo-embed'"),
    ("embeddings", 401, None, "rejected the API key"),
    ("chat", 429, None, "rate limit"),
    ("chat", 404, "DeploymentNotFound", "no chat deployment named 'demo-chat'"),
])
def test_doctor_fails_with_plain_english_and_fix(fake_openai, azure_env, which, status, code, needle):
    fake_openai.error = {which: AzureStatusError("raw sdk text", status_code=status, code=code)}
    checks = run_checks(get_settings())
    failed = [c for c in checks if c.status == "FAIL"]
    assert len(failed) == 1 and needle in failed[0].detail and failed[0].fix
    assert "raw sdk text" not in failed[0].line()


def test_doctor_flags_index_built_with_other_embedder(fake_openai, azure_env, monkeypatch):
    _build_index(fake_openai)
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "other-embed")
    check = _by_name(run_checks(get_settings()))["policy index"]
    assert check.status == "FAIL" and "azure:demo-embed" in check.detail and "ingest" in check.fix


def test_doctor_rejects_placeholder_and_path_endpoints(fake_openai, azure_env, monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://<your-resource>.openai.azure.com/")
    assert _by_name(run_checks(get_settings()))["endpoint format"].status == "FAIL"
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/openai/deployments/foo")
    assert _by_name(run_checks(get_settings()))["endpoint format"].status == "FAIL"


def test_doctor_fails_when_left_in_offline_mode(fake_openai, azure_env, monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDINGS", "local")
    names = _by_name(run_checks(get_settings()))
    assert names["RAG_EMBEDDINGS"].status == "FAIL"
    assert names["RAG_EMBEDDINGS"].detail.startswith("local")
    assert all(c.status != "FAIL" for c in run_checks(get_settings(), allow_offline=True) if c.name == "RAG_EMBEDDINGS")


# ------------------------------------------------------------------ modes


def test_banner_names_the_mode(azure_env, monkeypatch):
    assert mode.banner() == "Azure OpenAI: chat=demo-chat, embeddings=demo-embed"
    monkeypatch.delenv("AZURE_OPENAI_API_KEY")
    assert mode.banner() == "OFFLINE MODE - no Azure"


def test_force_offline_uses_a_separate_index(azure_env, monkeypatch):
    mode.force_offline()
    s = get_settings()
    assert (s.embeddings_backend, s.rag_llm) == ("local", "local")
    assert s.index_dir.name == "offline"
    mode.force_offline()  # idempotent
    assert get_settings().index_dir.name == "offline" and get_settings().index_dir.parent.name == "index"
    assert mode.banner() == "OFFLINE MODE - no Azure"


def test_cross_check_is_skipped_offline(azure_env):
    from ai_engineering.rag.cross_check import run_cross_check

    mode.force_offline()
    out = run_cross_check({}, {"POL-LTI-001": "SATISFIED"})
    assert out["available"] is False and "offline" in out["error"].lower()


def test_doctor_index_manifest_is_json(fake_openai, azure_env):
    _build_index(fake_openai)
    manifest = json.loads((get_settings().index_dir / "manifest.json").read_text())
    assert manifest["embedder"] == "azure:demo-embed"
