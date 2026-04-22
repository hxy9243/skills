from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    source: str
    title: str
    summary: str
    category: str
    tags: tuple[str, ...]
