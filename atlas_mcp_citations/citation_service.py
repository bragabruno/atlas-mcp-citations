"""CitationService — checks whether a source_id exists in the ingested corpus.

Strategy: try Elasticsearch first; fall back to Qdrant if ES returns None.
Both backends are injected so offline tests use fakes.
"""

from __future__ import annotations

from atlas_mcp_citations.domain import Chunk
from atlas_mcp_citations.protocols import ESCorpusClient, QdrantCorpusClient


class CitationService:
    """Orchestrate ES + Qdrant lookup to verify a source_id exists in the corpus."""

    def __init__(
        self,
        es: ESCorpusClient,
        qdrant: QdrantCorpusClient,
    ) -> None:
        self._es = es
        self._qdrant = qdrant

    async def verify(self, source_id: str) -> Chunk | None:
        """Return the first matching chunk for *source_id*, or None if not found.

        Queries Elasticsearch first.  If ES finds nothing, falls back to Qdrant.
        This mirrors the README contract: both backends are checked.
        """
        chunk = await self._es.lookup(source_id)
        if chunk is not None:
            return chunk
        return await self._qdrant.lookup(source_id)
