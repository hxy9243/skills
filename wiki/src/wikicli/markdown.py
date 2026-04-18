from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from wikicli.text import safe_title


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from a markdown string.
    
    Extracts the key-value pairs from the frontmatter block at the top
    of the file. Supports basic string key-value pairs and flat lists.
    
    Args:
        text (str): The full markdown text.
        
    Returns:
        tuple[dict[str, Any], str]: A tuple containing the parsed metadata dictionary
                                    and the remaining markdown body text.
    """
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    raw_frontmatter, body = parts
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw_frontmatter.splitlines()[1:]:
        if not line.strip():
            current_list_key = None
            continue
        if line.startswith("  - ") and current_list_key:
            metadata.setdefault(current_list_key, []).append(line[4:].strip().strip("'\""))
            continue
        if line.startswith("- ") and current_list_key:
            metadata.setdefault(current_list_key, []).append(line[2:].strip().strip("'\""))
            continue
        current_list_key = None
        key, sep, value = line.partition(":")
        if not sep:
            continue
        normalized_key = key.strip().lower()
        stripped_value = value.strip()
        if not stripped_value:
            metadata[normalized_key] = []
            current_list_key = normalized_key
            continue
        metadata[normalized_key] = stripped_value.strip("'\"")
    return metadata, body


def strip_frontmatter(text: str) -> str:
    """
    Remove the YAML frontmatter block from a markdown string.
    
    Args:
        text (str): The full markdown text.
        
    Returns:
        str: The markdown text without the frontmatter block.
    """
    return parse_frontmatter(text)[1]


def upsert_frontmatter_property(text: str, key: str, value: str) -> str:
    """
    Insert or update a property in the YAML frontmatter of a markdown string.
    
    If the frontmatter does not exist, it will be created. If the property
    already exists, its value will be replaced. Only primitive string
    replacement is supported (no nested objects).
    
    Args:
        text (str): The full markdown text.
        key (str): The frontmatter property key.
        value (str): The string value to assign to the key.
        
    Returns:
        str: The updated markdown text.
    """
    rendered = f'{key}: {json.dumps(value, ensure_ascii=False)}'
    if not text.startswith("---\n"):
        body = text.lstrip("\n")
        return f"---\n{rendered}\n---\n{body}"

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        body = text.lstrip("\n")
        return f"---\n{rendered}\n---\n{body}"

    raw_frontmatter, body = parts
    lines = raw_frontmatter.splitlines()[1:]
    output: list[str] = []
    target = key.lower()
    replaced = False
    skip_continuation = False

    for line in lines:
        stripped = line.strip()
        if skip_continuation:
            if line.startswith("  - ") or line.startswith("- "):
                continue
            skip_continuation = False

        if not stripped:
            output.append(line)
            continue

        current_key, sep, current_value = line.partition(":")
        if sep and current_key.strip().lower() == target:
            if not replaced:
                output.append(rendered)
                replaced = True
            if not current_value.strip():
                skip_continuation = True
            continue

        output.append(line)

    if not replaced:
        if output and output[-1].strip():
            output.append(rendered)
        else:
            while output and not output[-1].strip():
                output.pop()
            output.append(rendered)

    return "---\n" + "\n".join(output) + "\n---\n" + body


def title_from_text(text: str, path: Path) -> str:
    """
    Extract the title of a note from its first H1 heading.
    
    If no H1 heading is found, it falls back to parsing the file stem
    (filename without extension).
    
    Args:
        text (str): The markdown text.
        path (Path): The file path of the note.
        
    Returns:
        str: The extracted and safe title.
    """
    body = strip_frontmatter(text)
    for line in body.splitlines():
        if line.startswith("# "):
            return safe_title(line[2:])
    return safe_title(path.stem.replace("_", " "))


def clean_note_text(text: str) -> str:
    """
    Clean markdown text for summarization and tokenization.
    
    Strips frontmatter, headings, code blocks, images, and raw URLs.
    
    Args:
        text (str): The raw markdown text.
        
    Returns:
        str: The cleaned, plain text body.
    """
    body = strip_frontmatter(text)
    lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith("# "):
            continue
        if stripped.startswith("```") or stripped.startswith("!["):
            continue
        if stripped.startswith("http://") or stripped.startswith("https://"):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def category_value(category_path: Sequence[str]) -> str:
    """
    Format a sequence of category layers into a single string.
    
    Args:
        category_path (Sequence[str]): A list of category layers.
        
    Returns:
        str: The joined category string (e.g., 'Layer 1 > Layer 2').
    """
    return " > ".join(safe_title(part) for part in category_path)


def parse_category_path(value: Any) -> list[str] | None:
    """
    Parse a category property value into a list of layers.
    
    Supports both strings delimited by '>' and lists of strings.
    
    Args:
        value (Any): The raw category value from frontmatter or config.
        
    Returns:
        list[str] | None: A list of layer strings, or None if invalid.
    """
    if isinstance(value, str):
        parts = [safe_title(part) for part in value.split(">") if part.strip()]
        return parts if len(parts) >= 2 else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts = [safe_title(str(part)) for part in value if str(part).strip()]
        return parts if len(parts) >= 2 else None
    return None


def frontmatter_category_path(text: str) -> list[str] | None:
    """
    Extract and parse the 'category' property from a note's frontmatter.
    
    Args:
        text (str): The full markdown text.
        
    Returns:
        list[str] | None: The parsed category path, or None if not found.
    """
    metadata, _ = parse_frontmatter(text)
    return parse_category_path(metadata.get("category"))


def apply_category_property(path: Path, category_path: Sequence[str]) -> bool:
    """
    Update the 'category' frontmatter property of a note file on disk.
    
    Args:
        path (Path): The file path to the note.
        category_path (Sequence[str]): The category path to apply.
        
    Returns:
        bool: True if the file was modified, False if it already had the correct category.
    """
    original = path.read_text(encoding="utf-8")
    updated = upsert_frontmatter_property(original, "category", category_value(category_path))
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def note_tags_from_metadata(metadata: dict[str, Any]) -> list[str]:
    """
    Extract and normalize tags from parsed frontmatter metadata.
    
    Ensures all tags are strings and prefixed with '#'.
    
    Args:
        metadata (dict[str, Any]): The parsed frontmatter metadata.
        
    Returns:
        list[str]: A sorted list of unique tags.
    """
    raw = metadata.get("tags", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    tags = []
    for tag in raw:
        cleaned = str(tag).strip().strip("'\"")
        if cleaned:
            tags.append(cleaned if cleaned.startswith("#") else f"#{cleaned}")
    return sorted(set(tags))
