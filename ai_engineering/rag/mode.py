"""Which mode is the system running in? Every demo/report output prints this banner."""

from __future__ import annotations

import os

from .azure_client import azure_configured
from .config import RAGSettings, get_settings

# Offline safety net: local embeddings + local test LLM, with its own index so it never collides
# with the index built by the Azure embedder. Lives under the gitignored policy_index/ folder.
OFFLINE_INDEX_SUBDIR = "offline"


def is_azure_mode(settings: RAGSettings | None = None) -> bool:
    s = settings or get_settings()
    return azure_configured(s) and s.embeddings_backend.lower() == "azure" and s.rag_llm.lower() == "azure"


def banner(settings: RAGSettings | None = None) -> str:
    s = settings or get_settings()
    if is_azure_mode(s):
        return f"Azure OpenAI: chat={s.chat_deployment}, embeddings={s.embedding_deployment}"
    return "OFFLINE MODE - no Azure"


def force_offline() -> None:
    """Switch this process to the safety-net mode (used by --offline)."""
    index_dir = get_settings().index_dir
    os.environ["RAG_EMBEDDINGS"] = "local"
    os.environ["RAG_LLM"] = "local"
    os.environ["RAG_STORE"] = "local"
    if index_dir.name != OFFLINE_INDEX_SUBDIR:
        os.environ["RAG_INDEX_DIR"] = str(index_dir / OFFLINE_INDEX_SUBDIR)
    reset_caches()


def reset_caches() -> None:
    from . import tools

    tools.get_retriever.cache_clear()
    tools.get_checker.cache_clear()
