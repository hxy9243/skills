from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    hierarchy: str
    score: int
    match_reasons: tuple[str, ...]
    snippets: tuple[str, ...]
    tags: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["match_reasons"] = list(self.match_reasons)
        data["snippets"] = list(self.snippets)
        data["tags"] = list(self.tags)
        return data


def search(query: str, *, limit: int) -> list[dict[str, Any]]:
    if not query.strip() or limit <= 0:
        return []
    return []
