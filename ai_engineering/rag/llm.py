"""Minimal chat-completion wrapper that returns JSON. Swap in any object with the same method for tests."""

from __future__ import annotations

import json
import re
from typing import Protocol

from .azure_client import make_client
from .azure_errors import AzureCallError, call_azure
from .config import RAGSettings


class JSONLLM(Protocol):
    name: str

    def complete_json(self, system: str, user: str) -> dict: ...


class AzureChatLLM:
    def __init__(self, settings: RAGSettings):
        self.client = make_client(settings, "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY to use the policy checker.")
        self.deployment = settings.chat_deployment
        self.name = f"azure:{self.deployment}"

    def complete_json(self, system: str, user: str) -> dict:
        resp = call_azure(
            lambda: self.client.chat.completions.create(
                model=self.deployment,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            ),
            self.deployment,
            "chat",
        )
        try:
            return json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError as exc:
            raise AzureCallError(
                f"The chat deployment '{self.deployment}' did not return valid JSON. Use a chat model that "
                "supports JSON mode (e.g. gpt-4o or gpt-4o-mini) in AZURE_OPENAI_CHAT_DEPLOYMENT."
            ) from exc

# Added a local_llm to be able to do local testing
class LocalTestLLM:
    """Deterministic local LLM replacement used for RAG integration testing."""

    def __init__(self):
        self.name = "local-test"

    def complete_json(self, system: str, user: str) -> dict:
        # Find the first retrieved policy chunk.
        chunk_match = re.search(
            r"=== EXCERPT chunk_id:\s*(\S+)",
            user
        )

        chunk_id = chunk_match.group(1) if chunk_match else "local-test-chunk"

        # For our first integration test, use credit_score
        # if it exists in the application fields.
        if "credit_score" in user:
            return {
                "rules": [
                    {
                        "rule_id": "local_credit_score_rule",
                        "requirement": "Credit score must be at least 720.",
                        "chunk_id": chunk_id,
                        "clause": None,
                        "quote": "",
                        "field": "credit_score",
                        "operator": ">=",
                        "threshold": 720,
                        "unit": "score",
                        "severity": "requirement",
                    }
                ]
            }

        # Fallback rule if credit_score is not present.
        return {
            "rules": [
                {
                    "rule_id": "local_test_rule",
                    "requirement": "Local test policy rule.",
                    "chunk_id": chunk_id,
                    "clause": None,
                    "quote": "",
                    "field": None,
                    "operator": "qualitative",
                    "threshold": None,
                    "unit": None,
                    "severity": "requirement",
                }
            ]
        }
