"""Qdrant corpus backend.

Filters the ``doc_chunks`` collection by ``source_id`` payload field and
returns the first matching chunk's text, or None if absent.

Payload schema (atlas-docs/03 §3.1):
  source_id: string
  doc_id:    string
  chunk_idx: integer
  text:      string
"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, Record

from atlas_mcp_citations.domain import Chunk

_COLLECTION = "doc_chunks"


class QdrantCorpusClient:
    """Implements QdrantCorpusClient using the async Qdrant Python SDK."""

    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    async def lookup(self, source_id: str) -> Chunk | None:
        """Return the first chunk with payload ``source_id`` matching, or None."""
        points: list[Record]
        points, _ = await self._client.scroll(
            collection_name=_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id),
                    )
                ]
            ),
            limit=1,
            with_payload=True,
        )
        if not points:
            return None
        point: Record = points[0]
        payload: dict[str, object] = point.payload or {}
        return Chunk(
            id=str(point.id),
            text=str(payload.get("text", "")),
            source_id=str(payload.get("source_id", "")),
        )
