#!/usr/bin/env bash
# build.sh — build verification: the MCP server package imports cleanly (the
# FastMCP app + verify_citation tool are constructed at import time). Publishes
# nothing. No OpenAPI contract here — this is an MCP (stdio/streamable-http)
# server, not an HTTP API with an OpenAPI surface.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
# shellcheck source=scripts/lib/colors.sh
source scripts/lib/colors.sh
# shellcheck source=scripts/lib/common.sh
source scripts/lib/common.sh
trap 'on_err "$LINENO" "$?"' ERR

require_cmd python "pip install -e .[dev]"
run "import smoke (app.server)" python -c "import app.server"

log_ok "build verification passed"
