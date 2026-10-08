"""Golden personas: load them, hide the answer key from the engine, run investigate()."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "data" / "test_cases" / "golden_demo_cases.json"
TRANSACTIONS_PATH = ROOT / "data" / "processed" / "transactions.json"
# Answer-key fields: must never reach the engine, the RAG prompt or the explanation writer.
LABEL_FIELDS = {"expected_verdict", "persona_type", "notes"}


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def load_transactions() -> list[dict]:
    return json.loads(TRANSACTIONS_PATH.read_text(encoding="utf-8"))


def find_case(cases: list[dict], key: str) -> dict:
    """Match by applicant_id (CUST-GOLD-001) or persona_type, case-insensitive."""
    wanted = key.strip().lower()
    for case in cases:
        if wanted in (case["applicant_id"].lower(), case.get("persona_type", "").lower()):
            return case
    ids = ", ".join(c["applicant_id"] for c in cases)
    raise KeyError(f"No golden persona '{key}'. Available: {ids}")


def application_of(case: dict) -> dict:
    return {k: v for k, v in case.items() if k not in LABEL_FIELDS}


def case_payload(case: dict, transactions: list[dict], ml_enabled: bool = False) -> tuple[dict, dict]:
    """(application, engine input). The answer key is stripped first."""
    application = application_of(case)
    txns = [t for t in transactions if t.get("applicant_id") == case["applicant_id"]]
    payload = {"application": application, "transactions": txns}
    if ml_enabled:
        payload["ml"] = {"enabled": True}
    return application, payload


def run_case(case: dict, transactions: list[dict], ml_enabled: bool = False) -> tuple[dict, dict]:
    """Return (application, investigate() result)."""
    from ..orchestrator.orchestrator import investigate

    application, payload = case_payload(case, transactions, ml_enabled)
    return application, investigate(payload)


def run_case_agents(case: dict, transactions: list[dict], ml_enabled: bool = False, llm_client=None) -> tuple[dict, dict]:
    """Same as run_case, but through OrchestratorAgent (data, compliance, credit risk, explanation agents).
    The result has investigate()'s shape plus "explanation" and "explanation_detail"."""
    from ..orchestrator.agents import OrchestratorAgent

    application, payload = case_payload(case, transactions, ml_enabled)
    return application, OrchestratorAgent(llm_client=llm_client).run(payload)
