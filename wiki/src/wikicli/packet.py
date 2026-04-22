from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .app import Issue
from .category import CategoryPath
from .notebook import Note


@dataclass(frozen=True)
class Packet:
    """Agent-produced classification packet for one source note."""

    title: str
    summary: str
    category: CategoryPath
    tags: tuple[str, ...]
    search_terms: tuple[str, ...]
    source: str

    def to_json(self) -> dict[str, Any]:
        """Serialize the normalized packet for CLI responses and log events."""
        return {
            "title": self.title,
            "summary": self.summary,
            "category": self.category.to_json(),
            "tags": list(self.tags),
            "search_terms": list(self.search_terms),
            "source": self.source,
        }


def parse_packet(raw_packet: str) -> tuple[Packet | None, list[Issue]]:
    """Parse untrusted packet JSON into a normalized packet or issues.

    Success input:
    `{"title":"DSPy","summary":"Prompt optimization","category":"CS > AI","tags":["#ai"],"source":"Notes/DSPy.md"}`

    Success output is `(Packet(...), [])`; failure output is `(None, [Issue(...)])`.
    """
    try:
        payload = json.loads(raw_packet)
    except json.JSONDecodeError as exc:
        return None, [
            Issue(
                "packet_json_invalid",
                f"packet JSON is invalid: {exc.msg}",
                line=exc.lineno,
            )
        ]

    if isinstance(payload, list):
        return None, [
            Issue(
                "packet_not_object",
                "packet payload must be a single object, not a list",
            )
        ]
    if not isinstance(payload, dict):
        return None, [
            Issue("packet_not_object", "packet payload must be a JSON object")
        ]

    issues: list[Issue] = []
    title = _required_string(payload, "title", issues)
    summary = _required_string(payload, "summary", issues)
    category_raw = _required_string(payload, "category", issues)
    source_raw = _required_string(payload, "source", issues)

    try:
        category = CategoryPath.parse(category_raw) if category_raw else None
    except ValueError as exc:
        category = None
        issues.append(Issue("packet_category_invalid", str(exc)))

    try:
        source = Note.normalize_source(source_raw) if source_raw else ""
    except ValueError as exc:
        source = ""
        issues.append(Issue("packet_source_invalid", str(exc), source=source_raw))

    tags = _string_tuple(payload.get("tags", ()), "tags", issues)
    search_terms = _string_tuple(
        payload.get("search_terms", ()), "search_terms", issues
    )

    if issues or category is None:
        return None, issues
    return Packet(title, summary, category, tags, search_terms, source), []


def _required_string(payload: dict[str, Any], key: str, issues: list[Issue]) -> str:
    """Read one required non-empty string field and accumulate issues."""
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(
            Issue(
                "packet_field_invalid",
                f"packet field must be a non-empty string: {key}",
            )
        )
        return ""
    return value.strip()


def _string_tuple(value: Any, key: str, issues: list[Issue]) -> tuple[str, ...]:
    """Normalize optional list-of-string packet fields into tuples."""
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        issues.append(
            Issue(
                "packet_field_invalid", f"packet field must be a list of strings: {key}"
            )
        )
        return ()
    return tuple(item.strip() for item in value if item.strip())
