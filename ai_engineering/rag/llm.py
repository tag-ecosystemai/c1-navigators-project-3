"""Minimal chat-completion wrapper that returns JSON. Swap in any object with the same method for tests."""

from __future__ import annotations

import json
from typing import Protocol

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
        )
        self.deployment = settings.chat_deployment
        self.name = f"azure:{self.deployment}"

    def complete_json(self, system: str, user: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.deployment,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return json.loads(resp.choices[0].message.content or "{}")
