"""AzureSearchStore against a mock of the azure-search-documents SDK (no network, optional backend)."""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from ai_engineering.rag.chunking import Chunk
from ai_engineering.rag.config import get_settings
from ai_engineering.rag.doctor import run_checks
from ai_engineering.rag.stores import AzureSearchStore, get_store


class _Record:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeIndexClient:
    existing = ["credit-policies"]
    deleted, created = [], []

    def __init__(self, endpoint, cred):
        self.endpoint = endpoint

    def list_index_names(self):
        return iter(FakeIndexClient.existing)

    def delete_index(self, name):
        FakeIndexClient.deleted.append(name)

    def create_index(self, index):
        FakeIndexClient.created.append(index)


class FakeSearchClient:
    uploads: list = []
    last_search: dict = {}
    rows: list = []

    def __init__(self, endpoint, index_name, cred):
        self.index_name = index_name

    def upload_documents(self, documents):
        FakeSearchClient.uploads.append(documents)

    def search(self, **kwargs):
        FakeSearchClient.last_search = kwargs
        return iter(FakeSearchClient.rows)


class _DataType:
    String, Int32, Single = "String", "Int32", "Single"

    @staticmethod
    def Collection(inner):  # noqa: N802 - mirrors the SDK
        return f"Collection({inner})"


@pytest.fixture
def fake_sdk(monkeypatch):
    FakeIndexClient.existing, FakeIndexClient.deleted, FakeIndexClient.created = ["credit-policies"], [], []
    FakeSearchClient.uploads, FakeSearchClient.last_search = [], {}
    modules = {
        "azure": types.ModuleType("azure"),
        "azure.core": types.ModuleType("azure.core"),
        "azure.core.credentials": types.ModuleType("azure.core.credentials"),
        "azure.search": types.ModuleType("azure.search"),
        "azure.search.documents": types.ModuleType("azure.search.documents"),
        "azure.search.documents.indexes": types.ModuleType("azure.search.documents.indexes"),
        "azure.search.documents.indexes.models": types.ModuleType("azure.search.documents.indexes.models"),
        "azure.search.documents.models": types.ModuleType("azure.search.documents.models"),
    }
    modules["azure.core.credentials"].AzureKeyCredential = lambda key: ("cred", key)
    modules["azure.search.documents"].SearchClient = FakeSearchClient
    modules["azure.search.documents.indexes"].SearchIndexClient = FakeIndexClient
    models = modules["azure.search.documents.indexes.models"]
    for name in ("HnswAlgorithmConfiguration", "SearchableField", "SearchField", "SimpleField", "SearchIndex",
                 "VectorSearch", "VectorSearchProfile"):
        setattr(models, name, lambda _n=name, **kw: _Record(kind=_n, **kw))
    models.SearchFieldDataType = _DataType
    modules["azure.search.documents.models"].VectorizedQuery = lambda **kw: _Record(**kw)
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake-search.search.windows.net")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "fake-search-key")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "credit-policies")
    monkeypatch.setenv("RAG_STORE", "azure_search")


def _chunks(n):
    return [Chunk(chunk_id=f"c{i}", text=f"text {i}", source="02.md", title="Policy 02", category="internal",
                  section="2 DTI", page=None, clauses=["POL-DTI-001"]) for i in range(n)]


def test_get_store_returns_azure_search_store(fake_sdk):
    assert isinstance(get_store(get_settings()), AzureSearchStore)


def test_missing_search_settings_give_a_clear_error(fake_sdk, monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_API_KEY")
    with pytest.raises(RuntimeError, match="AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY"):
        get_store(get_settings())


def test_index_recreates_index_and_uploads_in_batches(fake_sdk):
    store = get_store(get_settings())
    n = 1001
    store.index(_chunks(n), np.ones((n, 4), dtype=np.float32), "azure:demo-embed")
    assert FakeIndexClient.deleted == ["credit-policies"]  # re-created from scratch
    created = FakeIndexClient.created[0]
    assert created.name == "credit-policies"
    vector_field = next(f for f in created.fields if f.name == "content_vector")
    assert vector_field.vector_search_dimensions == 4
    assert [len(batch) for batch in FakeSearchClient.uploads] == [500, 500, 1]
    doc = FakeSearchClient.uploads[0][0]
    assert doc["chunk_id"] == "c0" and doc["clauses"] == ["POL-DTI-001"] and doc["content_vector"] == [1.0] * 4
    assert doc["embed_text"].startswith("Policy 02 > 2 DTI")


def test_search_is_hybrid_and_maps_results(fake_sdk):
    FakeSearchClient.rows = [{"chunk_id": "c1", "text": "DTI text", "source": "02.md", "title": "Policy 02",
                              "section": "2 DTI", "category": "internal", "page": None, "clauses": ["POL-DTI-001"],
                              "@search.score": 1.5}]
    store = get_store(get_settings())
    results = store.search("max DTI", np.array([0.1, 0.2], dtype=np.float32), k=3, category="internal")
    sent = FakeSearchClient.last_search
    assert sent["search_text"] == "max DTI" and sent["top"] == 3  # text + vector in one call = hybrid
    assert sent["filter"] == "category eq 'internal'"
    assert sent["vector_queries"][0].fields == "content_vector"
    assert results[0].chunk.clauses == ["POL-DTI-001"] and results[0].score == 1.5
    assert results[0].chunk.citation.startswith("Policy 02")


def test_doctor_requires_search_settings_when_enabled(fake_sdk, monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_API_KEY")
    names = {c.name: c for c in run_checks(get_settings(), allow_offline=True)}
    assert names["env AZURE_SEARCH_API_KEY"].status == "FAIL"
    assert names["policy index"].status == "SKIP"
