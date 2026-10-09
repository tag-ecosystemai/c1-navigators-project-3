"""Shared fakes: a stand-in for the `openai` package so Azure code paths run with no network."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


class AzureStatusError(Exception):
    def __init__(self, message="", status_code=None, code=None):
        super().__init__(message)
        self.status_code, self.code = status_code, code


class FakeAzureOpenAI:
    """Records constructor kwargs; answers embeddings/chat from class-level settings."""

    instances: list = []
    embed_dim = 8
    chat_reply = '{"ok": true}'
    chat_script: list | None = None  # optional: a list of ready-made chat responses, consumed in order
    error: dict = {}  # {"embeddings": exc, "chat": exc}
    calls: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeAzureOpenAI.instances.append(self)
        self.embeddings = SimpleNamespace(create=self._embed)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))

    @classmethod
    def reset(cls):
        cls.instances, cls.calls, cls.error = [], [], {}
        cls.embed_dim, cls.chat_reply, cls.chat_script = 8, '{"ok": true}', None

    def _embed(self, model, input):  # noqa: A002 - matches the SDK signature
        FakeAzureOpenAI.calls.append(("embeddings", model))
        if "embeddings" in FakeAzureOpenAI.error:
            raise FakeAzureOpenAI.error["embeddings"]
        data = [SimpleNamespace(index=i, embedding=[float(i + 1)] + [0.5] * (self.embed_dim - 1)) for i in range(len(input))]
        return SimpleNamespace(data=data)

    def _chat(self, **kwargs):
        FakeAzureOpenAI.calls.append(("chat", kwargs))
        if "chat" in FakeAzureOpenAI.error:
            raise FakeAzureOpenAI.error["chat"]
        if FakeAzureOpenAI.chat_script:
            return FakeAzureOpenAI.chat_script.pop(0)
        return chat_response(FakeAzureOpenAI.chat_reply)


def chat_response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id, type="function", function=SimpleNamespace(name=name, arguments=arguments))


@pytest.fixture(autouse=True)
def _isolate_rag_env(tmp_path):
    """force_offline() edits os.environ directly, and tests must never touch the real policy index.
    Point the index at a temp dir and restore every RAG_*/AZURE_* variable afterwards."""
    import os

    from ai_engineering.rag import mode

    saved = {k: v for k, v in os.environ.items() if k.startswith(("RAG_", "AZURE_"))}
    # A developer's .env may hold real Azure credentials (it is loaded when the package is imported). Tests
    # must never use them: drop them so nothing can reach the network. Tests that need Azure use `azure_env`
    # with a fake client.
    for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY"):
        os.environ.pop(name, None)
    os.environ["RAG_INDEX_DIR"] = str(tmp_path / "default_index")
    mode.reset_caches()
    yield
    for key in [k for k in os.environ if k.startswith(("RAG_", "AZURE_"))]:
        del os.environ[key]
    os.environ.update(saved)
    mode.reset_caches()


@pytest.fixture
def fake_openai(monkeypatch):
    FakeAzureOpenAI.reset()
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AzureOpenAI=FakeAzureOpenAI))
    return FakeAzureOpenAI


@pytest.fixture
def azure_env(monkeypatch, tmp_path):
    """All five AZURE_OPENAI_* variables set (fake values) and Azure selected for every RAG part."""
    from ai_engineering.rag import mode

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake-resource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake-key-123")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "demo-chat")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "demo-embed")
    monkeypatch.setenv("RAG_EMBEDDINGS", "azure")
    monkeypatch.setenv("RAG_LLM", "azure")
    monkeypatch.setenv("RAG_STORE", "local")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "index"))
    mode.reset_caches()
    yield
    mode.reset_caches()
