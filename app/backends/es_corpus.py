"""Elasticsearch corpus backend.

Looks up the ``doc_chunks`` index by ``source_id`` field and returns the first
matching chunk's text, or None if the source_id is absent from the corpus.
"""

from __future__ import annotations

from elasticsearch import AsyncElasticsearch

from app.domain import Chunk

_INDEX = "doc_chunks"


class ElasticsearchCorpusClient:
    """Implements ESCorpusClient using the async Elasticsearch Python SDK."""

    def __init__(self, client: AsyncElasticsearch) -> None:
        self._client = client

    async def lookup(self, source_id: str) -> Chunk | None:
        """Return the first chunk matching *source_id* from Elasticsearch, or None."""
        response = await self._client.search(
            index=_INDEX,
            body={
                "size": 1,
                "query": {"term": {"source_id": source_id}},
            },
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        hit = hits[0]
        source = hit["_source"]
        return Chunk(
            id=hit["_id"],
            text=str(source.get("text", "")),
            source_id=str(source.get("source_id", "")),
        )
