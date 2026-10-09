"""Demo app: embedding cache, warm-up retry. (Azure is a fake client; nothing touches the network.)"""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient

from demo_app import service as service_module
from demo_app.server import create_app
from demo_app.service import DemoService


@pytest.fixture(autouse=True)
def _keep_cwd():
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


@pytest.fixture
def azure_app(fake_openai, azure_env):
    fake_openai.chat_reply = '{"rules": []}'
    return create_app(warm=False)


def _embedding_calls(fake_openai) -> int:
    return sum(1 for kind, _ in fake_openai.calls if kind == "embeddings")


def test_policy_topic_embeddings_are_fetched_once_per_process(azure_app, fake_openai):
    c = TestClient(azure_app)
    body = {"use_agents": True, "refresh": True}
    assert c.post("/api/investigate", json={"customer_id": "CUST-GOLD-002", **body}).json()["mode"] == "azure"
    after_first = _embedding_calls(fake_openai)
    assert after_first >= 16                       # the 16 topic queries were embedded
    assert c.post("/api/investigate", json={"customer_id": "CUST-GOLD-004", **body}).json()["mode"] == "azure"
    assert c.post("/api/investigate", json={"customer_id": "CUST-GOLD-001", **body}).json()["mode"] == "azure"
    assert _embedding_calls(fake_openai) == after_first   # later personas reuse them: no new embedding calls


def test_the_embedding_cache_returns_the_same_vectors_and_is_installed_once(azure_app):
    from ai_engineering.rag import tools

    svc = azure_app.state.service
    svc._ensure_embedding_cache()
    embedder = tools.get_retriever().embedder
    first = embedder.embed(["maximum debt to income"])
    second = embedder.embed(["maximum debt to income"])
    assert (first == second).all() and first is not second     # same numbers, a copy each time
    wrapped = embedder.embed
    svc._embed_cached = False
    svc._ensure_embedding_cache()                              # does not wrap twice
    assert embedder.embed is wrapped
    batch = embedder.embed(["a", "b"])                         # batches (index building) are never cached
    assert batch.shape[0] == 2


def test_warm_up_retries_a_persona_that_fell_back_then_moves_on(azure_app, monkeypatch):
    svc = azure_app.state.service
    svc._suspect_until = 0.0
    calls = []

    def fake_investigate(customer_id, use_agents=True, refresh=False):
        calls.append(customer_id)
        degraded = customer_id == "CUST-GOLD-001" and calls.count(customer_id) == 1
        return {"degraded_reason": "Azure OpenAI did not answer" if degraded else None}

    monkeypatch.setattr(svc, "investigate", fake_investigate)
    monkeypatch.setattr(service_module.time, "sleep", lambda s: None)
    svc.warm_state.update(done=0, running=True)
    svc._warm()
    assert calls.count("CUST-GOLD-001") == 2 and len(calls) == len(svc.cases) + 1
    assert svc.warm_state == {"done": 5, "total": 5, "running": False}


def test_warm_up_gives_up_after_three_attempts(azure_app, monkeypatch):
    svc = azure_app.state.service
    calls = []
    monkeypatch.setattr(svc, "investigate", lambda cid, use_agents=True, refresh=False: calls.append(cid) or {"degraded_reason": "down"})
    monkeypatch.setattr(service_module.time, "sleep", lambda s: None)
    svc._warm()
    assert len(calls) == 3 * len(svc.cases) and svc.warm_state["done"] == 5 and svc.warm_state["running"] is False


def test_offline_warm_up_does_not_retry(monkeypatch):
    svc = DemoService(offline=True, warm=False)
    calls = []
    monkeypatch.setattr(svc, "investigate", lambda cid, use_agents=True, refresh=False: calls.append(cid) or {"degraded_reason": "x"})
    monkeypatch.setattr(service_module.time, "sleep", lambda s: None)
    svc._warm()
    assert len(calls) == len(svc.cases)


def test_health_reports_warm_up_progress(azure_app):
    h = TestClient(azure_app).get("/api/health").json()
    assert h["warm"] == {"done": 0, "total": 5, "running": False}


def test_a_real_warm_up_fills_the_cache_so_every_click_is_instant():
    svc = DemoService(offline=True, warm=True)
    deadline = time.time() + 60
    while svc.warm_state["running"] and time.time() < deadline:
        time.sleep(0.1)
    assert svc.warm_state == {"done": 5, "total": 5, "running": False}
    app = create_app(service=svc)
    c = TestClient(app)
    for case in svc.cases:
        t = time.perf_counter()
        r = c.post("/api/investigate", json={"customer_id": case["applicant_id"]}).json()
        assert r["cached"] is True and (time.perf_counter() - t) < 0.5
