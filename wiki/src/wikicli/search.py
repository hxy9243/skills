from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .config import WikiConfig
from .notebook import clean_body_text, load_note, snippet_around, tokenize
from .wiki import active_catalog


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


def search(config: WikiConfig, query: str, *, limit: int) -> list[dict[str, Any]]:
    """Return deterministic search results for a query.

    Matches catalog title, summary, tags, hierarchy, search terms, and source
    body text, then sorts by score and source path for stable output.
    """
    terms = tokenize(query)
    if not terms or limit <= 0:
        return []
    results: list[SearchResult] = []
    for entry in active_catalog(config).values():
        score = 0
        reasons: list[str] = []
        snippets: list[str] = []
        haystacks = {
            "title": entry.title,
            "summary": entry.summary,
            "hierarchy": entry.category,
            "tags": " ".join(entry.tags),
            "search_terms": " ".join(entry.search_terms),
        }
        for reason, text in haystacks.items():
            overlap = _overlap(terms, text)
            if not overlap:
                continue
            score += _weight(reason) * len(overlap)
            reasons.append(reason)
            if reason in {"title", "summary", "hierarchy"}:
                snippets.append(snippet_around(text, overlap))
        try:
            note = load_note(config, entry.source)
        except OSError:
            note = None
        if note is not None:
            body_text = clean_body_text(note.body)
            overlap = _overlap(terms, body_text)
            if overlap:
                score += len(overlap)
                reasons.append("content")
                snippets.append(snippet_around(body_text, overlap))
        if score <= 0:
            continue
        results.append(
            SearchResult(
                source=entry.source,
                title=entry.title,
                hierarchy=entry.category,
                score=score,
                match_reasons=tuple(dict.fromkeys(reasons)),
                snippets=tuple(dict.fromkeys(snippets))[:3],
                tags=entry.tags,
            )
        )
    results.sort(key=lambda item: (-item.score, item.source.casefold()))
    return [result.to_json() for result in results[:limit]]


def _overlap(terms: tuple[str, ...], text: str) -> tuple[str, ...]:
    tokens = set(tokenize(text))
    return tuple(term for term in terms if term in tokens)


def _weight(reason: str) -> int:
    return {
        "title": 8,
        "search_terms": 6,
        "tags": 5,
        "hierarchy": 4,
        "summary": 3,
    }.get(reason, 1)
