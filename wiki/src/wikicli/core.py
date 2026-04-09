from __future__ import annotations

import fnmatch
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from wikicli.config import DEFAULT_EXCLUDES, WikiConfig, ensure_layout, read_json


SYSTEM_NOTE_NAMES = {"dashboard", "dashboard-index", "index", "readme", "summary", "log"}
LAYER_LABEL_RE = re.compile(r"^layer\d+\s*:\s*", re.IGNORECASE)
LAYER_BULLET_RE = re.compile(r"^-\s*layer(?P<depth>\d+)\s*:\s*(?P<label>.+)$", re.IGNORECASE)
NOTE_LINK_RE = re.compile(r"^\s*-\s*\[\[([^\]]+)\]\]\s*$")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "use", "with",
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_path(path: Path) -> str:
    return path.as_posix()


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.ASCII)
    value = re.sub(r"[_\s]+", "-", value.strip().lower())
    return value.strip("-") or "untitled"


def safe_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value or "Untitled"


def strip_layer_label(value: str) -> str:
    return safe_title(LAYER_LABEL_RE.sub("", value.strip()))


def format_layer_label(depth: int, value: str) -> str:
    return f"layer{depth}: {safe_title(value)}"


def markdown_label(value: str) -> str:
    match = re.match(r"\[([^\]]+)\]\([^)]+\)$", value.strip())
    if match:
        return match.group(1)
    return value.strip()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
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
    return parse_frontmatter(text)[1]


def category_value(category_path: Sequence[str]) -> str:
    return " > ".join(safe_title(part) for part in category_path)


def parse_category_path(value: Any) -> list[str] | None:
    if isinstance(value, str):
        parts = [safe_title(part) for part in value.split(">") if part.strip()]
        return parts if len(parts) >= 2 else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts = [safe_title(str(part)) for part in value if str(part).strip()]
        return parts if len(parts) >= 2 else None
    return None


def frontmatter_category_path(text: str) -> list[str] | None:
    metadata, _ = parse_frontmatter(text)
    return parse_category_path(metadata.get("category"))


def upsert_frontmatter_property(text: str, key: str, value: str) -> str:
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


def apply_category_property(path: Path, category_path: Sequence[str]) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = upsert_frontmatter_property(original, "category", category_value(category_path))
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def title_from_text(text: str, path: Path) -> str:
    body = strip_frontmatter(text)
    for line in body.splitlines():
        if line.startswith("# "):
            return safe_title(line[2:])
    return safe_title(path.stem.replace("_", " "))


def clean_note_text(text: str) -> str:
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


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
    return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 25]


def summarize_text(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]


def note_tags_from_metadata(metadata: dict[str, Any]) -> list[str]:
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


def extract_tree_section(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if "## Category Tree" not in text or "\n---\n" not in text:
        return None
    after_header = text.split("## Category Tree", 1)[1]
    tree_block, _, _ = after_header.partition("\n---\n")
    return tree_block.strip()


def parse_allowed_category_paths(path: Path) -> set[tuple[str, ...]]:
    text = extract_tree_section(path)
    if not text:
        return set()

    allowed: set[tuple[str, ...]] = set()
    stack: list[str] = []
    for raw_line in text.splitlines():
        match = LAYER_BULLET_RE.match(raw_line.lstrip())
        if not match:
            continue
        depth = max(1, int(match.group("depth")))
        name = strip_layer_label(markdown_label(match.group("label")))
        while len(stack) >= depth:
            stack.pop()
        stack.append(name)
        if depth >= 2:
            allowed.add(tuple(stack))
    return allowed


def parse_index_note_assignments(path: Path) -> dict[str, list[str]]:
    text = extract_tree_section(path)
    if not text:
        return {}

    assignments: dict[str, list[str]] = {}
    stack: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.rstrip()
        match = LAYER_BULLET_RE.match(stripped.lstrip())
        if match:
            depth = max(1, int(match.group("depth")))
            name = strip_layer_label(markdown_label(match.group("label")))
            while len(stack) >= depth:
                stack.pop()
            stack.append(name)
            continue

        note_match = NOTE_LINK_RE.match(stripped)
        if note_match and len(stack) >= 2:
            assignments[normalize_path(Path(note_match.group(1)))] = list(stack)
    return assignments


def infer_category_from_rules(config: WikiConfig, title: str, text: str, source_relpath: str, tags: Sequence[str] | None = None) -> list[str]:
    tag_text = " ".join(tags or [])
    scorebag = Counter(tokenize(f"{title}\n{text}\n{source_relpath}\n{tag_text}"))
    best_score = 0
    best = ["Needs Review", "Reclassify", "Pending"]
    for rule in config.category_rules:
        score = sum(scorebag.get(keyword.lower(), 0) for keyword in rule["keywords"])
        if score > best_score:
            best_score = score
            best = rule["category"]
    return best


def score_category_path(path_parts: Sequence[str], title: str, text: str, source_relpath: str, tags: Sequence[str] | None = None) -> tuple[int, int, int]:
    title_bag = Counter(tokenize(title))
    text_bag = Counter(tokenize(text))
    source_bag = Counter(tokenize(source_relpath))
    tag_bag = Counter(tokenize(" ".join(tags or [])))
    haystack = " ".join([title.lower(), text.lower(), source_relpath.lower(), " ".join(tag.lower() for tag in (tags or []))])

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


def infer_category(config: WikiConfig, title: str, text: str, source_relpath: str, tags: Sequence[str] | None = None) -> list[str]:
    allowed_paths = sorted(parse_allowed_category_paths(config.category_tree_path))
    if allowed_paths:
        ranked = sorted(
            ((score_category_path(path, title, text, source_relpath, tags), list(path)) for path in allowed_paths),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best_path = ranked[0]
        if best_score[0] > 0 or best_score[1] > 0:
            return best_path

    return infer_category_from_rules(config, title, text, source_relpath, tags)


def configured_category(config: WikiConfig, source_relpath: str) -> list[str] | None:
    config_path = config.generated_root / "config.json"
    raw = read_json(config_path, {}) if config_path.exists() else {}
    override = (raw.get("category_overrides") or {}).get(source_relpath)
    if override:
        category = [safe_title(part) for part in override]
        if len(category) >= 2:
            return category
    prefix_overrides = raw.get("category_prefix_overrides") or {}
    best_prefix = None
    for prefix in prefix_overrides:
        normalized_prefix = prefix.rstrip("/")
        if source_relpath.startswith(normalized_prefix + "/") or source_relpath == normalized_prefix:
            if best_prefix is None or len(normalized_prefix) > len(best_prefix):
                best_prefix = normalized_prefix
    if best_prefix is None:
        return None
    category = [safe_title(part) for part in prefix_overrides[best_prefix]]
    return category if len(category) >= 2 else None


def gather_source_files(config: WikiConfig) -> list[Path]:
    files: list[Path] = []
    generated_marker = normalize_path(config.generated_root)
    for root in config.include_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            resolved = path.resolve()
            rel = normalize_path(resolved.relative_to(config.notebook_root))
            if normalize_path(resolved).startswith(generated_marker):
                continue
            if any(part in DEFAULT_EXCLUDES for part in resolved.relative_to(config.notebook_root).parts):
                continue
            if any(fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in config.exclude_globs):
                continue
            files.append(resolved)
    return sorted(set(files))


def normalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    source = str(packet.get("source") or "").strip()
    if not source:
        raise ValueError("packet is missing source")
    title = safe_title(packet.get("title") or Path(source).stem)
    summary = summarize_text(packet.get("summary") or title)
    category = [safe_title(part) for part in (packet.get("category_path") or [])]
    if len(category) < 2:
        raise ValueError("packet category_path must have at least 2 levels")
    tags = sorted({str(tag).strip() for tag in packet.get("tags", []) if str(tag).strip()})
    return {"title": title, "summary": summary, "category_path": category, "tags": tags, "source": source}


def extract_packet_from_note(path: Path, config: WikiConfig) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(text)
    tags = note_tags_from_metadata(metadata)
    cleaned = clean_note_text(text)
    title = title_from_text(text, path)
    sentences = split_sentences(cleaned)
    summary = summarize_text(sentences[0] if sentences else cleaned or title)
    rel = normalize_path(path.relative_to(config.notebook_root))
    category_override = configured_category(config, rel)
    frontmatter_category = frontmatter_category_path(text)
    return {
        "title": title,
        "summary": summary,
        "category_path": frontmatter_category or category_override or infer_category(config, title, cleaned, rel, tags),
        "tags": tags,
        "source": rel,
    }


def append_log_event(config: WikiConfig, event: dict[str, Any]) -> None:
    ensure_layout(config)
    with config.log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {json.dumps(event, ensure_ascii=True, sort_keys=True)}\n")


def read_log_events(config: WikiConfig) -> list[dict[str, Any]]:
    if not config.log_path.exists():
        return []
    events = []
    for line in config.log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- {"):
            continue
        try:
            events.append(json.loads(stripped[2:]))
        except json.JSONDecodeError:
            continue
    return events


def active_catalog(config: WikiConfig) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for event in read_log_events(config):
        source = event.get("source")
        if not source:
            continue
        if event.get("action") == "add":
            catalog[source] = {
                "title": event["title"],
                "summary": event["summary"],
                "category_path": event["category_path"],
                "tags": event.get("tags", []),
                "source": source,
                "source_mtime_ns": event.get("source_mtime_ns"),
                "updated_at": event["timestamp"],
            }
        elif event.get("action") == "remove":
            catalog.pop(source, None)
    return catalog


def source_mtime_ns(config: WikiConfig, source: str) -> int | None:
    path = (config.notebook_root / source).resolve()
    if not path.exists():
        return None
    return path.stat().st_mtime_ns


def is_system_note(source: str) -> bool:
    return slugify(Path(source).stem) in SYSTEM_NOTE_NAMES
