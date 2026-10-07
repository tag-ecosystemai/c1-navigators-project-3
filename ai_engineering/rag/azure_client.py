"""The one place an Azure OpenAI client is built. Every LLM use (RAG embeddings, RAG rule
extraction, the explanation writer, the analyst agent) goes through here, so the five
AZURE_OPENAI_* variables in .env.example are the single source of truth."""

from __future__ import annotations

from .config import RAGSettings

DEFAULT_HINT = "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env (see docs/AZURE_SETUP.md)."


def azure_configured(settings: RAGSettings) -> bool:
    return bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)


def make_client(settings: RAGSettings, hint: str = DEFAULT_HINT):
    """AzureOpenAI client with a request timeout and 2 retries. Raises RuntimeError (never prints
    the key) if Azure is not configured."""
    if not azure_configured(settings):
        raise RuntimeError(hint)
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        timeout=settings.azure_timeout,
        max_retries=2,
    )
