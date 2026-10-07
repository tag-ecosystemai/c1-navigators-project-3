"""Preflight for the Azure setup. One PASS / FAIL / WARN / SKIP line per check, with the fix on
failures. Never prints the API key (or the endpoint); env vars are shown as set/unset only."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .azure_client import azure_configured
from .azure_errors import AzureCallError
from .config import RAGSettings
from .mode import banner

REQUIRED = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
OPTIONAL = ["AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "AZURE_OPENAI_CHAT_DEPLOYMENT"]


@dataclass
class Check:
    status: str  # PASS | FAIL | WARN | SKIP | INFO
    name: str
    detail: str = ""
    fix: str = ""

    def line(self) -> str:
        text = f"[{self.status}] {self.name}" + (f": {self.detail}" if self.detail else "")
        return text + (f"\n       fix: {self.fix}" if self.status == "FAIL" and self.fix else "")


def _msg(exc: Exception) -> str:
    """Our own error types carry a plain-English message; anything else is shown by type only."""
    return str(exc) if isinstance(exc, (RuntimeError, AzureCallError)) else type(exc).__name__


def run_checks(settings: RAGSettings, allow_offline: bool = False) -> list[Check]:
    checks: list[Check] = []
    add = lambda *a, **k: checks.append(Check(*a, **k))  # noqa: E731
    offline_note = "offline safety-net mode"

    # --- environment
    required = REQUIRED + (["AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY"] if settings.store_backend.lower() == "azure_search" else [])
    for name in required:
        is_set = bool(os.getenv(name))
        add("PASS" if is_set else "FAIL", f"env {name}", "set" if is_set else "unset",
            f"add {name}=... to .env in the repo root (see docs/AZURE_SETUP.md)")
    for name in OPTIONAL:
        add("INFO", f"env {name}", "set" if os.getenv(name) else "unset (default used)")
    endpoint = settings.azure_openai_endpoint or ""
    if "<" in endpoint:
        add("FAIL", "endpoint format", "AZURE_OPENAI_ENDPOINT is still the placeholder from .env.example",
            "replace it with the endpoint from the Azure portal (https://<your-resource>.openai.azure.com/)")
    elif endpoint and not (endpoint.startswith("https://") and "/openai/" not in endpoint and "?" not in endpoint):
        add("FAIL", "endpoint format", "AZURE_OPENAI_ENDPOINT should be only https://<resource>.openai.azure.com/",
            "remove any path such as /openai/deployments/... or ?api-version=... from the endpoint")
    add("INFO", "deployments in use",
        f"chat={settings.chat_deployment}, embeddings={settings.embedding_deployment}, api-version={settings.azure_openai_api_version}")

    # --- which backends are selected
    for var, value in (("RAG_EMBEDDINGS", settings.embeddings_backend), ("RAG_LLM", settings.rag_llm)):
        if value.lower() == "azure":
            add("PASS", f"{var}", "azure")
        elif allow_offline:
            add("SKIP", f"{var}", f"{value} ({offline_note})")
        else:
            add("FAIL", f"{var}", f"{value}: the system would run offline, not on Azure",
                f"set {var}=azure in .env (or pass --allow-offline for the safety net)")

    azure_ready = azure_configured(settings)

    # --- embeddings deployment returns a vector
    if settings.embeddings_backend.lower() != "azure":
        add("SKIP", "embeddings deployment", offline_note)
    elif not azure_ready:
        add("SKIP", "embeddings deployment", "Azure is not configured")
    else:
        try:
            from .embeddings import AzureOpenAIEmbedder

            vec = AzureOpenAIEmbedder(settings).embed(["ping"])
            if vec.ndim != 2 or vec.shape[1] == 0:
                raise RuntimeError("the deployment returned an empty vector")
            add("PASS", "embeddings deployment", f"{settings.embedding_deployment} returned a {vec.shape[1]}-dimension vector")
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "embeddings deployment", _msg(exc),
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT must be the name of an embeddings deployment (e.g. text-embedding-3-small)")

    # --- chat deployment answers a JSON-mode request
    if settings.rag_llm.lower() != "azure":
        add("SKIP", "chat deployment", offline_note)
    elif not azure_ready:
        add("SKIP", "chat deployment", "Azure is not configured")
    else:
        try:
            from .llm import AzureChatLLM

            reply = AzureChatLLM(settings).complete_json("Reply with a JSON object.", '{"ping": true}')
            if not isinstance(reply, dict):
                raise RuntimeError("the deployment did not answer with a JSON object")
            add("PASS", "chat deployment", f"{settings.chat_deployment} answered a JSON-mode request")
        except Exception as exc:  # noqa: BLE001
            add("FAIL", "chat deployment", _msg(exc),
                "AZURE_OPENAI_CHAT_DEPLOYMENT must be a chat deployment that supports JSON mode (e.g. gpt-4o-mini)")

    # --- the index exists and was built with the Azure embedder
    if settings.store_backend.lower() != "local":
        add("SKIP", "policy index", f"RAG_STORE={settings.store_backend} is not probed")
    else:
        manifest = settings.index_dir / "manifest.json"
        wanted = f"azure:{settings.embedding_deployment}" if settings.embeddings_backend.lower() == "azure" else None
        if not manifest.exists():
            add("WARN", "policy index", f"none at {settings.index_dir}; it is built automatically on first use "
                f"(or run: python -m ai_engineering.rag.cli ingest)")
        else:
            try:
                built_with = json.loads(manifest.read_text()).get("embedder", "?")
            except (OSError, ValueError):
                built_with = "?"
            if wanted is None or built_with == wanted:
                add("PASS", "policy index", f"built with {built_with}")
            else:
                add("FAIL", "policy index", f"built with '{built_with}' but the current embedder is '{wanted}'",
                    "rebuild it: python -m ai_engineering.rag.cli ingest")
    return checks


def ok(checks: list[Check]) -> bool:
    return not any(c.status == "FAIL" for c in checks)


def format_checks(settings: RAGSettings, checks: list[Check]) -> str:
    lines = [f"Mode: {banner(settings)}", ""] + [c.line() for c in checks]
    failed = sum(c.status == "FAIL" for c in checks)
    lines += ["", "All checks passed." if not failed else f"{failed} check(s) failed."]
    return "\n".join(lines)
