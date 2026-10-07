"""Cross-check the rule-based policy evaluator against the policy RAG checker.

The evaluator (ai_engineering/policy_engine/policy_evaluator.py) is the primary,
deterministic check: it returns {"POL-DTI-001": "FLAG_FOR_REVIEW", ...}.
The RAG checker reads the policy text itself and returns results with citations.

This module lines the two up by rule code (POL-XXX-NNN) and reports, per rule:
  - whether they agree,
  - the policy clause and quote behind the RAG result (the "cited explanation").

It never changes the evaluator's verdict. A disagreement is surfaced for the analyst
instead of silently picking a winner. If the RAG side is unavailable (no Azure key,
network error), the result says so and the evaluator's output stands on its own.
"""

from __future__ import annotations

import re
from typing import Any, Callable

_RULE_CODE = re.compile(r"POL-[A-Z]{2,4}-\d{2,4}")

# Common outcome scale used to compare the two checkers.
PASS, REVIEW, FAIL, MISSING = "pass", "review", "fail", "missing"
_RANK = {PASS: 0, MISSING: 1, REVIEW: 2, FAIL: 3}  # higher = worse

# Evaluator vocabulary -> common outcome. Values not listed (e.g. "Tier 1" for
# POL-SCR-001) are informational labels and are skipped, not compared.
EVALUATOR_OUTCOME = {
    "SATISFIED": PASS,
    "CLEAN": PASS,
    "CONDITIONAL": REVIEW,
    "FLAG_FOR_REVIEW": REVIEW,
    "REVIEW_REQUIRED": REVIEW,
    "CAUTION": REVIEW,
    "VULNERABLE": REVIEW,
    "CRITICAL_DISTRESS": REVIEW,
    "NOT_SATISFIED": FAIL,
    "KNOCKOUT": FAIL,
    "HIGH_RISK": FAIL,
    "MISSING_DATA": MISSING,
}


def rag_outcome(status: str, severity: str) -> str:
    """Map one RAG rule result onto the common scale.

    A failed 'requirement' is a hard fail. A failed 'referral' or 'risk_indicator'
    rule is a policy tier that sends the case to review rather than declining it.
    """
    if status == "satisfied":
        return PASS
    if status == "missing":
        return MISSING
    if status == "unclear":
        return REVIEW
    return FAIL if severity == "requirement" else REVIEW


def _code_of(result: dict) -> str | None:
    for key in ("clause", "rule_id", "citation"):
        m = _RULE_CODE.search((result.get(key) or "").upper())
        if m:
            return m.group(0)
    return None


def _worst_by_code(rag_results: list[dict]) -> dict[str, dict]:
    """Group RAG results by rule code, keeping the worst one (and its citation)."""
    worst: dict[str, dict] = {}
    for r in rag_results:
        code = _code_of(r)
        if code is None:
            continue
        outcome = rag_outcome(r.get("status", ""), r.get("severity", "requirement"))
        if code not in worst or _RANK[outcome] > _RANK[worst[code]["outcome"]]:
            worst[code] = {"outcome": outcome, "result": r}
    return worst


def _agreement(evaluator: str, rag: str) -> str:
    if evaluator == rag:
        return "agree"
    if rag == MISSING:
        return "evaluator_only"  # RAG had no data for this rule; evaluator stands alone
    if evaluator == MISSING:
        return "rag_only"
    if {evaluator, rag} == {PASS, FAIL}:
        return "hard_conflict"
    return "soft_conflict"


def compare(evaluator_flags: dict[str, Any], rag_result: dict) -> dict:
    """Line up evaluator flags and a RAG result (as returned by check_policy_compliance)."""
    rag_by_code = _worst_by_code(rag_result.get("results", []))
    rules: dict[str, dict] = {}

    for code, raw in evaluator_flags.items():
        ev_outcome = EVALUATOR_OUTCOME.get(str(raw))
        entry: dict[str, Any] = {"evaluator": raw, "evaluator_outcome": ev_outcome}
        rag = rag_by_code.get(code)
        if ev_outcome is None:
            entry["agreement"] = "not_compared"  # informational value, e.g. a credit tier
        elif rag is None:
            entry["agreement"] = "evaluator_only"  # RAG returned nothing for this code
            entry["rag_outcome"] = None
        else:
            r = rag["result"]
            entry.update(
                rag_outcome=rag["outcome"],
                agreement=_agreement(ev_outcome, rag["outcome"]),
                citation=r.get("citation"),
                clause=r.get("clause"),
                quote=r.get("quote"),
                explanation=r.get("explanation"),
                quote_verified=r.get("quote_verified"),
            )
        rules[code] = entry

    conflicts = [c for c, e in rules.items() if e["agreement"] in ("soft_conflict", "hard_conflict")]
    summary: dict[str, int] = {}
    for e in rules.values():
        summary[e["agreement"]] = summary.get(e["agreement"], 0) + 1

    return {
        "available": True,
        "error": None,
        "rules": rules,
        "conflicts": conflicts,
        "summary": summary,
        "needs_review": bool(conflicts),
    }


def run_cross_check(
    application: dict,
    evaluator_flags: dict[str, Any],
    check_fn: Callable[[dict], dict] | None = None,
) -> dict:
    """Run the RAG checker on `application` and compare it with `evaluator_flags`.

    `application` should be the application fields PLUS the computed values
    (financial and transaction metrics), so the RAG checker can test rules such as
    net disposable income. Any failure on the RAG side is caught and reported as
    available=False, so the main pipeline keeps working without it.
    """
    try:
        if check_fn is None:
            from .tools import check_policy_compliance as check_fn  # lazy: needs Azure config
        return compare(evaluator_flags, check_fn(application))
    except Exception as exc:  # noqa: BLE001 - the RAG layer must never break the main engine
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "rules": {},
            "conflicts": [],
            "summary": {},
            "needs_review": False,
        }
