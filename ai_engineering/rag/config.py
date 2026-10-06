"""Settings for the policy RAG pipeline, read from environment variables (.env supported)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional: load a .env file from the repo root if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:  # pragma: no cover
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]


def _path(env_name: str, default: str) -> Path:
    raw = os.getenv(env_name, default)
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


@dataclass
class RAGSettings:
    # Where the policy documents live and where the local index is written
    policy_dir: Path = field(default_factory=lambda: _path("RAG_POLICY_DIR", "data/policies"))
    index_dir: Path = field(default_factory=lambda: _path("RAG_INDEX_DIR", "data/processed/policy_index"))

    # "azure" (Azure OpenAI embeddings) or "local" (offline hashing embedder, for dev/tests only)
    embeddings_backend: str = field(default_factory=lambda: os.getenv("RAG_EMBEDDINGS", "azure"))
    # "local" (numpy + BM25 on disk) or "azure_search" (Azure AI Search)
    store_backend: str = field(default_factory=lambda: os.getenv("RAG_STORE", "local"))
    # "azure" (Azure OpenAI chat) or "local" (deterministic test LLM)
    rag_llm: str = field(default_factory=lambda: os.getenv("RAG_LLM", "azure"))

    # Chunking
    chunk_max_chars: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_MAX_CHARS", "1200")))
    chunk_overlap_chars: int = field(default_factory=lambda: int(os.getenv("RAG_CHUNK_OVERLAP_CHARS", "150")))

    # Retrieval
    top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "5")))

    # Azure OpenAI
    azure_openai_endpoint: str | None = field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT"))
    azure_openai_api_key: str | None = field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY"))
    azure_openai_api_version: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )
    embedding_deployment: str = field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    )
    chat_deployment: str = field(default_factory=lambda: os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"))

    # Azure AI Search
    azure_search_endpoint: str | None = field(default_factory=lambda: os.getenv("AZURE_SEARCH_ENDPOINT"))
    azure_search_api_key: str | None = field(default_factory=lambda: os.getenv("AZURE_SEARCH_API_KEY"))
    azure_search_index: str = field(default_factory=lambda: os.getenv("AZURE_SEARCH_INDEX", "credit-policies"))


def get_settings() -> RAGSettings:
    return RAGSettings()
