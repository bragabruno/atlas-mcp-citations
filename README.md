# atlas-mcp-citations

MCP server that verifies cited sources against the Atlas ingested corpus. Built with the official Python `mcp` SDK, Python 3.12 asyncio, and deployed as a standalone K8s service on AKS.

## Tool Contract

### `verify_citation`

```
verify_citation(source_id: str, claim: str) -> {exists: bool, snippet: str | null}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_id` | `str` | The source identifier to verify (as claimed by the agent) |
| `claim` | `str` | The claim text that should be supported by the source |

**Returns:**

| Field | Type | Description |
|-------|------|-------------|
| `exists` | `bool` | Whether the `source_id` is present in the ingested corpus |
| `snippet` | `str \| null` | A supporting text snippet from the source, or `null` if not found |

## Role in Citation Enforcement

`atlas-mcp-citations` is called at two points in the Atlas pipeline:

1. **Gateway post-guardrail** — after a response is generated, the gateway's citation enforcement step calls `verify_citation` for each claimed `source_id`. Responses referencing non-existent sources are rejected or flagged.
2. **Agent runtime** — agents may call `verify_citation` proactively to validate sources before including them in a response.

## Corpus Lookup

The server checks the ingested corpus by querying both:

- **Elasticsearch** — `doc_chunks` index, lookup by `source_id` field.
- **Qdrant** — collection `doc_chunks`, payload filter on `source_id`.

The first matching chunk's text is returned as the `snippet`.

## Dependencies

| Dependency | Role |
|------------|------|
| `mcp` (official Python SDK) | MCP server framework |
| Elasticsearch | Corpus lookup by `source_id` over `doc_chunks` |
| Qdrant | Corpus lookup by `source_id` over collection `doc_chunks` |

## Diagrams

- [Component (C4-L3)](docs/diagrams/component-c4.md)
- [Sequence — verify citation](docs/diagrams/seq-verify-citation.md)
- [Class diagram](docs/diagrams/class.puml)

## Related

- [atlas-mcp-doc-search](../atlas-mcp-doc-search) — hybrid document search MCP server
- [atlas-docs](../atlas-docs) — document ingestion pipeline that populates the corpus
