"""PolicyRetriever: the single entry point the agent and backend use for policy RAG."""

from __future__ import annotations

import logging

from .chunking import Chunk, chunk_documents
from .config import RAGSettings, get_settings
from .embeddings import Embedder, get_embedder
from .loaders import load_directory
from .stores import LocalVectorStore, SearchResult, VectorStore, get_store

log = logging.getLogger(__name__)


class PolicyRetriever:
    def __init__(
        self,
        settings: RAGSettings | None = None,
        embedder: Embedder | None = None,
        store: VectorStore | None = None,
    ):
        self.settings = settings or get_settings()
        self.embedder = embedder or get_embedder(self.settings)
        self.store = store or get_store(self.settings)
        self._checked = False

    # ------------------------------------------------------------------ ingest
    def ingest(self) -> list[Chunk]:
        """Load every document in the policy folder, chunk, embed and (re)build the index."""
        docs = load_directory(self.settings.policy_dir)
        if not docs:
            raise RuntimeError(f"No supported documents (.pdf .docx .md .txt) in {self.settings.policy_dir}")
        chunks = chunk_documents(docs, self.settings.chunk_max_chars, self.settings.chunk_overlap_chars)
        log.info("Loaded %d documents -> %d chunks; embedding with %s", len(docs), len(chunks), self.embedder.name)
        vectors = self.embedder.embed([c.embed_text for c in chunks])
        self.store.index(chunks, vectors, self.embedder.name)
        self._checked = True
        return chunks

    # ------------------------------------------------------------------ search
    def _check_compatible(self) -> None:
        if self._checked:
            return
        if isinstance(self.store, LocalVectorStore):
            if self.store.vectors is None:
                self.store.load()
            if self.store.embedder_name != self.embedder.name:
                raise RuntimeError(
                    f"The index was built with '{self.store.embedder_name}' but the current embedder is "
                    f"'{self.embedder.name}'. Re-run ingest after changing RAG_EMBEDDINGS or the deployment."
                )
        self._checked = True

    def search(self, query: str, k: int | None = None, category: str | None = None) -> list[SearchResult]:
        self._check_compatible()
        qvec = self.embedder.embed([query])[0]
        return self.store.search(query, qvec, k=k or self.settings.top_k, category=category)

    def search_many(self, queries: list[str], k: int | None = None) -> list[SearchResult]:
        """Run several queries and merge results, keeping each chunk once (best score)."""
        best: dict[str, SearchResult] = {}
        for q in queries:
            for r in self.search(q, k=k):
                if r.chunk.chunk_id not in best or r.score > best[r.chunk.chunk_id].score:
                    best[r.chunk.chunk_id] = r
        return sorted(best.values(), key=lambda r: -r.score)
