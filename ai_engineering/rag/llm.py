"""Minimal chat-completion wrapper that returns JSON. Swap in any object with the same method for tests."""

from __future__ import annotations

import json
import re
from typing import Protocol

from .azure_errors import call_azure
from .config import RAGSettings


class JSONLLM(Protocol):
    name: str

    def complete_json(self, system: str, user: str) -> dict: ...


class AzureChatLLM:
    def __init__(self, settings: RAGSettings):
        from openai import AzureOpenAI

        if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
            raise RuntimeError("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY to use the policy checker.")
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            timeout=settings.azure_timeout,
            max_retries=2,
        )
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
        return json.loads(resp.choices[0].message.content or "{}")

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
