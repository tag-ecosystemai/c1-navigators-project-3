"""Agent-facing tools for policy RAG, with OpenAI / Azure OpenAI function-calling schemas.

Usage in the agent:

    from ai_engineering.rag.tools import POLICY_TOOL_SCHEMAS, call_policy_tool
    tools = POLICY_TOOL_SCHEMAS + other_tools
    ...
    if tool_call.function.name in POLICY_TOOL_NAMES:
        result = call_policy_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
"""

from __future__ import annotations

import logging
from functools import lru_cache

from .config import get_settings
from .llm import AzureChatLLM, LocalTestLLM
from .policy_checker import PolicyChecker
from .retriever import PolicyRetriever

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_retriever() -> PolicyRetriever:
    retriever = PolicyRetriever(get_settings())
    if not retriever.index_exists():
        # The index is gitignored, so a fresh clone has none: build it on first use.
        log.warning("No policy index at %s; building it now from %s", retriever.settings.index_dir,
                    retriever.settings.policy_dir)
        chunks = retriever.ingest()
        log.warning("Policy index built automatically: %d chunks with %s", len(chunks), retriever.embedder.name)
    return retriever


# @lru_cache(maxsize=1)
# def get_checker() -> PolicyChecker:
#     retriever = get_retriever()
#     return PolicyChecker(retriever, AzureChatLLM(retriever.settings))
@lru_cache(maxsize=1)
def get_checker() -> PolicyChecker:

    retriever = get_retriever()

    if retriever.settings.rag_llm == "local":
        llm = LocalTestLLM()
    else:
        llm = AzureChatLLM(retriever.settings)

    return PolicyChecker(retriever, llm)


def search_policies(query: str, k: int = 5, category: str | None = None) -> dict:
    """Return the policy/regulation passages most relevant to a question, with citations."""
    results = get_retriever().search(query, k=k, category=category)
    return {"query": query, "results": [r.to_dict() for r in results]}


def check_policy_compliance(application: dict) -> dict:
    """Compare application facts (and computed ratios) against lending policy requirements."""
    return get_checker().check(application).to_dict()


POLICY_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": (
                "Search the bank's lending policies and regulatory documents. Use it to find the rule "
                "that applies to a question (e.g. maximum debt-to-income, required documents, red flags). "
                "Always cite the returned 'citation' when you use a passage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A specific question or topic"},
                    "k": {"type": "integer", "description": "Number of passages to return", "default": 5},
                    "category": {
                        "type": "string",
                        "description": "Optional sub-folder of data/policies to search, e.g. 'internal' or 'regulation'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_policy_compliance",
            "description": (
                "Check an application against every applicable lending policy requirement. Returns each "
                "requirement with status satisfied / not_satisfied / unclear / missing, the applicant's value, "
                "and the policy clause it comes from. Pass application fields and any computed ratios "
                "(e.g. debt_to_income as a fraction)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "object",
                        "description": "Flat JSON of application facts and computed financial indicators",
                        "additionalProperties": True,
                    }
                },
                "required": ["application"],
            },
        },
    },
]

POLICY_TOOL_NAMES = {"search_policies", "check_policy_compliance"}

_DISPATCH = {"search_policies": search_policies, "check_policy_compliance": check_policy_compliance}


def call_policy_tool(name: str, arguments: dict) -> dict:
    return _DISPATCH[name](**arguments)
