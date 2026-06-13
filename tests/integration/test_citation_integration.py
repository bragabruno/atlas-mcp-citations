"""Integration test — citation verification against real ES + Qdrant.

Spins ephemeral Elasticsearch + Qdrant via testcontainers, seeds one source_id
into ES and a different one into Qdrant, then runs the REAL CitationService
(ElasticsearchCorpusClient + QdrantCorpusClient) end to end. This exercises the
ES-first / Qdrant-fallback orchestration against the live backends the offline
unit tests can only fake — the real `term` lookup, the real payload-filtered
scroll, and the fallback path.

Requires Docker. Marked `integration`, so excluded from the default offline
suite (`pytest`); run explicitly with `pytest -m integration`.
"""

# testcontainers is a namespace package without type stubs.
# pyright: reportMissingTypeStubs=false
from __future__ import annotations

from collections.abc import Iterator

import pytest
from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

pytest.importorskip("testcontainers.elasticsearch")
pytest.importorskip("testcontainers.qdrant")
from testcontainers.elasticsearch import ElasticSearchContainer  # noqa: E402
from testcontainers.qdrant import QdrantContainer  # noqa: E402

from atlas_mcp_citations.backends.es_corpus import ElasticsearchCorpusClient  # noqa: E402
from atlas_mcp_citations.backends.qdrant_corpus import QdrantCorpusClient  # noqa: E402
from atlas_mcp_citations.citation_service import CitationService  # noqa: E402

# Match the local stack's pins (atlas-infra/local/compose.dev.yaml).
_ES_IMAGE = "elasticsearch:9.4.0"
_QDRANT_IMAGE = "qdrant/qdrant:v1.17.1"
_INDEX = "doc_chunks"
_COLLECTION = "doc_chunks"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def es_url() -> Iterator[str]:
    container = (
        ElasticSearchContainer(_ES_IMAGE)
        .with_env("discovery.type", "single-node")
        .with_env("xpack.security.enabled", "false")
        .with_env("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
    )
    with container as es:
        yield f"http://{es.get_container_host_ip()}:{es.get_exposed_port(9200)}"


@pytest.fixture(scope="module")
def qdrant_url() -> Iterator[str]:
    with QdrantContainer(_QDRANT_IMAGE) as qd:
        yield f"http://{qd.get_container_host_ip()}:{qd.get_exposed_port(6333)}"


async def _seed_es(url: str) -> None:
    es = AsyncElasticsearch([url])
    try:
        # source_id must be a keyword so the backend's `term` lookup matches.
        await es.indices.create(
            index=_INDEX,
            mappings={
                "properties": {
                    "source_id": {"type": "keyword"},
                    "text": {"type": "text"},
                }
            },
        )
        await es.index(
            index=_INDEX,
            id="es-1",
            document={"source_id": "EUR-ES-Only-1", "text": "ES corpus chunk text"},
            refresh=True,
        )
    finally:
        await es.close()


async def _seed_qdrant(url: str) -> None:
    qc = AsyncQdrantClient(url=url)
    try:
        await qc.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=8, distance=Distance.COSINE),
        )
        await qc.upsert(
            collection_name=_COLLECTION,
            points=[
                PointStruct(
                    id=1,
                    vector=[0.1] * 8,
                    payload={"source_id": "EUR-QD-Only-1", "text": "Qdrant corpus chunk text"},
                )
            ],
            wait=True,
        )
    finally:
        await qc.close()


async def test_verify_es_first_then_qdrant_fallback(es_url: str, qdrant_url: str) -> None:
    await _seed_es(es_url)
    await _seed_qdrant(qdrant_url)

    es_client = AsyncElasticsearch([es_url])
    qd_client = AsyncQdrantClient(url=qdrant_url)
    try:
        service = CitationService(
            ElasticsearchCorpusClient(es_client),
            QdrantCorpusClient(qd_client),
        )
        es_hit = await service.verify("EUR-ES-Only-1")  # found in ES
        qd_hit = await service.verify("EUR-QD-Only-1")  # ES miss → Qdrant fallback
        missing = await service.verify("EUR-Does-Not-Exist")  # neither backend
    finally:
        await es_client.close()
        await qd_client.close()

    assert es_hit is not None
    assert es_hit.text == "ES corpus chunk text"
    assert qd_hit is not None
    assert qd_hit.text == "Qdrant corpus chunk text"
    assert missing is None
