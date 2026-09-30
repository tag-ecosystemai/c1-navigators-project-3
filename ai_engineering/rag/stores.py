"""Vector stores with hybrid (vector + keyword) search.

Hybrid search matters for policy text: users ask with abbreviations and exact terms
("DTI", "620", "self-employed") that keyword search finds reliably, while embeddings
catch paraphrases ("how much can they borrow vs salary" -> loan-to-income clause).

- LocalVectorStore: numpy + BM25, persisted to data/processed/policy_index/. No server.
- AzureSearchStore: Azure AI Search index with native hybrid search, for deployment.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .chunking import Chunk
from .config import RAGSettings


@dataclass
class SearchResult:
    chunk: Chunk
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk.chunk_id,
            "citation": self.chunk.citation,
            "text": self.chunk.text,
            "source": self.chunk.source,
            "section": self.chunk.section,
            "clauses": self.chunk.clauses,
            "page": self.chunk.page,
            "category": self.chunk.category,
            "score": round(float(self.score), 4),
        }


class VectorStore(Protocol):
    def index(self, chunks: list[Chunk], vectors: np.ndarray, embedder_name: str) -> None: ...

    def search(
        self, query: str, query_vector: np.ndarray, k: int = 5, category: str | None = None
    ) -> list[SearchResult]: ...


# --------------------------------------------------------------------------- BM25

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")
_STOP = set(
    "a an the of to in on for and or is are be by with at as it this that from any must not no "
    "what which who how when where can do does should would".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(d) for d in docs]
        self.lengths = [len(d) for d in docs]
        self.avgdl = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, (tf, dl) in enumerate(zip(self.docs, self.lengths)):
            s = 0.0
            for t in query_tokens:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out[i] = s
        return out


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return fused


# --------------------------------------------------------------------------- Local store


class LocalVectorStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.chunks: list[Chunk] = []
        self.vectors: np.ndarray | None = None
        self.embedder_name: str | None = None
        self._bm25: BM25 | None = None

    # ---- write
    def index(self, chunks: list[Chunk], vectors: np.ndarray, embedder_name: str) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        np.save(self.index_dir / "vectors.npy", vectors.astype(np.float32))
        with open(self.index_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        manifest = {"embedder": embedder_name, "dim": int(vectors.shape[1]), "count": len(chunks)}
        (self.index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.chunks, self.vectors, self.embedder_name = chunks, vectors, embedder_name
        self._bm25 = BM25([tokenize(c.embed_text) for c in chunks])

    # ---- read
    def load(self) -> "LocalVectorStore":
        manifest_path = self.index_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"No policy index at {self.index_dir}. Run: python -m ai_engineering.rag.cli ingest"
            )
        manifest = json.loads(manifest_path.read_text())
        self.embedder_name = manifest["embedder"]
        self.vectors = np.load(self.index_dir / "vectors.npy")
        with open(self.index_dir / "chunks.jsonl", encoding="utf-8") as f:
            self.chunks = [Chunk.from_dict(json.loads(line)) for line in f if line.strip()]
        self._bm25 = BM25([tokenize(c.embed_text) for c in self.chunks])
        return self

    def search(
        self, query: str, query_vector: np.ndarray, k: int = 5, category: str | None = None, candidates: int = 20
    ) -> list[SearchResult]:
        if self.vectors is None or self._bm25 is None:
            self.load()
        allowed = [i for i, c in enumerate(self.chunks) if category is None or c.category == category]
        if not allowed:
            return []
        allowed_arr = np.array(allowed)

        vec_scores = self.vectors[allowed_arr] @ query_vector.astype(np.float32).ravel()
        vec_rank = [int(allowed_arr[i]) for i in np.argsort(-vec_scores)[:candidates]]

        kw_all = self._bm25.scores(tokenize(query))
        kw_scores = kw_all[allowed_arr]
        kw_order = [i for i in np.argsort(-kw_scores)[:candidates] if kw_scores[i] > 0]
        kw_rank = [int(allowed_arr[i]) for i in kw_order]

        fused = reciprocal_rank_fusion([vec_rank, kw_rank])
        best = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [SearchResult(self.chunks[i], s) for i, s in best]


# --------------------------------------------------------------------------- Azure AI Search


class AzureSearchStore:
    """Azure AI Search index. Requires: pip install azure-search-documents"""

    VECTOR_FIELD = "content_vector"

    def __init__(self, settings: RAGSettings):
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient

        if not (settings.azure_search_endpoint and settings.azure_search_api_key):
            raise RuntimeError("Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY to use RAG_STORE=azure_search.")
        cred = AzureKeyCredential(settings.azure_search_api_key)
        self.index_name = settings.azure_search_index
        self.index_client = SearchIndexClient(settings.azure_search_endpoint, cred)
        self.search_client = SearchClient(settings.azure_search_endpoint, self.index_name, cred)

    def _create_index(self, dim: int) -> None:
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        fields = [
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="text", type=SearchFieldDataType.String),
            SearchableField(name="embed_text", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="section", type=SearchFieldDataType.String),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page", type=SearchFieldDataType.Int32),
            SimpleField(
                name="clauses", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True
            ),
            SearchField(
                name=self.VECTOR_FIELD,
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dim,
                vector_search_profile_name="policy-vector-profile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="policy-hnsw")],
            profiles=[VectorSearchProfile(name="policy-vector-profile", algorithm_configuration_name="policy-hnsw")],
        )
        # re-create from scratch so chunks from deleted/renamed documents do not linger
        if self.index_name in list(self.index_client.list_index_names()):
            self.index_client.delete_index(self.index_name)
        self.index_client.create_index(SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search))

    def index(self, chunks: list[Chunk], vectors: np.ndarray, embedder_name: str) -> None:
        self._create_index(int(vectors.shape[1]))
        docs = []
        for c, v in zip(chunks, vectors):
            d = c.to_dict()
            d["embed_text"] = c.embed_text
            d[self.VECTOR_FIELD] = v.tolist()
            docs.append(d)
        for i in range(0, len(docs), 500):
            self.search_client.upload_documents(documents=docs[i : i + 500])

    def search(
        self, query: str, query_vector: np.ndarray, k: int = 5, category: str | None = None
    ) -> list[SearchResult]:
        from azure.search.documents.models import VectorizedQuery

        vq = VectorizedQuery(vector=query_vector.ravel().tolist(), k_nearest_neighbors=max(k, 20), fields=self.VECTOR_FIELD)
        flt = f"category eq '{category}'" if category else None
        results = self.search_client.search(
            search_text=query,  # text + vector in one call = Azure's native hybrid search (RRF)
            vector_queries=[vq],
            filter=flt,
            top=k,
            select=["chunk_id", "text", "source", "title", "section", "category", "page", "clauses"],
        )
        out = []
        for r in results:
            chunk = Chunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                source=r["source"],
                title=r["title"],
                category=r["category"],
                section=r["section"],
                page=r.get("page"),
                clauses=list(r.get("clauses") or []),
            )
            out.append(SearchResult(chunk, float(r["@search.score"])))
        return out


def get_store(settings: RAGSettings) -> VectorStore:
    backend = settings.store_backend.lower()
    if backend == "local":
        return LocalVectorStore(settings.index_dir)
    if backend == "azure_search":
        return AzureSearchStore(settings)
    raise ValueError(f"Unknown RAG_STORE backend: {settings.store_backend!r} (use 'local' or 'azure_search')")
