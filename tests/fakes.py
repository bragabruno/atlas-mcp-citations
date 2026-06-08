"""In-process fake backends for offline testing.

No live Elasticsearch or Qdrant required.
"""

from __future__ import annotations

from atlas_mcp_citations.domain import Chunk


class FakeESCorpusClient:
    """Returns a configurable chunk or None for any source_id lookup."""

    def __init__(self, corpus: dict[str, Chunk]) -> None:
        self._corpus = corpus

    async def lookup(self, source_id: str) -> Chunk | None:
        return self._corpus.get(source_id)


class FakeQdrantCorpusClient:
    """Returns a configurable chunk or None for any source_id lookup."""

    def __init__(self, corpus: dict[str, Chunk]) -> None:
        self._corpus = corpus

    async def lookup(self, source_id: str) -> Chunk | None:
        return self._corpus.get(source_id)
