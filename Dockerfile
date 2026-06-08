# syntax=docker/dockerfile:1
# atlas-mcp-citations runtime image — multi-stage, non-root, pinned base.
# Base pinned exactly (atlas-docs/02 §2), matching the CI image. Runtime deps are
# the exact-pinned [project.dependencies] from pyproject.toml (no dev deps).

FROM python:3.12.13-slim-bookworm AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
COPY . .
# Install the package + its pinned runtime deps into an isolated venv.
RUN python -m venv /venv \
 && /venv/bin/pip install --no-cache-dir .

FROM python:3.12.13-slim-bookworm AS runtime
# Non-root runtime user.
RUN groupadd --system app \
 && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /venv /venv
COPY --from=build /app /app
ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8000
# MCP citations server over FastMCP Streamable HTTP (port 8000). The entrypoint
# reads ELASTICSEARCH_URL / QDRANT_URL from the env; credentials come from the
# Key Vault CSI mount at deploy time (atlas-docs/04 §3). The image ships no
# secrets. There is no console_script in pyproject, so run the module directly.
CMD ["python", "-m", "atlas_mcp_citations.server"]
