#!/usr/bin/env bash
# local.sh — run the MCP citations server locally over FastMCP Streamable HTTP.
# The entrypoint (atlas_mcp_citations/server.py __main__) reads ELASTICSEARCH_URL and QDRANT_URL
# from the environment; these default to localhost so a local ES + Qdrant
# (e.g. docker compose) are picked up automatically. Override as needed.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
# shellcheck source=scripts/lib/colors.sh
source scripts/lib/colors.sh
# shellcheck source=scripts/lib/common.sh
source scripts/lib/common.sh
trap 'on_err "$LINENO" "$?"' ERR

require_cmd python "pip install -e .[dev]"
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://127.0.0.1:9200}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
log_info "atlas-mcp-citations → FastMCP Streamable HTTP /mcp (Ctrl-C to stop)"
log_info "ES=${ELASTICSEARCH_URL}  Qdrant=${QDRANT_URL}"
exec python -m atlas_mcp_citations.server
