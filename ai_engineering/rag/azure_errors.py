"""Turn common Azure OpenAI failures into plain-English messages (never includes secrets)."""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


class AzureCallError(RuntimeError):
    """An Azure OpenAI call failed; the message says what to check."""


def explain_azure_error(exc: Exception, deployment: str, kind: str) -> str:
    """`kind` is 'embedding' or 'chat'. Matches on status code / class name so the openai
    package does not have to be importable here."""
    status = getattr(exc, "status_code", None)
    code = str(getattr(exc, "code", "") or "")
    name = type(exc).__name__
    env = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT" if kind == "embedding" else "AZURE_OPENAI_CHAT_DEPLOYMENT"

    if code == "DeploymentNotFound" or (status == 404 and "deployment" in str(exc).lower()):
        return (
            f"Azure OpenAI has no {kind} deployment named '{deployment}'. Set {env} in .env to the "
            "deployment name shown in Azure AI Foundry (the deployment name, not the model name)."
        )
    if status == 401 or name == "AuthenticationError":
        return (
            "Azure OpenAI rejected the API key (401). Check AZURE_OPENAI_API_KEY and that "
            "AZURE_OPENAI_ENDPOINT belongs to the same resource."
        )
    if status == 429 or name == "RateLimitError":
        return (
            "Azure OpenAI rate limit or quota reached (429) even after retries. Wait a minute and retry, "
            f"or raise the quota for the '{deployment}' deployment."
        )
    if name in ("APITimeoutError", "Timeout", "TimeoutException"):
        return (
            f"The Azure OpenAI {kind} request timed out. Check the network/VPN and that "
            "AZURE_OPENAI_ENDPOINT is reachable, or raise RAG_AZURE_TIMEOUT."
        )
    if name == "APIConnectionError":
        return "Could not connect to Azure OpenAI. Check AZURE_OPENAI_ENDPOINT, your network and any proxy/VPN."
    return f"Azure OpenAI {kind} call failed: {name}" + (f" (HTTP {status})" if status else "")


def call_azure(fn: Callable[[], T], deployment: str, kind: str) -> T:
    """Run an Azure call, re-raising any failure as AzureCallError with a readable message."""
    try:
        return fn()
    except AzureCallError:
        raise
    except Exception as exc:  # noqa: BLE001 - translate every SDK failure
        raise AzureCallError(explain_azure_error(exc, deployment, kind)) from exc
