"""Embedding backends.

- AzureOpenAIEmbedder: the real one (text-embedding-3-small / -large deployment).
- HashingEmbedder: offline, deterministic, no API key. Weak semantically; only for
  unit tests and for working without Azure credentials. Keyword search (BM25) in the
  local store makes up for a lot of its weakness on policy text.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .azure_client import make_client
from .azure_errors import call_azure
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
        self.client = make_client(
            settings,
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY "
            "in .env, or set RAG_EMBEDDINGS=local to use the offline embedder.",
        )
        self.deployment = settings.embedding_deployment
        self.batch_size = batch_size
        self.name = f"azure:{self.deployment}"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t.replace("\n", " ") for t in texts[i : i + self.batch_size]]
            resp = call_azure(
                lambda b=batch: self.client.embeddings.create(model=self.deployment, input=b),
                self.deployment,
                "embedding",
            )
            vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        return _normalise(np.array(vectors, dtype=np.float32))


# class HashingEmbedder:
#     """Bag of words and word pairs hashed into a fixed-size vector (scikit-learn)."""

#     def __init__(self, n_features: int = 2048):
#         from sklearn.feature_extraction.text import HashingVectorizer

#         self.vectorizer = HashingVectorizer(
#             n_features=n_features, ngram_range=(1, 2), alternate_sign=False, norm=None, stop_words="english"
#         )
#         self.name = f"local-hashing:{n_features}"

#     def embed(self, texts: list[str]) -> np.ndarray:
#         m = self.vectorizer.transform(texts).toarray().astype(np.float32)
#         m = np.log1p(m)  # damp repeated words
#         return _normalise(m)

# Modified HashingEmbedder class
class HashingEmbedder:
    """Lightweight bag-of-words and word-pair hashing embedder using only Python."""

    def __init__(self, n_features: int = 2048):
        self.n_features = n_features
        self.name = f"local-hashing:{n_features}"

    def _tokens(self, text: str) -> list[str]:
        import re

        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        # Remove common English stop words.
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for",
            "from", "in", "is", "it", "of", "on", "or", "that", "the",
            "this", "to", "was", "were", "with",
        }

        words = [word for word in words if word not in stop_words]

        # Include both individual words and adjacent word pairs.
        return words + [
            f"{words[i]} {words[i + 1]}"
            for i in range(len(words) - 1)
        ]

    def embed(self, texts: list[str]) -> np.ndarray:
        import hashlib

        matrix = np.zeros(
            (len(texts), self.n_features),
            dtype=np.float32,
        )

        for row, text in enumerate(texts):
            for token in self._tokens(text):
                digest = hashlib.md5(
                    token.encode("utf-8")
                ).digest()

                index = int.from_bytes(
                    digest[:4],
                    byteorder="little",
                ) % self.n_features

                matrix[row, index] += 1.0

        matrix = np.log1p(matrix)  # damp repeated words
        return _normalise(matrix)


def get_embedder(settings: RAGSettings) -> Embedder:
    backend = settings.embeddings_backend.lower()
    if backend == "azure":
        return AzureOpenAIEmbedder(settings)
    if backend == "local":
        return HashingEmbedder()
    raise ValueError(f"Unknown RAG_EMBEDDINGS backend: {settings.embeddings_backend!r} (use 'azure' or 'local')")
