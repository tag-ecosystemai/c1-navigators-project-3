"""Demo web app: API contract, verdict parity with investigate(), fallback, secrets, static page."""

from __future__ import annotations

import json
import os
import re
import time

import pytest
from fastapi.testclient import TestClient

from ai_engineering.demo.cases import ROOT, application_of, load_cases, load_transactions, run_case
from ai_engineering.policy_engine.policy_evaluator import evaluate_policies
from ai_engineering.rag import tools
from demo_app import rules_view, service as service_module
from demo_app.server import STATIC, create_app
from demo_app.service import DemoService, _Redactor, _friendly

from .conftest import AzureStatusError

CASES = load_cases()
IDS = [c["applicant_id"] for c in CASES]
KEY, ENDPOINT, HOST = "fake-key-123", "https://fake-resource.openai.azure.com/", "fake-resource.openai.azure.com"


@pytest.fixture(autouse=True)
def _keep_cwd():
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


@pytest.fixture
def client():
    """Offline app (credentials are stripped by conftest): the safety-net mode."""
    with TestClient(create_app(offline=True, warm=False)) as c:
        yield c


@pytest.fixture
def azure_app(fake_openai, azure_env):
    """Azure mode against the fake openai package: the preflight passes at startup."""
    fake_openai.chat_reply = '{"rules": []}'
    app = create_app(warm=False)
    assert app.state.service.session.azure_mode
    return app


def post(c, cid, **kw):
    return c.post("/api/investigate", json={"customer_id": cid, **kw})


# ============================================================ personas, health, 404


def test_personas_returns_the_five_golden_customers_without_the_answer_key(client):
    r = client.get("/api/personas")
    assert r.status_code == 200
    personas = r.json()
    assert [p["id"] for p in personas] == IDS and len(personas) == 5
    for p in personas:
        assert p["name"] and p["tagline"] and p["headline"]["loan_amount"] and p["headline"]["credit_score"]
    assert "expected_verdict" not in r.text and "notes" not in personas[0]


def test_unknown_customer_is_a_clean_404_json(client):
    r = post(client, "CUST-NOPE")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["ok"] is False and body["error"] == "unknown_customer" and body["available"] == IDS


def test_an_unexpected_failure_is_never_a_500(client, monkeypatch):
    def boom(*a, **k):
        raise ValueError("kaboom")

    monkeypatch.setattr(client.app.state.service, "investigate", boom)
    r = post(client, IDS[0])
    assert r.status_code == 200 and r.json()["ok"] is False and r.json()["error"] == "investigation_failed"
    assert "kaboom" not in r.text


def test_health_offline(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["mode"] == "offline" and h["deployments"] is None
    assert isinstance(h["index_loaded"], bool) and h["policy_clauses_loaded"] >= 14 and h["personas"] == 5
    assert set(h["ml"]) == {"available", "reason"}


def test_health_azure_names_the_deployments_but_never_the_key_or_endpoint(azure_app):
    c = TestClient(azure_app)
    h = c.get("/api/health")
    assert h.json()["mode"] == "azure" and h.json()["deployments"] == {"chat": "demo-chat", "embeddings": "demo-embed"}
    assert KEY not in h.text and HOST not in h.text and "endpoint" not in h.text.lower().replace("index", "")


# ============================================================ verdict parity with investigate()


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("use_agents", [True, False])
def test_api_verdict_and_driver_equal_investigate(client, monkeypatch, cid, use_agents):
    monkeypatch.setattr(tools, "check_policy_compliance", lambda application: {"results": []})
    case = next(c for c in CASES if c["applicant_id"] == cid)
    _, direct = run_case(case, load_transactions())
    api = post(client, cid, use_agents=use_agents).json()
    decision = direct["report"]["final_decision"]
    assert api["ok"] and api["verdict"]["code"] == decision["verdict"]
    assert (api["verdict"]["driver"] or {}).get("code") == (None if decision["primary_driver"].startswith("All ") else decision["primary_driver"])
    # every rule status and number shown is the engine's
    assert {r["code"]: r["status"] for r in api["rules"]} == direct["report"]["policy_assessment"]
    fin = direct["report"]["financial_assessment"]
    dti = next(r for r in api["rules"] if r["code"] == "POL-DTI-001")
    assert dti["actual_num"] == pytest.approx(fin["dti_pct"])
    assert api["data_gaps"] == direct["report"]["data_gaps"]


def test_golden_verdicts_match_the_expected_ones(client):
    for case in CASES:
        assert post(client, case["applicant_id"]).json()["verdict"]["code"] == case["expected_verdict"]


# ============================================================ response contract


def test_response_contract_for_the_decline_case(client):
    d = post(client, "CUST-GOLD-002").json()
    assert d["ok"] and d["mode"] == "offline" and d["degraded_reason"] is None and d["cached"] is False
    assert d["verdict"]["label"] == "Decline recommended" and d["verdict"]["note"] == "Decision support only: a human makes the final decision."
    assert d["verdict"]["driver"]["code"] == "POL-INC-001" and "57.3%" in d["verdict"]["reason"]
    assert len(d["rules"]) == 14 and sum(d["rules_summary"].values()) == 14
    keys = {"code", "name", "status", "outcome", "decline_class", "is_driver", "actual", "threshold", "reason", "citation", "policy_excerpt"}
    for r in d["rules"]:
        assert keys <= set(r) and r["reason"] and r["threshold"] and r["citation"].startswith("Document Code")
    inc = next(r for r in d["rules"] if r["code"] == "POL-INC-001")
    assert inc["outcome"] == "fail" and inc["decline_class"] and inc["is_driver"] and inc["bar"]["marks"]
    assert d["ml"]["label"] == "Supporting signal. Does not change the verdict."
    assert d["explanation"]["source"] == "template" and "not by an LLM" in d["explanation"]["label"]
    assert d["checklist"][0]["priority"] == "high" and d["checklist"][-1]["id"] == "record"
    assert set(d["timings"]) == {"total_ms", "engine_ms"}


def test_agent_steps_are_reported_in_order_with_durations(client):
    steps = post(client, "CUST-GOLD-004", use_agents=True).json()["steps"]
    assert [s["key"] for s in steps] == ["data", "compliance", "credit", "explanation"]
    assert all(isinstance(s["duration_ms"], int) and s["duration_ms"] >= 0 and s["status"] for s in steps)
    direct = post(client, "CUST-GOLD-004", use_agents=False).json()["steps"]
    assert [s["key"] for s in direct] == ["engine", "explanation"]


def test_offline_cross_check_is_honest(client):
    x = post(client, "CUST-GOLD-001").json()["cross_check"]
    assert x["available"] is False and x["reason"] == "offline mode" and x["compared"] == 0 and x["total_rules"] == 14
    assert len(x["not_compared"]) == 14 and x["conflicts"] == []


def test_the_undisclosed_debt_case_shows_the_740_and_review(client):
    d = post(client, "CUST-GOLD-004").json()
    assert d["verdict"]["code"] == "FURTHER_REVIEW_REQUIRED" and d["verdict"]["driver"]["code"] == "POL-TXN-003"
    debt = next(r for r in d["rules"] if r["code"] == "POL-TXN-003")
    assert debt["actual_num"] == pytest.approx(740) and "$740" in debt["reason"] and debt["outcome"] == "fail"
    assert next(r for r in d["rules"] if r["code"] == "POL-NDI-001")["outcome"] == "review"


def test_the_clean_case_has_no_driver_and_all_rules_pass(client):
    d = post(client, "CUST-GOLD-001").json()
    assert d["verdict"]["code"] == "ELIGIBLE_FOR_APPROVAL" and d["verdict"]["driver"] is None
    assert d["rules_summary"] == {"pass": 14, "review": 0, "fail": 0, "missing": 0}


def test_ml_block_has_score_level_and_per_applicant_drivers_when_the_model_loads(client):
    ml = post(client, "CUST-GOLD-003").json()["ml"]
    if not ml["available"] or ml["precomputed"]:
        pytest.skip("live model not available here")
    assert 0.9 < ml["score"] <= 1 and ml["level"] == "HIGH_RISK"
    assert len(ml["drivers"]) == 5 and {d["effect"] for d in ml["drivers"]} <= {"raises risk", "lowers risk"}
    assert abs(sum(d["share"] for d in ml["drivers"])) <= 1.0001


def test_every_response_is_ascii_clean_with_no_dashes(client):
    for cid in IDS:
        text = json.dumps(post(client, cid).json(), ensure_ascii=False)
        assert text.isascii() and "—" not in text and "–" not in text and "Â" not in text


# ============================================================ caching


def test_repeat_click_is_served_from_the_cache_and_refresh_recomputes(client):
    first = post(client, "CUST-GOLD-002").json()
    t = time.perf_counter()
    second = post(client, "CUST-GOLD-002").json()
    assert second["cached"] is True and first["cached"] is False and (time.perf_counter() - t) < 0.5
    assert second["verdict"] == first["verdict"] and second["timings"] == first["timings"]
    assert post(client, "CUST-GOLD-002", refresh=True).json()["cached"] is False
    assert post(client, "CUST-GOLD-002", use_agents=False).json()["cached"] is False  # a different key


# ============================================================ Azure, fallback, secrets


def test_azure_mode_runs_and_reports_azure(azure_app):
    d = post(TestClient(azure_app), "CUST-GOLD-002").json()
    assert d["mode"] == "azure" and d["degraded_reason"] is None
    assert d["cross_check"]["available"] is True and d["cross_check"]["total_rules"] == 14


def test_azure_failure_falls_back_to_offline_with_a_reason_and_still_200(azure_app, fake_openai):
    c = TestClient(azure_app)
    direct = run_case(next(x for x in CASES if x["applicant_id"] == "CUST-GOLD-002"), load_transactions())[1]
    fake_openai.error = {"chat": AzureStatusError(f"unauthorized for {KEY} at {ENDPOINT}", status_code=401)}
    azure_app.state.service.azure_timeout = 5
    r = post(c, "CUST-GOLD-002")
    d = r.json()
    assert r.status_code == 200 and d["ok"] and d["mode"] == "offline"
    assert d["degraded_reason"] and "API key" in d["degraded_reason"]
    assert d["verdict"]["code"] == direct["report"]["final_decision"]["verdict"]       # same decision either way
    assert d["explanation"]["source"] == "template" and d["cross_check"]["available"] is False
    # the next click does not wait for another failing call, and says why
    again = post(c, "CUST-GOLD-004").json()
    assert again["mode"] == "offline" and "recent failure" in again["degraded_reason"] and "API key" in again["degraded_reason"]
    h = c.get("/api/health").json()
    assert h["mode"] == "offline" and h["last_failure"]["customer"] == "CUST-GOLD-002"
    for text in (r.text, json.dumps(again), json.dumps(h)):
        assert KEY not in text and HOST not in text and "fake-resource" not in text


def test_a_transient_azure_error_is_retried_once_before_falling_back(azure_app, monkeypatch):
    svc = azure_app.state.service
    monkeypatch.setattr(service_module, "AZURE_RETRY_PAUSE", 0)
    real, calls = DemoService._run, []

    def flaky(self, case, use_agents, offline):
        calls.append(offline)
        if not offline and calls.count(False) == 1:
            raise RuntimeError("429 too many requests")
        return real(self, case, use_agents, offline)

    monkeypatch.setattr(DemoService, "_run", flaky)
    d = post(TestClient(azure_app), "CUST-GOLD-002").json()
    assert d["mode"] == "azure" and d["degraded_reason"] is None and calls == [False, False]
    assert svc.last_failure is None


def test_azure_timeout_falls_back_to_offline(azure_app, monkeypatch):
    azure_app.state.service.azure_timeout = 0.2
    real = DemoService._run

    def slow(self, case, use_agents, offline):
        if not offline:
            time.sleep(1.0)
        return real(self, case, use_agents, offline)

    monkeypatch.setattr(DemoService, "_run", slow)
    d = post(TestClient(azure_app), "CUST-GOLD-004").json()
    assert d["mode"] == "offline" and "did not answer within 0.2s" in d["degraded_reason"]
    assert d["verdict"]["code"] == "FURTHER_REVIEW_REQUIRED"


def test_a_degraded_azure_result_is_not_cached_so_the_next_click_retries(azure_app, fake_openai):
    c = TestClient(azure_app)
    fake_openai.error = {"chat": AzureStatusError("rate limited", status_code=429)}
    azure_app.state.service.azure_timeout = 5
    assert post(c, "CUST-GOLD-002").json()["mode"] == "offline"
    assert ("CUST-GOLD-002", True) not in azure_app.state.service.cache


def test_a_failed_azure_preflight_at_startup_serves_offline_with_the_reason(fake_openai, azure_env):
    fake_openai.error = {"embeddings": AzureStatusError("nope", status_code=404, code="DeploymentNotFound")}
    app = create_app(warm=False)
    c = TestClient(app)
    h = c.get("/api/health").json()
    assert h["mode"] == "offline" and "preflight failed" in h["degraded_reason"] and "demo-embed" in h["degraded_reason"]
    d = post(c, "CUST-GOLD-002").json()
    assert d["ok"] and d["mode"] == "offline" and "preflight failed" in d["degraded_reason"]
    assert ("CUST-GOLD-002", True) in app.state.service.cache  # stable offline results stay cached


def test_no_response_ever_contains_the_key_or_the_endpoint(azure_app, fake_openai):
    c = TestClient(azure_app)
    texts = [c.get("/api/health").text, c.get("/api/personas").text, c.get("/").text]
    for cid in IDS:
        texts.append(post(c, cid).text)
    fake_openai.error = {"embeddings": RuntimeError(f"connect failed to {ENDPOINT} with key {KEY}")}
    for cid in IDS:
        texts.append(post(c, cid, refresh=True).text)
    texts.append(c.get("/api/health").text)
    for text in texts:
        assert KEY not in text and HOST not in text and "fake-resource" not in text and "https://" not in text


def test_redactor_and_friendly_reason(azure_env):
    red = _Redactor()
    assert red(f"failed at {ENDPOINT} using {KEY} on {HOST}") == "failed at [redacted] using [redacted] on [redacted]"
    assert "[url]" in red("see https://example.com/x?y=1 now")
    assert _friendly("AzureCallError: Azure OpenAI rejected the API key (401).") == "Azure OpenAI rejected the API key (401)."
    assert _friendly(None) == "unknown problem"


# ============================================================ policy excerpts


def test_policy_excerpts_keep_currency_signs_and_drop_latex_and_markdown():
    from demo_app.service import _excerpt

    text = ("**Applicant with Dependents:** Minimum required NDI buffer of **$800.00 USD/month** + $200 per additional "
            "dependent child. Low Risk ($\\le$ 35.0%). $$\\text{DTI} = \\frac{a}{b} \\times 100\\%$$ done")
    out = _excerpt(text)
    assert "$800.00 USD/month" in out and "+ $200 per" in out and "(<= 35.0%)" in out
    assert "$$" not in out and "frac" not in out and "**" not in out and "(formula)" in out
    assert len(_excerpt("word " * 400, limit=100)) <= 100


def test_every_rule_has_a_clean_policy_citation_and_excerpt(client):
    d = post(client, "CUST-GOLD-004").json()
    for r in d["rules"]:
        assert r["citation"] and r["policy_excerpt"] and "$$" not in r["policy_excerpt"] and "\\" not in r["policy_excerpt"]
    ndi = next(r for r in d["rules"] if r["code"] == "POL-NDI-001")
    assert "$500" in ndi["policy_excerpt"] and "$800" in ndi["policy_excerpt"]


# ============================================================ static page


def test_the_placeholder_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "Credit-Risk Investigation Agent" in r.text
def test_the_page_source_has_no_dashes_or_mojibake():
    text = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "—" not in text and "–" not in text and "Â" not in text and "â€" not in text


# ============================================================ display thresholds mirror the evaluator


def _policy(app=None, fin=None, txn=None):
    application = {"age": 40, "declared_monthly_net_income": 5000, "employment_length_months": 24, "credit_score": 700,
                   "bankruptcies_count": 0, "tax_liens_count": 0, "dependents_count": 0, **(app or {})}
    financial = {"dti_pct": 20.0, "lti_ratio": 0.2, "ndi_amount": 2000.0, "income_variance_pct": 0.0, **(fin or {})}
    transactions = {"gambling_pct_of_income": 0.0, "nsf_event_count": 0, "undisclosed_debt_total": 0.0,
                    "window_dressing_events": [], "burn_rate_status": "HEALTHY", **(txn or {})}
    return evaluate_policies({"application": application}, financial, transactions)["data"]


def test_dti_bands_match_the_evaluator():
    a, b, c = rules_view.DTI_BANDS
    expect = [(a, "SATISFIED"), (a + .1, "CONDITIONAL"), (b, "CONDITIONAL"), (b + .1, "FLAG_FOR_REVIEW"), (c, "FLAG_FOR_REVIEW"), (c + .1, "NOT_SATISFIED")]
    for value, status in expect:
        assert _policy(fin={"dti_pct": value})["POL-DTI-001"] == status, value


def test_lti_caps_match_the_evaluator():
    scores = {"Tier 1": 750, "Tier 2": 690, "Tier 3": 620, "Tier 4": 550}
    for tier, cap in rules_view.LTI_CAPS.items():
        score = {"credit_score": scores[tier]}
        assert _policy(score, {"lti_ratio": cap})["POL-LTI-001"] == "SATISFIED", tier
        assert _policy(score, {"lti_ratio": cap + rules_view.LTI_REVIEW_MARGIN})["POL-LTI-001"] == "FLAG_FOR_REVIEW", tier
        assert _policy(score, {"lti_ratio": cap + rules_view.LTI_REVIEW_MARGIN + .001})["POL-LTI-001"] == "NOT_SATISFIED", tier


def test_income_gambling_income_tenure_and_age_limits_match_the_evaluator():
    lo, hi = rules_view.INC_BANDS
    assert [_policy(fin={"income_variance_pct": v})["POL-INC-001"] for v in (lo, lo + .1, hi, hi + .1)] == [
        "SATISFIED", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "HIGH_RISK"]
    g_lo, g_hi = rules_view.GAMBLING_BANDS
    assert [_policy(txn={"gambling_pct_of_income": v})["POL-TXN-001"] for v in (g_lo - .01, g_lo, g_hi, g_hi + .1)] == [
        "SATISFIED", "FLAG_FOR_REVIEW", "FLAG_FOR_REVIEW", "NOT_SATISFIED"]
    assert _policy({"declared_monthly_net_income": rules_view.MIN_INCOME})["POL-ELG-002"] == "SATISFIED"
    assert _policy({"declared_monthly_net_income": rules_view.MIN_INCOME - 1})["POL-ELG-002"] == "NOT_SATISFIED"
    assert _policy({"employment_length_months": rules_view.MIN_TENURE_MONTHS})["POL-ELG-003"] == "SATISFIED"
    assert _policy({"employment_length_months": rules_view.MIN_TENURE_MONTHS - 1})["POL-ELG-003"] == "FLAG_FOR_REVIEW"
    a_lo, a_hi = rules_view.AGE_RANGE
    assert [_policy({"age": v})["POL-ELG-001"] for v in (a_lo - 1, a_lo, a_hi, a_hi + 1)] == [
        "NOT_SATISFIED", "SATISFIED", "SATISFIED", "NOT_SATISFIED"]


def test_outcome_classes_follow_the_decision_matrix():
    assert rules_view.outcome("POL-SCR-001", "Tier 4") == "fail" and rules_view.is_decline_class("POL-SCR-001", "Tier 4")
    assert rules_view.outcome("POL-SCR-001", "Tier 3") == "review" and rules_view.outcome("POL-SCR-001", "Tier 2") == "pass"
    assert rules_view.outcome("POL-TXN-003", "NOT_SATISFIED") == "fail" and not rules_view.is_decline_class("POL-TXN-003", "NOT_SATISFIED")
    assert rules_view.outcome("POL-TXN-002", "KNOCKOUT") == "fail" and rules_view.outcome("POL-TXN-002", "CAUTION") == "review"
    assert rules_view.outcome("POL-NDI-001", "MISSING_DATA") == "missing"


def test_missing_data_reason_names_the_missing_field():
    out = rules_view.describe_rule("POL-NDI-001", "MISSING_DATA", {}, {}, {}, {"POL-NDI-001": ["declared_monthly_living_expenses"]})
    assert "declared_monthly_living_expenses" in out["reason"]


def test_negative_amounts_and_status_words_read_naturally():
    ndi = rules_view.describe_rule("POL-NDI-001", "NOT_SATISFIED", {"dependents_count": 0}, {"ndi_amount": -501.33}, {}, {})
    assert ndi["actual"] == "-$501.33/month" and "$-" not in ndi["reason"] and "negative" in ndi["reason"]
    burn = rules_view.describe_rule("POL-TXN-005", "CRITICAL_DISTRESS", {}, {}, {}, {})
    assert burn["actual"] == "Critical distress" and "_" not in burn["actual"]
