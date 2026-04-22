from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    """Active catalog record after replaying add/remove log events."""

    source: str
    title: str
    summary: str
    category: str
    tags: tuple[str, ...]
