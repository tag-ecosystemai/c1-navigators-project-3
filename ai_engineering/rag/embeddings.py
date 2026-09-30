"""Embedding backends.

- AzureOpenAIEmbedder: the real one (text-embedding-3-small / -large deployment).
- HashingEmbedder: offline, deterministic, no API key. Weak semantically; only for
  unit tests and for working without Azure credentials. Keyword search (BM25) in the
  local store makes up for a lot of its weakness on policy text.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .config import RAGSettings


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


def _normalise(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (v / norms).astype(np.float32)


class AzureOpenAIEmbedder:
    def __init__(self, settings: RAGSettings, batch_size: int = 64):
        from openai import AzureOpenAI

        if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
            raise RuntimeError(
                "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY "
                "in .env, or set RAG_EMBEDDINGS=local to use the offline embedder."
            )
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.embedding_deployment
        self.batch_size = batch_size
        self.name = f"azure:{self.deployment}"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t.replace("\n", " ") for t in texts[i : i + self.batch_size]]
            resp = self.client.embeddings.create(model=self.deployment, input=batch)
            vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        return _normalise(np.array(vectors, dtype=np.float32))


class HashingEmbedder:
    """Bag of words and word pairs hashed into a fixed-size vector (scikit-learn)."""

    def __init__(self, n_features: int = 2048):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.vectorizer = HashingVectorizer(
            n_features=n_features, ngram_range=(1, 2), alternate_sign=False, norm=None, stop_words="english"
        )
        self.name = f"local-hashing:{n_features}"

    def embed(self, texts: list[str]) -> np.ndarray:
        m = self.vectorizer.transform(texts).toarray().astype(np.float32)
        m = np.log1p(m)  # damp repeated words
        return _normalise(m)


def get_embedder(settings: RAGSettings) -> Embedder:
    backend = settings.embeddings_backend.lower()
    if backend == "azure":
        return AzureOpenAIEmbedder(settings)
    if backend == "local":
        return HashingEmbedder()
    raise ValueError(f"Unknown RAG_EMBEDDINGS backend: {settings.embeddings_backend!r} (use 'azure' or 'local')")
