from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from wikicli.config import WikiConfig
from wikicli.fs import normalize_path
from wikicli.markdown import (
    category_value,
    clean_note_text,
    frontmatter_category,
    note_tags_from_metadata,
    parse_frontmatter,
    title_from_text,
)
from wikicli.text import safe_title, split_sentences, summarize_text, tokenize
from wikicli.tree import parse_allowed_category_paths


def score_category_path(
    path_parts: Sequence[str],
    title: str,
    text: str,
    source_relpath: str,
    tags: Sequence[str] | None = None,
) -> tuple[int, int, int]:
    """
    Calculate a relevance score for a given category path against a note.

    Args:
        path_parts (Sequence[str]): The category path to evaluate.
        title (str): The note title.
        text (str): The note body text.
        source_relpath (str): The relative path of the source note.
        tags (Sequence[str] | None): A list of tags for the note.

    Returns:
        tuple[int, int, int]: A scoring tuple (total_score, matched_parts, inverted_depth).
    """
    title_bag = Counter(tokenize(title))
    text_bag = Counter(tokenize(text))
    source_bag = Counter(tokenize(source_relpath))
    tag_bag = Counter(tokenize(" ".join(tags or [])))
    haystack = " ".join(
        [
            title.lower(),
            text.lower(),
            source_relpath.lower(),
            " ".join(tag.lower() for tag in (tags or [])),
        ]
    )

    score = 0
    matched = 0
    for part in path_parts:
        part_tokens = set(tokenize(part))
        if not part_tokens:
            continue
        token_score = 0
        for token in part_tokens:
            token_score += title_bag.get(token, 0) * 8
            token_score += tag_bag.get(token, 0) * 6
            token_score += source_bag.get(token, 0) * 5
            token_score += text_bag.get(token, 0) * 2
        phrase = part.lower()
        if phrase and phrase in haystack:
            token_score += 12
        if token_score > 0:
            matched += 1
        score += token_score
    return score, matched, -len(path_parts)


def infer_category(
    config: WikiConfig,
    title: str,
    text: str,
    source_relpath: str,
    tags: Sequence[str] | None = None,
) -> str:
    """
    Infer the best category by evaluating allowed tree paths or falling back to rules.

    Args:
        config (WikiConfig): The active wiki configuration.
        title (str): The note title.
        text (str): The note body text.
        source_relpath (str): The relative path of the source note.
        tags (Sequence[str] | None): A list of tags for the note.

    Returns:
        str: The best-matching category path.
    """
    allowed_paths = sorted(parse_allowed_category_paths(config.category_tree_path))
    if allowed_paths:
        ranked = sorted(
            (
                (
                    score_category_path(path, title, text, source_relpath, tags),
                    list(path),
                )
                for path in allowed_paths
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best_path = ranked[0]
        if best_score[0] > 0 or best_score[1] > 0:
            return " > ".join(best_path)

    return "Needs Review"


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


def infer_search_terms(title: str, category: str, tags: Sequence[str]) -> list[str]:
    """
    Infer default search terms for a note when none are explicitly provided.

    Args:
        title (str): The note title.
        category (str): The normalized category string.
        tags (Sequence[str]): The normalized note tags.

    Returns:
        list[str]: A de-duplicated list of inferred search terms.
    """
    leaf = category.rsplit(">", 1)[-1].strip()
    raw_terms = [title, leaf, *(tag.lstrip("#") for tag in tags)]
    return normalize_search_terms(raw_terms)


def normalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize and validate an incoming category packet dictionary.

    Ensures required fields exist, formats titles/categories safely, and bounds the packet.

    Args:
        packet (dict[str, Any]): The raw packet dictionary.

    Returns:
        dict[str, Any]: The normalized packet.

    Raises:
        ValueError: If 'source' is missing or 'category' is too shallow.
    """
    source = str(packet.get("source") or "").strip()
    if not source:
        raise ValueError("packet is missing source")
    title = safe_title(packet.get("title") or Path(source).stem)
    summary = summarize_text(packet.get("summary") or title)
    category = normalize_category(
        packet.get("category") or packet.get("category_path") or []
    )
    tags = sorted(
        {str(tag).strip() for tag in packet.get("tags", []) if str(tag).strip()}
    )
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
    Extract a fully formed metadata packet from a note by parsing and inferencing.

    Args:
        path (Path): The absolute path to the note.
        config (WikiConfig): The active wiki configuration.

    Returns:
        dict[str, Any]: A packet dictionary with title, summary, category, tags, and source.
    """
    text = path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(text)
    tags = note_tags_from_metadata(metadata)
    cleaned = clean_note_text(text)
    title = title_from_text(text, path)
    sentences = split_sentences(cleaned)
    summary = summarize_text(sentences[0] if sentences else cleaned or title)
    rel = normalize_path(path.relative_to(config.notebook_root))
    current_category = frontmatter_category(text)
    inferred_category = infer_category(config, title, cleaned, rel, tags)
    category = normalize_category(current_category or inferred_category, min_depth=1)
    return {
        "title": title,
        "summary": summary,
        "category": category,
        "tags": tags,
        "search_terms": infer_search_terms(title, category, tags),
        "source": rel,
    }
