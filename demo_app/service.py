"""Demo app service: runs the existing engine for a golden persona and shapes the result for the UI.

Nothing here decides anything. The verdict, driver, rule statuses, ML score, cross-check and explanation all come
from the existing code (run_case / run_case_agents / OrchestratorAgent / investigate). This module adds timings,
display text, an analyst checklist, caching, secret redaction and a graceful Azure -> offline fallback.
"""

from __future__ import annotations

import concurrent.futures
import contextvars
import copy
import logging
import re
import threading
import time
from urllib.parse import urlparse

from ai_engineering.demo.cases import find_case, load_cases, load_transactions, run_case, run_case_agents
from ai_engineering.demo.explain import TEMPLATE_LABEL, explain
from ai_engineering.demo.ml_probe import ml_status
from ai_engineering.demo.render import ascii_safe
from ai_engineering.demo.session import PreflightFailed, start_session
from ai_engineering.demo.view import RULE_TITLES, build_view
from ai_engineering.ml_scoring import ml_integration
from ai_engineering.ml_scoring.model_features import derive_features
from ai_engineering.orchestrator import agents as agents_module
from ai_engineering.orchestrator import orchestrator as orchestrator_module
from ai_engineering.rag import mode
from ai_engineering.rag.azure_client import azure_configured
from ai_engineering.rag.chunking import chunk_documents
from ai_engineering.rag.config import get_settings
from ai_engineering.rag.loaders import load_directory

from .rules_view import ACTIONS, describe_rule, is_decline_class, outcome

VERDICT_LABELS = {
    "ELIGIBLE_FOR_APPROVAL": "Eligible for approval",
    "FURTHER_REVIEW_REQUIRED": "Further review required",
    "DECLINE_RECOMMENDED": "Decline recommended",
}
ML_LABEL = "Supporting signal. Does not change the verdict."
DECISION_NOTE = "Decision support only: a human makes the final decision."
AZURE_SUSPECT_SECONDS = 20
AZURE_RETRY_PAUSE = 2.0

PERSONAS = {
    "GOLDEN_PRIME_APPROVAL": "Prime borrower with stable income and a clean bank statement",
    "GOLDEN_INCOME_DISCREPANCY": "Declared income is far higher than what the bank deposits show",
    "GOLDEN_GAMBLING_NSF": "Heavy gambling spend and repeated overdraft events",
    "GOLDEN_UNDISCLOSED_DEBT": "Looks affordable, but the bank statement hides loan payments",
    "GOLDEN_KNOCKOUT_FAIL": "Low credit score, low income and a recent bankruptcy",
}

FEATURE_LABELS = {
    "dti": "Debt-to-income ratio", "loan_to_income": "Loan relative to monthly income",
    "expense_to_income": "Housing cost relative to income", "debt_to_income": "Existing debt relative to income",
    "credit_score": "Credit score", "credit_score_tier_num": "Credit tier",
    "income_stability": "Gap between declared and actual salary", "gambling_ratio": "Gambling spend",
    "savings_rate": "Savings rate", "monthly_payment_ratio": "New payment relative to income",
    "lti_ratio": "Loan-to-income ratio", "monthly_inflows": "Total money in", "monthly_outflows": "Total money out",
    "anomaly_score": "Flagged transactions", "txn_density": "Transaction activity",
    "avg_txn_amount": "Average transaction size", "dependents_count": "Dependents",
    "bankruptcies_count": "Bankruptcies", "tax_liens_count": "Tax liens",
    "employment_length_months": "Months in current job",
}


class UnknownCustomer(KeyError):
    pass


log = logging.getLogger("demo_app")

# ------------------------------------------------------------------ per-request offline switch

_OFFLINE_RUN: contextvars.ContextVar[bool] = contextvars.ContextVar("demo_offline_run", default=False)


def _raise_offline(application):
    raise RuntimeError("offline mode: the policy checker was not run")


def _install_cross_check_switch() -> None:
    """Make the policy cross-check skippable for ONE request (a context variable), without touching global state,
    so a failed Azure call never turns other requests offline. Wraps the callers' references at runtime; no
    engine file is edited, and with the variable unset the original function runs unchanged."""
    for module in (orchestrator_module, agents_module):
        current = module.run_cross_check
        if getattr(current, "_demo_switch", False):
            continue

        def make(real):
            def switched(application, evaluator_flags, check_fn=None):
                if _OFFLINE_RUN.get():
                    return real(application, evaluator_flags, check_fn=_raise_offline)
                return real(application, evaluator_flags, check_fn)

            switched._demo_switch = True
            return switched

        module.run_cross_check = make(current)


# ------------------------------------------------------------------ helpers


def _policy_clauses() -> dict[str, dict]:
    """rule code -> {citation, text}, from the policy documents (no embeddings, no network)."""
    settings = get_settings()
    docs = load_directory(settings.policy_dir)
    out: dict[str, dict] = {}
    for chunk in chunk_documents(docs, settings.chunk_max_chars, settings.chunk_overlap_chars):
        for code in chunk.clauses:
            out.setdefault(code, {"citation": chunk.citation, "text": chunk.text})
    return out


_LATEX_SYMBOLS = {r"\le": "<=", r"\leq": "<=", r"\ge": ">=", r"\geq": ">=", r"\times": "x", r"\%": "%"}


def _excerpt(text: str, limit: int = 600) -> str:
    """Policy text as one readable line: markdown and LaTeX removed, currency signs kept."""
    text = re.sub(r"\$\$.*?\$\$", " (formula) ", text, flags=re.S)          # display math blocks
    for latex, plain in _LATEX_SYMBOLS.items():
        text = text.replace("$" + latex + "$", plain).replace(latex, plain)
    text = re.sub(r"[*#`|\\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _friendly(reason: str | None) -> str:
    """A short, plain reason with no class names and no URLs."""
    text = (reason or "unknown problem").strip()
    text = re.sub(r"^(?:AzureCallError|RuntimeError|Exception|TimeoutError)\b:?\s*", "", text)
    text = text.replace("Azure explanation unavailable (", "Azure OpenAI explanation failed (").rstrip(")")
    return text[:240] or "Azure OpenAI did not respond"


def _summarize_preflight(message: str) -> str:
    fails = [line.strip() for line in message.splitlines() if line.strip().startswith("[FAIL]")]
    fixes = [line.strip() for line in message.splitlines() if line.strip().startswith("fix:")]
    text = "Azure OpenAI preflight failed: " + "; ".join(f.replace("[FAIL] ", "") for f in fails[:3])
    return (text + (". " + fixes[0] if fixes else ""))[:400]


class _Redactor:
    """Removes the API key, the endpoint (full, host) and any URL from text before it leaves the server."""

    def __init__(self):
        s = get_settings()
        literals = [s.azure_openai_api_key, s.azure_openai_endpoint, s.azure_search_api_key, s.azure_search_endpoint]
        for endpoint in (s.azure_openai_endpoint, s.azure_search_endpoint):
            host = urlparse(endpoint or "").hostname
            if host:
                literals += [host, host.split(".")[0]]
        self.literals = sorted({x for x in literals if x and len(x) >= 4}, key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for literal in self.literals:
            text = text.replace(literal, "[redacted]")
        return re.sub(r"https?://[^\s'\")]+", "[url]", text)


def _ml_drivers(application: dict, transactions: list[dict], financial: dict) -> tuple[list[dict], str | None]:
    """Top reasons for THIS applicant's score, from the model's own per-prediction contributions."""
    try:
        import numpy as np
        import xgboost as xgb

        model = ml_integration._load_model()
        if model is None:
            return [], "per-case drivers need the live model"
        features = derive_features(application, transactions, financial)
        order = list(getattr(model, "feature_names_in_", features))
        x = np.array([[features[name] for name in order]], dtype=float)
        contributions = model.get_booster().predict(xgb.DMatrix(x, feature_names=order), pred_contribs=True)[0][:-1]
        total = float(np.abs(contributions).sum()) or 1.0
        ranked = sorted(zip(order, contributions), key=lambda item: -abs(item[1]))[:5]
        return [{"feature": name, "label": FEATURE_LABELS.get(name, name), "value": round(features[name], 2),
                 "effect": "raises risk" if c > 0 else "lowers risk", "share": round(abs(float(c)) / total, 3)}
                for name, c in ranked], None
    except Exception as exc:  # noqa: BLE001 - drivers are optional
        return [], f"per-case drivers unavailable ({type(exc).__name__})"


# ------------------------------------------------------------------ the service


class DemoService:
    def __init__(self, offline: bool = False, warm: bool = True, azure_timeout: float | None = None):
        import os

        _install_cross_check_switch()
        self.cases = load_cases()
        self.transactions = load_transactions()
        self.clauses = _policy_clauses()
        self.azure_timeout = azure_timeout if azure_timeout is not None else float(os.getenv("DEMO_AZURE_TIMEOUT", "60"))
        self.cache: dict[tuple, dict] = {}
        self._locks: dict[tuple, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._suspect_until = 0.0
        self.last_failure: dict | None = None
        self._embed_lock = threading.Lock()
        self._embed_cached = False
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix="azure")
        self.warm_state = {"done": 0, "total": len(self.cases), "running": False}

        self.azure_expected = (not offline) and azure_configured(get_settings())
        self.startup_note: str | None = None
        try:
            self.session = start_session(offline=offline)
        except PreflightFailed as exc:
            self.startup_note = _summarize_preflight(str(exc))
            self.session = start_session(offline=True)
        if self.azure_expected and self.session.azure_mode:
            self.azure_verified = True
        else:
            self.azure_verified = False
        self.forced_offline = offline
        if warm:
            self.warm_state["running"] = True
            threading.Thread(target=self._warm, daemon=True, name="warm").start()

    # ---- public API
    @property
    def mode(self) -> str:
        return "azure" if self.session.azure_mode and time.time() >= self._suspect_until else "offline"

    def health(self) -> dict:
        s = get_settings()
        azure = self.session.azure_mode
        return {
            "status": "ok",
            "mode": self.mode,
            "azure_configured": azure_configured(s),
            "azure_verified": self.azure_verified,
            "degraded_reason": self._standing_reason(),
            "last_failure": self._clean(self.last_failure) if self.last_failure else None,
            "index_loaded": (s.index_dir / "manifest.json").exists(),
            "policy_clauses_loaded": len(self.clauses),
            "deployments": {"chat": s.chat_deployment, "embeddings": s.embedding_deployment} if azure else None,
            "ml": {"available": self.session.ml_enabled, "reason": self.session.ml_reason},
            "warm": dict(self.warm_state),
            "personas": len(self.cases),
        }

    def personas(self) -> list[dict]:
        out = []
        for case in self.cases:
            out.append({
                "id": case["applicant_id"], "name": case.get("full_name", ""),
                "persona": case.get("persona_type", ""), "tagline": PERSONAS.get(case.get("persona_type", ""), ""),
                "age": case.get("age"), "job": case.get("job_title", ""),
                "headline": {"loan_amount": case.get("requested_loan_amount"), "loan_term_months": case.get("loan_term_months"),
                             "credit_score": case.get("credit_score"), "monthly_income": case.get("declared_monthly_net_income"),
                             "loan_purpose": str(case.get("loan_purpose", "")).replace("_", " ").title()},
            })
        return self._clean(out)

    def investigate(self, customer_id: str, use_agents: bool = True, refresh: bool = False) -> dict:
        try:
            case = find_case(self.cases, customer_id)
        except KeyError as exc:
            raise UnknownCustomer(customer_id) from exc
        key = (case["applicant_id"], bool(use_agents))
        with self._lock_for(key):
            if not refresh and key in self.cache:
                hit = copy.deepcopy(self.cache[key])
                hit["cached"] = True
                return hit
            started = time.perf_counter()
            response = self._compute(case, bool(use_agents))
            response["timings"]["total_ms"] = round((time.perf_counter() - started) * 1000)
            if not response["degraded_reason"] or not self.session.azure_mode:
                # a transient Azure fallback is not cached (the next click retries); results of a process that is
                # offline for good (forced, or Azure unavailable at startup) are stable, so they are
                self.cache[key] = copy.deepcopy(response)
            return response

    # ---- internals
    def _lock_for(self, key) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _warm(self) -> None:
        """Pre-run every persona so the first click is instant. A persona that had to fall back to offline is
        retried (twice at most) once the fallback window has passed."""
        for case in self.cases:
            for attempt in range(3):
                try:
                    response = self.investigate(case["applicant_id"], True)
                except Exception:  # noqa: BLE001 - warming is best effort
                    break
                if not response.get("degraded_reason") or not self.session.azure_mode:
                    break
                time.sleep(max(0.0, self._suspect_until - time.time()) + 1.0)
            self.warm_state["done"] += 1
            time.sleep(1.0)
        self.warm_state["running"] = False

    def _standing_reason(self) -> str | None:
        if time.time() < self._suspect_until:
            return self._recent_failure_text()
        return self._clean(self.startup_note) if self.azure_expected and not self.session.azure_mode else None

    def _ensure_embedding_cache(self) -> None:
        """The policy checker embeds the same 16 fixed topic queries for every case (about 1 s each on Azure). The
        vector for a given text never changes, so keep them in memory for the life of this process. Results are
        identical; only repeated network calls are saved. Wraps the embedder object at runtime; no RAG file changes."""
        if self._embed_cached:
            return
        with self._embed_lock:
            if self._embed_cached:
                return
            from ai_engineering.rag import tools

            embedder = tools.get_retriever().embedder
            if not getattr(embedder.embed, "_demo_cache", False):
                real, cache = embedder.embed, {}

                def cached(texts):
                    if len(texts) == 1:
                        if texts[0] not in cache:
                            cache[texts[0]] = real(texts)
                        return cache[texts[0]].copy()
                    return real(texts)

                cached._demo_cache = True
                embedder.embed = cached
            self._embed_cached = True

    def _recent_failure_text(self) -> str:
        why = f" ({self.last_failure['reason']})" if self.last_failure else ""
        return f"Azure OpenAI had a recent failure{why}; showing offline results, retrying in {max(1, int(self._suspect_until - time.time()))}s."

    def _try_azure(self, case: dict, use_agents: bool) -> tuple[dict | None, str | None]:
        """One Azure attempt (plus one retry for a transient error). Returns (engine, None) or (None, reason)."""
        reason = None
        for attempt in range(2):
            try:
                future = self._pool.submit(self._run, case, use_agents, False)
                engine = future.result(timeout=self.azure_timeout)
                problem = self._azure_problem(engine)
                if not problem:
                    return engine, None
                reason = _friendly(problem)
            except concurrent.futures.TimeoutError:
                return None, f"Azure OpenAI did not answer within {self.azure_timeout:g}s"  # no retry: already waited
            except Exception as exc:  # noqa: BLE001 - any Azure problem: fall back, never fail the UI
                reason = _friendly(str(exc) or type(exc).__name__)
            if attempt == 0:
                log.warning("Azure attempt failed for %s (%s); retrying once", case["applicant_id"], reason)
                time.sleep(AZURE_RETRY_PAUSE)
        return None, reason

    def _compute(self, case: dict, use_agents: bool) -> dict:
        degraded = None
        engine = None
        if self.session.azure_mode and time.time() >= self._suspect_until:
            engine, reason = self._try_azure(case, use_agents)
            if engine is None:
                degraded = reason
                self.last_failure = {"customer": case["applicant_id"], "reason": reason, "at": time.strftime("%H:%M:%S")}
                log.warning("Azure failed for %s: %s; falling back to offline", case["applicant_id"], reason)
                self._suspect_until = time.time() + AZURE_SUSPECT_SECONDS
        elif self.session.azure_mode:
            degraded = self._recent_failure_text()
        elif self.azure_expected:
            degraded = self.startup_note
        if engine is None:
            engine = self._run(case, use_agents, True)
        return self._assemble(case, engine, "offline" if engine["offline"] else "azure", degraded, use_agents)

    @staticmethod
    def _azure_problem(engine: dict) -> str | None:
        cross = engine["result"]["report"].get("policy_cross_check") or {}
        if not cross.get("available"):
            return "Azure policy cross-check failed: " + _friendly(cross.get("error"))
        note = engine["explanation"].get("note") or ""
        if note.startswith("Azure explanation unavailable"):
            return note
        return None

    def _run(self, case: dict, use_agents: bool, offline: bool) -> dict:
        """One engine run. `offline=True` skips the Azure policy checker and the Azure explanation (template)."""
        token = _OFFLINE_RUN.set(offline)
        try:
            if not offline:
                self._ensure_embedding_cache()
            llm = None if offline else self.session.llm
            ml_enabled = self.session.ml_enabled
            steps_raw: dict[str, tuple[float, float]] = {}
            t0 = time.perf_counter()
            if use_agents:
                from ai_engineering.orchestrator.agents import OrchestratorAgent

                agent = OrchestratorAgent(llm_client=llm)
                for obj, method, name in ((agent.data_agent, "run", "data"), (agent.compliance_agent, "run", "compliance"),
                                          (agent.credit_agent, "run", "credit"), (agent.llm_agent, "explain_view", "explanation")):
                    setattr(obj, method, _timed(getattr(obj, method), name, steps_raw))
                from ai_engineering.demo.cases import case_payload

                application, payload = case_payload(case, self.transactions, ml_enabled)
                result = agent.run(payload)
                explanation = {**result["explanation_detail"], "text": result["explanation"]}
                view = build_view(case, application, result, mode.banner(), not offline and self.session.azure_mode, self.session.ml_reason)
            else:
                application, result = run_case(case, self.transactions, ml_enabled=ml_enabled)
                view = build_view(case, application, result, mode.banner(), not offline and self.session.azure_mode, self.session.ml_reason)
                steps_raw["engine"] = (t0, time.perf_counter())
                e0 = time.perf_counter()
                explanation = explain(view, llm)
                steps_raw["explanation"] = (e0, time.perf_counter())
            return {"application": application, "result": result, "view": view, "explanation": explanation,
                    "steps_raw": steps_raw, "offline": offline, "started": t0, "ended": time.perf_counter()}
        finally:
            _OFFLINE_RUN.reset(token)

    # ---- response shaping
    def _assemble(self, case: dict, engine: dict, mode_name: str, degraded: str | None, use_agents: bool) -> dict:
        result, view, application = engine["result"], engine["view"], engine["application"]
        report = result["report"]
        fin, txn = report["financial_assessment"], report["transaction_assessment"]
        gaps = {g["rule"]: g["missing_fields"] for g in report.get("data_gaps", [])}
        verdict_code = report["final_decision"]["verdict"]
        driver_code = report["final_decision"]["primary_driver"]

        rules = []
        for r in view["rules"]:
            detail = describe_rule(r["code"], r["status"], application, fin, txn, gaps)
            clause = self.clauses.get(r["code"], {})
            rules.append({
                "code": r["code"], "name": RULE_TITLES.get(r["code"], r["code"]), "status": r["status"],
                "outcome": outcome(r["code"], r["status"]), "decline_class": is_decline_class(r["code"], r["status"]),
                "is_driver": r["code"] == driver_code, **detail,
                "citation": clause.get("citation", ""), "policy_excerpt": _excerpt(clause.get("text", "")),
            })
        by_code = {r["code"]: r for r in rules}
        counts = {k: sum(1 for r in rules if r["outcome"] == k) for k in ("pass", "review", "fail", "missing")}

        cross = self._cross_check(report.get("policy_cross_check") or {}, by_code)
        ml = self._ml(result, view, application, fin)
        explanation = engine["explanation"]
        source = "azure" if str(explanation.get("source", "")).startswith("azure") else "template"
        steps = self._steps(engine, result, cross, explanation, use_agents)

        response = {
            "ok": True, "customer_id": case["applicant_id"], "use_agents": use_agents, "mode": mode_name,
            "degraded_reason": degraded, "cached": False,
            "applicant": {"id": case["applicant_id"], "name": case.get("full_name", ""), "age": case.get("age"),
                          "job": case.get("job_title", ""), "loan_amount": case.get("requested_loan_amount"),
                          "loan_term_months": case.get("loan_term_months"), "credit_score": case.get("credit_score"),
                          "monthly_income": case.get("declared_monthly_net_income"),
                          "loan_purpose": str(case.get("loan_purpose", "")).replace("_", " ").title()},
            "verdict": {"code": verdict_code, "label": VERDICT_LABELS.get(verdict_code, verdict_code),
                        "reason": self._verdict_reason(verdict_code, by_code.get(driver_code), rules),
                        "driver": ({"code": driver_code, "name": by_code[driver_code]["name"], "reason": by_code[driver_code]["reason"]}
                                   if driver_code in by_code else None),
                        "note": DECISION_NOTE},
            "rules": rules, "rules_summary": counts, "data_gaps": report.get("data_gaps", []),
            "ml": ml, "cross_check": cross,
            "explanation": {"text": explanation["text"], "source": source, "label": explanation.get("label") or TEMPLATE_LABEL,
                            "note": explanation.get("note")},
            "checklist": self._checklist(verdict_code, rules, cross, report.get("data_gaps", [])),
            "steps": steps,
            "timings": {"total_ms": 0, "engine_ms": round((engine["ended"] - engine["started"]) * 1000)},
            "system": {"status": result["system"]["status"], "modules_failed": result["system"]["modules_failed"]},
        }
        return self._clean(response)

    @staticmethod
    def _verdict_reason(verdict: str, driver: dict | None, rules: list[dict]) -> str:
        others = [r for r in rules if r["outcome"] in ("review", "fail") and not r["is_driver"]]
        tail = f" {len(others)} other rule(s) also need attention." if others else ""
        if verdict == "ELIGIBLE_FOR_APPROVAL":
            return "Every evaluated rule is clean, so the case meets the standard approval criteria."
        if driver is None:
            return "The rule engine produced no result, so a person must review the case."
        if verdict == "DECLINE_RECOMMENDED":
            return f"{driver['name']}: {driver['reason']} The decision matrix treats this as a decline." + tail
        return f"{driver['name']}: {driver['reason']} The policy gives no automatic verdict for this, so a person decides." + tail

    @staticmethod
    def _cross_check(cross: dict, by_code: dict) -> dict:
        total = len(by_code)
        if not cross.get("available"):
            err = cross.get("error") or ""
            reason = "offline mode" if "offline" in err.lower() else (_friendly(err) if err else "")
            return {"available": False, "reason": reason, "total_rules": total, "compared": 0, "agree": 0,
                    "soft_conflicts": 0, "hard_conflicts": 0, "conflicts": [],
                    "not_compared": [{"code": c, "name": by_code[c]["name"], "reason": "The policy checker was not run."} for c in by_code]}
        rules = cross.get("rules") or {}
        agree = soft = hard = 0
        conflicts, not_compared = [], []
        for code, entry in rules.items():
            agreement = entry.get("agreement")
            name = by_code.get(code, {}).get("name", code)
            if agreement == "agree":
                agree += 1
            elif agreement in ("soft_conflict", "hard_conflict"):
                soft += agreement == "soft_conflict"
                hard += agreement == "hard_conflict"
                conflicts.append({
                    "code": code, "name": name, "kind": agreement, "evaluator": entry.get("evaluator"),
                    "rag_outcome": entry.get("rag_outcome"), "citation": entry.get("citation"),
                    "quote": _excerpt(entry.get("quote") or "", 320), "explanation": entry.get("explanation"),
                    "note": ("Likely cause: this rule is a formula (a base amount plus an amount per dependent), which the policy "
                             "checker cannot turn into one threshold, so it stays cautious. The rule engine computed the buffer.")
                    if code == "POL-NDI-001" and entry.get("rag_outcome") == "review" else
                    "The policy checker read the clause more cautiously than the rule engine. A person should read the cited text.",
                })
            else:
                why = ("An informational label, not a pass or fail result." if agreement == "not_compared"
                       else "The policy checker returned nothing comparable for this rule.")
                not_compared.append({"code": code, "name": name, "reason": why})
        seen = set(rules)
        not_compared += [{"code": c, "name": by_code[c]["name"], "reason": "The policy checker returned nothing for this rule."}
                         for c in by_code if c not in seen]
        compared = agree + soft + hard + sum(1 for e in rules.values() if e.get("agreement") == "rag_only")
        return {"available": True, "reason": None, "total_rules": total, "compared": compared, "agree": agree,
                "soft_conflicts": soft, "hard_conflicts": hard, "conflicts": conflicts, "not_compared": not_compared}

    def _ml(self, result: dict, view: dict, application: dict, fin: dict) -> dict:
        info = view["ml"]
        drivers, note = [], None
        if info.get("available") and not info.get("precomputed"):
            txns = [t for t in self.transactions if t.get("applicant_id") == application.get("applicant_id")]
            drivers, note = _ml_drivers(application, txns, fin)
        elif info.get("precomputed"):
            note = "Per-applicant drivers need the live model; this score is a stored batch prediction."
        return {"available": bool(info.get("available")), "precomputed": bool(info.get("precomputed")),
                "score": info.get("score"), "level": info.get("level"), "label": ML_LABEL, "text": info.get("text"),
                "drivers": drivers, "drivers_note": note}

    @staticmethod
    def _steps(engine: dict, result: dict, cross: dict, explanation: dict, use_agents: bool) -> list[dict]:
        raw = engine["steps_raw"]
        ms = lambda a, b: round((b - a) * 1000)  # noqa: E731
        failed = set(result["system"]["modules_failed"])
        if not use_agents:
            e = raw["engine"]
            x = raw["explanation"]
            return [{"key": "engine", "name": "Investigation engine", "status": "ok", "duration_ms": ms(*e),
                     "detail": "Direct investigate() call"},
                    {"key": "explanation", "name": "Explanation", "status": "ok", "duration_ms": ms(*x), "detail": ""}]
        data, comp, credit, expl = raw.get("data"), raw.get("compliance"), raw.get("credit"), raw.get("explanation")
        comp_end = (credit[0] if credit else (comp[1] if comp else 0))  # the gap before credit risk is the cross-check
        steps = [
            {"key": "data", "name": "Data analysis", "duration_ms": ms(*data) if data else 0,
             "status": "degraded" if failed & {"financial_summary", "transaction_metrics", "anomaly_detection"} else "ok",
             "detail": "Validated input, financial metrics, transactions, anomalies"},
            {"key": "compliance", "name": "Compliance + policy cross-check", "duration_ms": ms(comp[0], comp_end) if comp else 0,
             "status": "ok" if cross["available"] else "skipped",
             "detail": "14 policy rules evaluated" + ("; policy checker compared " + str(cross["compared"]) if cross["available"]
                                                       else "; policy checker not run")},
            {"key": "credit", "name": "Credit risk (ML)", "duration_ms": ms(*credit) if credit else 0,
             "status": "ok" if engine["result"]["ml"].get("risk_score") is not None else "skipped",
             "detail": "20 model features scored"},
            {"key": "explanation", "name": "Explanation", "duration_ms": ms(*expl) if expl else 0,
             "status": "ok" if explanation.get("source", "").startswith("azure") else "template",
             "detail": "Written by Azure OpenAI" if explanation.get("source", "").startswith("azure") else "Rule-based template"},
        ]
        return steps

    @staticmethod
    def _checklist(verdict: str, rules: list[dict], cross: dict, gaps: list[dict]) -> list[dict]:
        items: list[dict] = []
        lead = {"DECLINE_RECOMMENDED": "Review the knockout rule(s) below before confirming any decline.",
                "FURTHER_REVIEW_REQUIRED": "Escalate under the referral matrix: no rule gives an automatic decline.",
                "ELIGIBLE_FOR_APPROVAL": "Run the standard pre-approval checks: identity, documents, final sign-off."}[verdict]
        items.append({"id": "lead", "text": lead, "rule": None, "priority": "high"})
        for r in sorted((r for r in rules if r["outcome"] in ("fail", "review")), key=lambda r: (r["outcome"] != "fail", not r["is_driver"])):
            items.append({"id": "act-" + r["code"], "text": ACTIONS.get(r["code"], "Review this rule."), "rule": r["code"],
                          "priority": "high" if r["outcome"] == "fail" else "normal"})
        for g in gaps:
            items.append({"id": "gap-" + g["rule"], "text": f"Obtain {', '.join(g['missing_fields'])}: rule {g['rule']} could not be evaluated.",
                          "rule": g["rule"], "priority": "normal"})
        for c in cross.get("conflicts", []):
            items.append({"id": "conf-" + c["code"], "text": f"Read the cited clause for {c['code']}: the policy checker disagreed with the rule engine.",
                          "rule": c["code"], "priority": "normal"})
        items.append({"id": "record", "text": "Record your own decision. This system only recommends; it never approves or declines.",
                      "rule": None, "priority": "normal"})
        return items

    def _clean(self, obj):
        redact = _Redactor()

        def walk(value):
            if isinstance(value, str):
                return ascii_safe(redact(value))
            if isinstance(value, dict):
                return {k: walk(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [walk(v) for v in value]
            return value

        return walk(obj)


def _timed(fn, name: str, sink: dict):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            sink[name] = (start, time.perf_counter())

    return wrapper
