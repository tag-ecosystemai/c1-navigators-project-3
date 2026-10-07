"""Analyst Q&A agent: Azure OpenAI function calling over the policy tools and the golden case reports."""

from __future__ import annotations

import json

from ..rag.azure_errors import call_azure
from ..rag.tools import POLICY_TOOL_NAMES, POLICY_TOOL_SCHEMAS, call_policy_tool
from .cases import find_case, load_cases, load_transactions, run_case
from .ml_probe import ml_status
from .view import build_view

MAX_TOOL_LOOPS = 5
MAX_TOOL_RESULT_CHARS = 12000

SYSTEM_PROMPT = (
    "You are an assistant for a bank credit analyst reviewing loan applications. Answer ONLY from the "
    "results of the tools you call: search_policies (policy text), check_policy_compliance (an "
    "application checked against policy) and get_case_report (the investigation report for a golden "
    "persona such as CUST-GOLD-001). Cite the clause or rule code (e.g. POL-DTI-001) for every claim. "
    "If the tools do not contain the answer, say you do not know instead of guessing. You never make "
    "or change the decision: the verdict in a case report comes from the rule engine and a human "
    "analyst decides. Keep answers short and factual."
)

GET_CASE_REPORT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_case_report",
        "description": (
            "Run the investigation engine on one golden persona and return its report: verdict, primary "
            "driver, every policy rule with status and the applicant's value, data gaps, financial and "
            "transaction metrics, and the top evidence. Also returns the application fields, which can be "
            "passed to check_policy_compliance."
        ),
        "parameters": {
            "type": "object",
            "properties": {"applicant_id": {"type": "string", "description": "e.g. CUST-GOLD-001"}},
            "required": ["applicant_id"],
        },
    },
}

AGENT_TOOLS = POLICY_TOOL_SCHEMAS + [GET_CASE_REPORT_SCHEMA]
AGENT_TOOL_NAMES = POLICY_TOOL_NAMES | {"get_case_report"}


def get_case_report(applicant_id: str) -> dict:
    cases = load_cases()
    case = find_case(cases, applicant_id)
    usable, reason = ml_status()
    application, result = run_case(case, load_transactions(), ml_enabled=usable)
    # banner/mode are irrelevant to the agent; expected_verdict is never included (answer key)
    view = build_view(case, application, result, banner="", azure_mode=True, ml_reason=None if usable else reason)
    cross = view["cross_check"]
    return {
        "applicant_id": view["applicant_id"],
        "verdict": view["verdict"],
        "primary_driver": view["driver"],
        "rules": view["rules"],
        "data_gaps": view["data_gaps"],
        "ml": view["ml"]["text"],
        "financial": view["financial"],
        "transactions": view["transactions"],
        "policy_cross_check": {"available": cross.get("available"), "conflicts": cross.get("conflicts", []),
                               "error": cross.get("error")},
        "top_evidence": [{k: e[k] for k in ("severity", "title", "data")} for e in view["evidence"][:10]],
        "application": application,
    }


def dispatch(name: str, arguments: dict) -> dict:
    """Run one tool. Errors are returned to the model as data so it can explain them."""
    try:
        if name == "get_case_report":
            return get_case_report(**arguments)
        if name in POLICY_TOOL_NAMES:
            return call_policy_tool(name, arguments)
        return {"error": f"unknown tool '{name}'"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def new_conversation() -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run_turn(client, deployment: str, messages: list[dict], question: str, dispatch_fn=dispatch,
             max_loops: int = MAX_TOOL_LOOPS) -> str:
    """Add the question, let the model call tools (at most `max_loops` rounds), return its answer."""
    messages.append({"role": "user", "content": question})
    for loop in range(max_loops + 1):
        extra = {"tools": AGENT_TOOLS, "tool_choice": "auto"} if loop < max_loops else {}
        response = call_azure(
            lambda: client.chat.completions.create(model=deployment, messages=messages, temperature=0, **extra),
            deployment, "chat")
        message = response.choices[0].message
        calls = getattr(message, "tool_calls", None)
        if not calls:
            answer = message.content or "I could not produce an answer."
            messages.append({"role": "assistant", "content": answer})
            return answer
        messages.append({
            "role": "assistant", "content": message.content,
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls],
        })
        for call in calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = dispatch_fn(call.function.name, arguments)
            except json.JSONDecodeError:
                result = {"error": "tool arguments were not valid JSON"}
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, default=str)[:MAX_TOOL_RESULT_CHARS]})
    return "I could not produce an answer."  # unreachable: the last loop sends no tools
