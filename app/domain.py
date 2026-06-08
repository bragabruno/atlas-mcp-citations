"""Domain types — no framework imports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A single retrieved document chunk."""

    id: str
    text: str
    source_id: str
