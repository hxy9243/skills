from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    """Normalized search hit from source notes, generated pages, or metadata."""

    source: str
    title: str
    hierarchy: str
    score: int
    match_reasons: tuple[str, ...]
    snippets: tuple[str, ...]
    tags: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        """Serialize tuple fields as JSON arrays for CLI responses."""
        data = asdict(self)
        data["match_reasons"] = list(self.match_reasons)
        data["snippets"] = list(self.snippets)
        data["tags"] = list(self.tags)
        return data


def search(query: str, *, limit: int) -> list[dict[str, Any]]:
    """Return deterministic search results for a query.

    The skeleton intentionally returns no hits until notebook/catalog search is
    implemented; empty queries and non-positive limits also produce no results.
    """
    if not query.strip() or limit <= 0:
        return []
    return []
