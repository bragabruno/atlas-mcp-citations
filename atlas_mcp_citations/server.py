"""Atlas MCP citations server.

Exposes the ``verify_citation`` tool via FastMCP / Streamable HTTP.
Backend clients (ES, Qdrant) are injected via the ``_service`` module-level
singleton so the server can be used in tests with fake backends without
touching live services.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from atlas_mcp_citations.citation_service import CitationService
from atlas_mcp_citations.protocols import ESCorpusClient, QdrantCorpusClient

# Bind host/port from the env. FastMCP's own FASTMCP_HOST env var is not honored
# in this SDK version (its default kwarg overrides it), so read it explicitly and
# pass as a constructor kwarg (highest precedence). Default stays loopback for
# bare local runs; the container image sets FASTMCP_HOST=0.0.0.0 so the published
# port is reachable across the container boundary.
mcp: FastMCP = FastMCP(
    "atlas-mcp-citations",
    instructions="Verify that a source_id exists in the Atlas ingested corpus.",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
)

# Module-level service — replaced by configure() before the server starts.
_service: CitationService | None = None


def configure(
    es: ESCorpusClient,
    qdrant: QdrantCorpusClient,
) -> None:
    """Wire the backend clients into the module-level CitationService.

    Call this once at startup before running the server (or in test fixtures).
    """
    global _service
    _service = CitationService(es=es, qdrant=qdrant)


def _get_service() -> CitationService:
    if _service is None:
        raise RuntimeError("Server not configured — call configure() before serving.")
    return _service


@mcp.tool()
async def verify_citation(source_id: str, claim: str) -> dict[str, object]:
    """Verify that a source_id exists in the Atlas ingested corpus.

    Checks the corpus via Elasticsearch and Qdrant (payload filter on
    source_id).  Returns the first matching chunk's text as ``snippet``.

    Args:
        source_id: The source identifier to verify (as claimed by the agent).
        claim: The claim text that should be supported by the source.
            Must be between 1 and 1000 characters (per atlas-docs/03 §6.2).

    Returns:
        A dict with ``exists`` (bool) and ``snippet`` (str | null).
        ``snippet`` is a supporting text excerpt from the source, or null
        if the source_id is not found in the corpus.
    """
    if not claim or len(claim) > 1000:
        raise ValueError("claim must be between 1 and 1000 characters")
    if not source_id:
        raise ValueError("source_id must be a non-empty string")

    service = _get_service()
    chunk = await service.verify(source_id)
    if chunk is None:
        return {"exists": False, "snippet": None}
    return {"exists": True, "snippet": chunk.text}


def main() -> None:
    """Console-script entry point — wires real backends and starts the server."""
    import os

    from elasticsearch import AsyncElasticsearch
    from qdrant_client import AsyncQdrantClient

    from atlas_mcp_citations.backends.es_corpus import ElasticsearchCorpusClient
    from atlas_mcp_citations.backends.qdrant_corpus import QdrantCorpusClient as QdrantCorpusBackend

    es_url = os.environ["ELASTICSEARCH_URL"]
    qdrant_url = os.environ["QDRANT_URL"]

    configure(
        es=ElasticsearchCorpusClient(AsyncElasticsearch([es_url])),
        qdrant=QdrantCorpusBackend(AsyncQdrantClient(url=qdrant_url)),
    )

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
