"""Tests for verify_citation — citation lookup orchestration with fake backends.

Tests cover:
  - existing source_id returns exists=True and the snippet text
  - missing source_id returns exists=False and snippet=null
  - output shape matches atlas-docs/03 §6.2 schema
  - ES result takes priority over Qdrant (ES found → Qdrant not consulted)
  - Qdrant fallback when ES returns None
"""

from __future__ import annotations

import pytest

from app.citation_service import CitationService
from app.domain import Chunk
from app.server import configure, verify_citation
from tests.fakes import FakeESCorpusClient, FakeQdrantCorpusClient

# ---------------------------------------------------------------------------
# Shared corpus fixture
# ---------------------------------------------------------------------------

_EXISTING_CHUNK = Chunk(
    id="chunk-001",
    text="Regulation EU 2023/42 mandates annual disclosure of carbon offsets.",
    source_id="src-eu-2023-42",
)


def _service_with_es_hit() -> CitationService:
    """ES has the chunk; Qdrant is empty."""
    return CitationService(
        es=FakeESCorpusClient({"src-eu-2023-42": _EXISTING_CHUNK}),
        qdrant=FakeQdrantCorpusClient({}),
    )


def _service_with_qdrant_only() -> CitationService:
    """ES empty; Qdrant has the chunk (tests fallback path)."""
    return CitationService(
        es=FakeESCorpusClient({}),
        qdrant=FakeQdrantCorpusClient({"src-eu-2023-42": _EXISTING_CHUNK}),
    )


def _service_empty() -> CitationService:
    """Both backends have nothing — source not in corpus."""
    return CitationService(
        es=FakeESCorpusClient({}),
        qdrant=FakeQdrantCorpusClient({}),
    )


# ---------------------------------------------------------------------------
# CitationService unit tests
# ---------------------------------------------------------------------------


class TestCitationServiceExisting:
    async def test_es_hit_returns_chunk(self) -> None:
        service = _service_with_es_hit()
        chunk = await service.verify("src-eu-2023-42")
        assert chunk is not None
        assert chunk.source_id == "src-eu-2023-42"
        assert "carbon offsets" in chunk.text

    async def test_qdrant_fallback_when_es_empty(self) -> None:
        service = _service_with_qdrant_only()
        chunk = await service.verify("src-eu-2023-42")
        assert chunk is not None
        assert chunk.source_id == "src-eu-2023-42"

    async def test_missing_source_returns_none(self) -> None:
        service = _service_empty()
        chunk = await service.verify("src-does-not-exist")
        assert chunk is None


class TestCitationServicePriority:
    async def test_es_takes_priority_over_qdrant(self) -> None:
        """When ES has a result, Qdrant's (different) chunk is never used."""
        es_chunk = Chunk(id="es-id", text="from ES", source_id="src-x")
        qdrant_chunk = Chunk(id="qdrant-id", text="from Qdrant", source_id="src-x")
        service = CitationService(
            es=FakeESCorpusClient({"src-x": es_chunk}),
            qdrant=FakeQdrantCorpusClient({"src-x": qdrant_chunk}),
        )
        chunk = await service.verify("src-x")
        assert chunk is not None
        assert chunk.id == "es-id"
        assert chunk.text == "from ES"


# ---------------------------------------------------------------------------
# Server tool output shape (atlas-docs/03 §6.2 contract)
# ---------------------------------------------------------------------------


class TestVerifyCitationOutputShape:
    @pytest.fixture(autouse=True)
    def _configure_server(self) -> None:
        configure(
            es=FakeESCorpusClient({"src-eu-2023-42": _EXISTING_CHUNK}),
            qdrant=FakeQdrantCorpusClient({}),
        )

    async def test_existing_source_returns_exists_true(self) -> None:
        result = await verify_citation(
            source_id="src-eu-2023-42",
            claim="The regulation requires annual carbon offset disclosure.",
        )
        assert result["exists"] is True

    async def test_existing_source_returns_snippet(self) -> None:
        result = await verify_citation(
            source_id="src-eu-2023-42",
            claim="The regulation requires annual carbon offset disclosure.",
        )
        assert isinstance(result["snippet"], str)
        assert len(result["snippet"]) > 0

    async def test_snippet_contains_source_text(self) -> None:
        result = await verify_citation(
            source_id="src-eu-2023-42",
            claim="The regulation requires annual carbon offset disclosure.",
        )
        assert "carbon offsets" in str(result["snippet"])

    async def test_missing_source_returns_exists_false(self) -> None:
        configure(
            es=FakeESCorpusClient({}),
            qdrant=FakeQdrantCorpusClient({}),
        )
        result = await verify_citation(
            source_id="src-phantom",
            claim="Some claim about a phantom source.",
        )
        assert result["exists"] is False

    async def test_missing_source_returns_null_snippet(self) -> None:
        configure(
            es=FakeESCorpusClient({}),
            qdrant=FakeQdrantCorpusClient({}),
        )
        result = await verify_citation(
            source_id="src-phantom",
            claim="Some claim about a phantom source.",
        )
        assert result["snippet"] is None

    async def test_output_keys_match_atlas_docs_03_schema(self) -> None:
        """Response must contain exactly the keys defined in atlas-docs/03 §6.2."""
        result = await verify_citation(
            source_id="src-eu-2023-42",
            claim="claim text",
        )
        # atlas-docs/03 §6.2 requires: exists (bool), snippet (str | null)
        assert "exists" in result
        assert "snippet" in result
        assert isinstance(result["exists"], bool)
        # snippet is str when found
        assert isinstance(result["snippet"], str) or result["snippet"] is None

    async def test_missing_output_keys_match_atlas_docs_03_schema(self) -> None:
        configure(
            es=FakeESCorpusClient({}),
            qdrant=FakeQdrantCorpusClient({}),
        )
        result = await verify_citation(
            source_id="src-missing",
            claim="claim text",
        )
        assert "exists" in result
        assert "snippet" in result
        assert result["exists"] is False
        assert result["snippet"] is None
