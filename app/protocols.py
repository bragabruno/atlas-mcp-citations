"""Backend Protocols — corpus lookup backends implement these.

Concrete implementations (ES, Qdrant) are injected at runtime.
Tests inject fakes so no live services are required.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain import Chunk


@runtime_checkable
class ESCorpusClient(Protocol):
    """Elasticsearch corpus lookup by source_id."""

    async def lookup(self, source_id: str) -> Chunk | None:
        """Return the first matching chunk for *source_id*, or None if absent."""
        ...


@runtime_checkable
class QdrantCorpusClient(Protocol):
    """Qdrant corpus lookup by source_id payload filter."""

    async def lookup(self, source_id: str) -> Chunk | None:
        """Return the first matching chunk for *source_id*, or None if absent."""
        ...
