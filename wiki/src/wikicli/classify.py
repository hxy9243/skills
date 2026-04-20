from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from wikicli.config import WikiConfig
from wikicli.fs import normalize_path
from wikicli.markdown import (
    category_value,
    note_tags_from_metadata,
    parse_frontmatter,
)
from wikicli.text import safe_title, summarize_text


def normalize_category(value: Any, min_depth: int = 2) -> str:
    """
    Normalize a category value into the canonical string form.

    Args:
        value (Any): Either a ``>``-delimited string or a sequence of parts.

    Returns:
        str: The normalized category path.
    """
    normalized = category_value(value, min_depth=min_depth)
    if not normalized:
        raise ValueError(f"packet category must have at least {min_depth} levels")
    return normalized


def normalize_search_terms(value: Any) -> list[str]:
    """
    Normalize search terms into a stable, de-duplicated string list.

    Args:
        value (Any): A string or sequence of strings.

    Returns:
        list[str]: A normalized list of search terms.
    """
    if isinstance(value, str):
        raw_terms = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        raw_terms = [str(term) for term in value]
    else:
        raw_terms = []

    normalized: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        cleaned = safe_title(term)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def require_string(packet: dict[str, Any], field: str) -> str:
    """
    Return a required packet string field after whitespace normalization.

    Args:
        packet (dict[str, Any]): The raw packet dictionary.
        field (str): The required field name.

    Returns:
        str: The stripped string value.

    Raises:
        ValueError: If the field is absent, non-string, or blank.
    """
    value = packet.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"packet is missing {field}")
    return value.strip()


def normalize_tags(value: Any) -> list[str]:
    """
    Normalize an explicit packet tag list.

    Args:
        value (Any): The raw ``tags`` field.

    Returns:
        list[str]: A sorted list of de-duplicated tags.

    Raises:
        ValueError: If ``tags`` is absent or not a list-like value.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("packet is missing tags")
    return sorted({str(tag).strip() for tag in value if str(tag).strip()})


def normalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize and validate an incoming category packet dictionary.

    Ensures required fields exist, formats titles/categories safely, and bounds the packet.

    Args:
        packet (dict[str, Any]): The raw packet dictionary.

    Returns:
        dict[str, Any]: The normalized packet.

    Raises:
        ValueError: If any required semantic field is missing or invalid.
    """
    source = require_string(packet, "source")
    title = safe_title(require_string(packet, "title"))
    summary = summarize_text(require_string(packet, "summary"))
    category = normalize_category(packet.get("category"))
    tags = normalize_tags(packet.get("tags"))
    search_terms = normalize_search_terms(packet.get("search_terms", []))
    return {
        "title": title,
        "summary": summary,
        "category": category,
        "tags": tags,
        "search_terms": search_terms,
        "source": source,
    }


def extract_packet_from_note(path: Path, config: WikiConfig) -> dict[str, Any]:
    """
    Extract a packet only from explicit note frontmatter metadata.

    This function intentionally does not infer title, summary, category, or tags from
    note body text, file path, or the approved category tree.

    Args:
        path (Path): The absolute path to the note.
        config (WikiConfig): The active wiki configuration.

    Returns:
        dict[str, Any]: A normalized packet dictionary.
    """
    text = path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(text)
    rel = normalize_path(path.relative_to(config.notebook_root))
    packet = {
        "source": rel,
        "title": metadata.get("title"),
        "summary": metadata.get("summary"),
        "category": metadata.get("category"),
        "tags": note_tags_from_metadata(metadata) if "tags" in metadata else None,
        "search_terms": metadata.get("search_terms", []),
    }
    return normalize_packet(packet)
