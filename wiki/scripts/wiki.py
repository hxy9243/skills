#!/usr/bin/env python3
"""Lightweight deterministic backend for the wiki skill."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


DEFAULT_EXCLUDES = [
    ".git",
    ".obsidian",
    ".trash",
    ".venv",
    "__pycache__",
    "node_modules",
    "_WIKI",
]
CATEGORY_RULES = [
    (["agent", "assistant", "tool", "workflow", "automation"], ["Computer Science", "AI Systems", "Agents"]),
    (["infra", "infrastructure", "cluster", "runtime", "container", "vm", "orchestration", "deploy"], ["Computer Science", "AI Systems", "Infrastructure"]),
    (["memory", "context", "recall", "buffer", "state"], ["Computer Science", "AI Systems", "Memory"]),
    (["model", "training", "inference", "neural", "transformer", "gradient", "rlhf", "finetuning", "learning"], ["Computer Science", "Machine Learning", "Systems"]),
    (["distributed", "database", "replication", "consensus", "scheduler", "cluster"], ["Computer Science", "Computer Systems", "Distributed Systems"]),
    (["search", "retrieval", "index", "embedding", "vector"], ["Computer Science", "Knowledge Systems", "Retrieval"]),
    (["product", "market", "strategy", "company", "startup"], ["Culture", "Technology", "Product Strategy"]),
    (["design", "typography", "layout", "color", "ui"], ["Design", "Interface Design", "Visual Systems"]),
]
SYSTEM_NOTE_NAMES = {
    "dashboard",
    "dashboard-index",
    "index",
    "readme",
    "summary",
    "log",
}
LAYER_LABEL_RE = re.compile(r"^layer\d+\s*:\s*", re.IGNORECASE)
LAYER_BULLET_RE = re.compile(r"^-\s*layer(?P<depth>\d+)\s*:\s*(?P<label>.+)$", re.IGNORECASE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "with",
}


@dataclass
class WikiConfig:
    notebook_root: Path
    include_roots: list[Path]
    exclude_globs: list[str]
    generated_root: Path

    @property
    def categories_dir(self) -> Path:
        return self.generated_root / "categories"

    @property
    def index_path(self) -> Path:
        return self.generated_root / "index.md"

    @property
    def log_path(self) -> Path:
        return self.generated_root / "log.md"

    @property
    def category_tree_path(self) -> Path:
        return self.generated_root / "index.md"


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


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | None) -> WikiConfig:
    explicit_path = Path(config_path).expanduser().resolve() if config_path else None
    global_path = Path("~/.wiki/config.json").expanduser()

    if explicit_path:
        raw = read_json(explicit_path, {}) if explicit_path.exists() else {}
    else:
        raw = read_json(global_path, {}) if global_path.exists() else {}
        hinted_notebook_root = Path(raw.get("notebook_root") or str(Path.home() / "Documents" / "kevinhusnotes")).expanduser().resolve()
        hinted_generated_root = Path(raw.get("generated_root") or str(hinted_notebook_root / "_WIKI")).expanduser().resolve()
        local_path = hinted_generated_root / "config.json"
        if local_path.exists():
            local_raw = read_json(local_path, {})
            raw = merge_dicts(raw, local_raw)

    notebook_root = Path(raw.get("notebook_root") or str(Path.home() / "Documents" / "kevinhusnotes")).expanduser().resolve()
    generated_root = Path(raw.get("generated_root") or str(notebook_root / "_WIKI")).expanduser().resolve()
    include_roots = []
    for item in raw.get("include_roots") or ["."]:
        root = Path(item)
        include_roots.append(root if root.is_absolute() else (notebook_root / root).resolve())
    exclude_globs = sorted(set(DEFAULT_EXCLUDES + list(raw.get("exclude_globs", []))))
    return WikiConfig(notebook_root=notebook_root, include_roots=include_roots, exclude_globs=exclude_globs, generated_root=generated_root)


def ensure_layout(config: WikiConfig) -> None:
    config.generated_root.mkdir(parents=True, exist_ok=True)
    config.categories_dir.mkdir(parents=True, exist_ok=True)
    if not config.log_path.exists():
        config.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    if not config.index_path.exists():
        config.index_path.write_text("# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n", encoding="utf-8")


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


def infer_category(title: str, text: str, source_relpath: str) -> list[str]:
    scorebag = Counter(tokenize(f"{title}\n{text}\n{source_relpath}"))
    best_score = 0
    best = ["Needs Review", "Reclassify", "Pending"]
    for keywords, category in CATEGORY_RULES:
        score = sum(scorebag.get(keyword.lower(), 0) for keyword in keywords)
        if score > best_score:
            best_score = score
            best = category
    return best


def configured_category(config: WikiConfig, source_relpath: str) -> list[str] | None:
    config_path = config.generated_root / "config.json"
    raw = read_json(config_path, {}) if config_path.exists() else {}
    override = (raw.get("category_overrides") or {}).get(source_relpath)
    if override:
        category = [safe_title(part) for part in override]
        if len(category) >= 3:
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
    return category if len(category) >= 3 else None


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


def extract_tree_section_from_index(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if "## Category Tree" not in text or "\n---\n" not in text:
        return None
    after_header = text.split("## Category Tree", 1)[1]
    tree_block, _, _ = after_header.partition("\n---\n")
    return tree_block.strip()


def parse_category_tree_structure(path: Path) -> list[dict[str, Any]]:
    text = extract_tree_section_from_index(path)
    if not text:
        return []
    tree: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()
        match = LAYER_BULLET_RE.match(stripped)
        if not match:
            continue
        depth = max(1, int(match.group("depth")))
        node = {"name": strip_layer_label(markdown_label(match.group("label"))), "children": []}
        if depth == 1:
            tree.append(node)
            stack = [node]
            continue
        while len(stack) >= depth:
            stack.pop()
        if not stack:
            continue
        stack[-1]["children"].append(node)
        stack.append(node)
    return tree


def parse_category_tree(path: Path) -> set[tuple[str, ...]]:
    allowed: set[tuple[str, ...]] = set()

    def visit(node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        path_parts = (*prefix, node["name"])
        if not node["children"]:
            allowed.add(path_parts)
            return
        for child in node["children"]:
            visit(child, path_parts)

    for root in parse_category_tree_structure(path):
        visit(root, ())
    return allowed


def normalize_packet(packet: dict[str, Any], config: WikiConfig) -> dict[str, Any]:
    source = str(packet.get("source") or "").strip()
    if not source:
        raise ValueError("packet is missing source")
    title = safe_title(packet.get("title") or Path(source).stem)
    summary = summarize_text(packet.get("summary") or title)
    category = [safe_title(part) for part in (packet.get("category_path") or [])]
    if len(category) < 3:
        raise ValueError("packet category_path must have at least 3 levels")
    tags = sorted({str(tag).strip() for tag in packet.get("tags", []) if str(tag).strip()})
    return {
        "title": title,
        "summary": summary,
        "category_path": category,
        "tags": tags,
        "source": source,
    }


def extract_packet_from_note(path: Path, config: WikiConfig) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(text)
    cleaned = clean_note_text(text)
    title = title_from_text(text, path)
    sentences = split_sentences(cleaned)
    summary = summarize_text(sentences[0] if sentences else cleaned or title)
    rel = normalize_path(path.relative_to(config.notebook_root))
    category_override = configured_category(config, rel)
    return {
        "title": title,
        "summary": summary,
        "category_path": category_override or infer_category(title, cleaned, rel),
        "tags": note_tags_from_metadata(metadata),
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
    lowered = slugify(Path(source).stem)
    return lowered in SYSTEM_NOTE_NAMES


def category_page_path(config: WikiConfig, path_parts: Sequence[str]) -> Path:
    current = config.categories_dir
    for part in path_parts:
        current = current / slugify(part)
    return current / "index.md"


def branch_intro(path_parts: Sequence[str], notes: list[dict[str, Any]], child_names: list[str]) -> str:
    if child_names:
        return summarize_text(
            f"{' -> '.join(path_parts)} groups {', '.join(child_names[:5])}. "
            f"It currently references {len(notes)} notes that help future retrieval and Q&A for this branch."
        )
    titles = [note["title"] for note in notes[:4]]
    return summarize_text(
        f"{' -> '.join(path_parts)} focuses on {', '.join(titles) or 'the linked notes'}. "
        f"Use this page as the compact retrieval context for this topic."
    )


def layer_metadata(path_parts: Sequence[str]) -> list[str]:
    return [f"- {format_layer_label(index + 1, part)}" for index, part in enumerate(path_parts)]


def relative_category_link(path_parts: Sequence[str], target_parts: Sequence[str]) -> str:
    target = Path(*[slugify(part) for part in target_parts]) / "index.md"
    if not path_parts:
        return normalize_path(Path("categories") / target)
    current = Path(*[slugify(part) for part in path_parts]) / "index.md"
    return normalize_path(Path(os.path.relpath(target, start=current.parent)))


def branch_keywords(path_parts: Sequence[str], notes: list[dict[str, Any]], child_names: list[str]) -> list[str]:
    tokens = Counter()
    for part in path_parts:
        tokens.update(tokenize(part))
    for child in child_names:
        tokens.update(tokenize(child))
    for note in notes:
        tokens.update(tokenize(note["title"]))
        tokens.update(tokenize(note.get("summary", "")))
        for tag in note.get("tags", []):
            tokens.update(tokenize(tag))
    banned = {"layer1", "layer2", "layer3", "notes", "note", *STOPWORDS}
    return [token for token, _ in tokens.most_common(12) if token not in banned][:8]


def flatten_tree_paths(tree: list[dict[str, Any]]) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()

    def visit(node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        path_parts = (*prefix, node["name"])
        if not node["children"]:
            paths.add(path_parts)
            return
        for child in node["children"]:
            visit(child, path_parts)

    for root in tree:
        visit(root, ())
    return paths


def render_category_page(path_parts: Sequence[str], child_names: list[str], notes: list[dict[str, Any]]) -> str:
    depth = len(path_parts)
    lines = [
        f"# {format_layer_label(depth, path_parts[-1])}",
        "",
        "## Layer Path",
        *layer_metadata(path_parts),
        "",
        "## Brief Intro",
        branch_intro(path_parts, notes, child_names),
        "",
        "## Topics Covered",
    ]
    if child_names or notes:
        for child in child_names:
            lines.append(f"- [{format_layer_label(depth + 1, child)}]({relative_category_link(path_parts, [*path_parts, child])})")
        for note in sorted(notes, key=lambda item: item["title"].lower()):
            lines.append(f"- [[{note['source']}]] - {note['title']}")
    else:
        lines.append("- None")
    lines.extend(["", "## References"])
    if notes:
        for note in sorted(notes, key=lambda item: item["title"].lower()):
            tag_text = f" ({' '.join(note['tags'])})" if note.get("tags") else ""
            lines.append(f"- [[{note['source']}]] - {note['summary']}{tag_text}")
    else:
        lines.append("- None")
    lines.extend(["", "## Search Cues"])
    keywords = branch_keywords(path_parts, notes, child_names)
    lines.append(f"- Keywords: {', '.join(keywords)}" if keywords else "- Keywords: none yet")
    return "\n".join(lines).rstrip() + "\n"


def suggest_unindexed_packets(config: WikiConfig, sources: list[str]) -> list[dict[str, Any]]:
    packets = []
    for source in sources:
        if is_system_note(source):
            continue
        source_path = config.notebook_root / source
        if not source_path.exists():
            continue
        packets.append(extract_packet_from_note(source_path, config))
    return packets


def combined_notes(catalog: dict[str, dict[str, Any]], suggested: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {source: dict(note) for source, note in catalog.items()}
    for note in suggested:
        merged.setdefault(note["source"], dict(note))
    return sorted(merged.values(), key=lambda item: item["source"].lower())


def tree_from_paths(paths: set[tuple[str, ...]]) -> list[dict[str, Any]]:
    roots: dict[str, dict[str, Any]] = {}
    for path in sorted(paths):
        current = roots
        for part in path:
            node = current.setdefault(part, {"name": part, "children": {}})
            current = node["children"]

    def materialize(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rendered = []
        for name in sorted(nodes):
            node = nodes[name]
            rendered.append({"name": node["name"], "children": materialize(node["children"])})
        return rendered

    return materialize(roots)


def render_category_tree(tree: list[dict[str, Any]], notes: list[dict[str, Any]]) -> str:
    notes_by_path: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    declared_paths = flatten_tree_paths(tree)
    note_paths = {tuple(note["category_path"]) for note in notes}
    effective = tree_from_paths(declared_paths | note_paths)
    for note in notes:
        notes_by_path[tuple(note["category_path"])].append(note)

    lines = [
        "## Category Tree",
        "",
        "This tree is the classification reference for the wiki. Each branch uses deterministic layer labels so add and search can target a specific depth.",
        "",
    ]
    def render_node(node: dict[str, Any], prefix: tuple[str, ...], depth: int) -> None:
        path_parts = (*prefix, node["name"])
        rel = normalize_path(Path("categories", *[slugify(part) for part in path_parts], "index.md"))
        lines.append(f"{'  ' * (depth - 1)}- layer{depth}: [{node['name']}]({rel})")
        if node["children"]:
            for child in node["children"]:
                render_node(child, path_parts, depth + 1)
            return
        for note in sorted(notes_by_path.get(path_parts, []), key=lambda item: item["source"].lower()):
            lines.append(f"{'  ' * depth}- [[{note['source']}]]")

    for root in effective:
        render_node(root, (), 1)
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rebuild_generated_views(config: WikiConfig, unindexed: list[str] | None = None) -> dict[str, Any]:
    ensure_layout(config)
    catalog = active_catalog(config)
    unindexed = sorted(unindexed or [])
    suggested = suggest_unindexed_packets(config, unindexed)
    skipped_system = [source for source in unindexed if is_system_note(source)]
    tree = parse_category_tree_structure(config.category_tree_path)
    all_notes = combined_notes(catalog, suggested)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    children: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for note in all_notes:
        path = tuple(note["category_path"])
        for depth in range(1, len(path) + 1):
            groups[path[:depth]].append(note)
        for depth in range(1, len(path)):
            children[path[:depth]].add(path[depth])

    valid_pages = set()
    for path_parts, notes in groups.items():
        page = category_page_path(config, path_parts)
        page.parent.mkdir(parents=True, exist_ok=True)
        child_names = sorted(children.get(tuple(path_parts), set()))
        page.write_text(render_category_page(path_parts, child_names, notes), encoding="utf-8")
        valid_pages.add(page.resolve())

    for path in sorted(config.categories_dir.rglob("*.md"), reverse=True):
        if path.resolve() not in valid_pages:
            path.unlink()
    for path in sorted(config.categories_dir.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass

    tree_section = render_category_tree(tree, all_notes) if tree or all_notes else "## Category Tree\n\n- None\n"
    body_section = "## Skipped System Notes\n"
    if skipped_system:
        for source in skipped_system:
            body_section += f"- [[{source}]]\n"
    else:
        body_section += "- None\n"
    combined = "# Wiki Index\n\n" + tree_section + "\n\n---\n\n" + body_section
    config.index_path.write_text(combined, encoding="utf-8")
    return {"catalog": catalog, "category_pages": len(valid_pages), "suggested": suggested, "all_notes": all_notes}


def obsidian_search(config: WikiConfig, query: str) -> list[dict[str, Any]] | None:
    if not shutil.which("obsidian-cli"):
        return None
    try:
        vault_name = config.notebook_root.name
        result = subprocess.run(
            ["obsidian-cli", "search-content", query, "--vault", vault_name],
            cwd=str(config.notebook_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode not in {0, 1}:
        return None
    matches = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matches.append({"backend": "obsidian-cli", "raw": stripped})
    return matches


def rg_search(root: Path, query: str) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["rg", "-n", "-i", query, str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path, _, remainder = line.partition(":")
        line_no, _, text = remainder.partition(":")
        matches.append({"path": path, "line": line_no or "1", "text": text.strip()})
    return matches


def generated_search(config: WikiConfig, query: str) -> list[dict[str, Any]]:
    matches = []
    for item in rg_search(config.generated_root, query):
        try:
            rel = normalize_path(Path(item["path"]).resolve().relative_to(config.generated_root))
        except ValueError:
            rel = item["path"]
        matches.append({"path": rel, "line": item["line"], "text": item["text"]})
    return matches


def query_terms(query: str) -> list[str]:
    return [term for term in tokenize(query) if term not in STOPWORDS]


def rg_content_search(config: WikiConfig, query: str) -> list[dict[str, Any]]:
    matches = []
    generated_root = config.generated_root.resolve()
    for item in rg_search(config.notebook_root, query):
        path = Path(item["path"]).resolve()
        if path == generated_root or generated_root in path.parents:
            continue
        try:
            source = normalize_path(path.relative_to(config.notebook_root))
        except ValueError:
            continue
        matches.append({"source": source, "line": item["line"], "snippet": item["text"], "match_reason": "content"})
    return matches


def tag_search(notes: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = set(query_terms(query))
    if not terms:
        return []
    matches = []
    for note in notes:
        tags = note.get("tags", [])
        tag_tokens = {token.lstrip("#") for tag in tags for token in tokenize(tag)}
        overlap = sorted(terms & tag_tokens)
        if not overlap:
            continue
        matches.append(
            {
                "source": note["source"],
                "tags": tags,
                "snippet": f"Matched tags: {', '.join('#' + token for token in overlap)}",
                "match_reason": "tags",
            }
        )
    return matches


def hierarchy_search(notes: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = set(query_terms(query))
    if not terms:
        return []
    matches = []
    for note in notes:
        hierarchy_tokens = set(tokenize(" ".join(note.get("category_path", []))))
        overlap = sorted(terms & hierarchy_tokens)
        if not overlap:
            continue
        matches.append(
            {
                "source": note["source"],
                "snippet": f"Matched hierarchy terms: {', '.join(overlap)}",
                "match_reason": "hierarchy",
            }
        )
    return matches


def enrich_note_matches(raw_matches: Sequence[dict[str, Any]], note_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in raw_matches:
        source = item.get("source")
        if not source:
            continue
        note = note_lookup.get(source, {})
        enriched = merged.setdefault(
            source,
            {
                "source": source,
                "title": note.get("title", Path(source).stem),
                "hierarchy": note.get("category_path", []),
                "tags": note.get("tags", []),
                "match_reasons": [],
                "snippets": [],
            },
        )
        reason = item.get("match_reason")
        if reason and reason not in enriched["match_reasons"]:
            enriched["match_reasons"].append(reason)
        snippet = item.get("snippet")
        if snippet and snippet not in enriched["snippets"]:
            enriched["snippets"].append(snippet)
        line = item.get("line")
        if line and "line" not in enriched:
            enriched["line"] = line
    return list(merged.values())


def cmd_add(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    if not config.category_tree_path.exists():
        raise SystemExit(f"missing category tree: {config.category_tree_path}")

    packets: list[dict[str, Any]] = []
    if args.packet:
        payload = read_json(Path(args.packet).expanduser().resolve(), None)
        if payload is None:
            raise SystemExit(f"packet file not found: {args.packet}")
        packets.extend(payload if isinstance(payload, list) else [payload])
    for file_arg in args.files:
        packets.append(extract_packet_from_note(Path(file_arg).expanduser().resolve(), config))

    added = []
    for packet in packets:
        normalized = normalize_packet(packet, config)
        source_path = (config.notebook_root / normalized["source"]).resolve()
        if not source_path.exists():
            raise SystemExit(f"missing source note: {normalized['source']}")
        event = {
            "timestamp": utc_now(),
            "action": "add",
            "source_mtime_ns": source_path.stat().st_mtime_ns,
            **normalized,
        }
        append_log_event(config, event)
        added.append(normalized)

    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    artifacts = rebuild_generated_views(config, sorted(current_files - set(active_catalog(config))))
    print(json.dumps({"added": added, "indexed_notes": len(artifacts["catalog"]), "category_pages": artifacts["category_pages"]}, indent=2))
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    if not config.category_tree_path.exists():
        raise SystemExit(f"missing category tree: {config.category_tree_path}")

    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    removed = []
    for source in sorted(set(catalog) - current_files):
        event = {"timestamp": utc_now(), "action": "remove", "source": source, "reason": "source note missing"}
        append_log_event(config, event)
        removed.append(source)

    catalog = active_catalog(config)
    modified = sorted(
        source
        for source, record in catalog.items()
        if source in current_files
        and record.get("source_mtime_ns") is not None
        and source_mtime_ns(config, source) != record.get("source_mtime_ns")
    )
    unindexed = sorted(current_files - set(catalog))
    artifacts = rebuild_generated_views(config, unindexed)
    catalog = artifacts["catalog"]
    unindexed = sorted(current_files - set(catalog))
    print(
        json.dumps(
            {
                "indexed_notes": len(catalog),
                "removed_notes": removed,
                "modified_notes": modified,
                "unindexed_notes": unindexed,
                "category_pages": artifacts["category_pages"],
            },
            indent=2,
        )
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    suggested = suggest_unindexed_packets(config, sorted(current_files - set(catalog)))
    notes = combined_notes(catalog, suggested)
    note_lookup = {note["source"]: note for note in notes}

    note_matches = obsidian_search(config, args.query)
    backend = "obsidian-cli"
    if not note_matches:
        backend = "rg"
        note_matches = []
    content_matches = rg_content_search(config, args.query)
    tag_matches = tag_search(notes, args.query)
    hierarchy_matches = hierarchy_search(notes, args.query)
    generated_matches = generated_search(config, args.query)
    structured_note_matches = enrich_note_matches([*content_matches, *tag_matches, *hierarchy_matches], note_lookup)
    print(
        json.dumps(
            {
                "query": args.query,
                "notes_backend": backend,
                "obsidian_matches": (note_matches or [])[: args.limit],
                "note_matches": structured_note_matches[: args.limit],
                "tag_matches": tag_matches[: args.limit],
                "hierarchy_matches": hierarchy_matches[: args.limit],
                "generated_matches": generated_matches[: args.limit],
            },
            indent=2,
        )
    )
    return 0 if note_matches or structured_note_matches or generated_matches else 1


def cmd_lint(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    issues: list[str] = []
    if not config.category_tree_path.exists():
        issues.append("missing index.md")

    allowed = parse_category_tree(config.category_tree_path)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    for source, record in sorted(catalog.items()):
        if source not in current_files:
            issues.append(f"missing source note: {source}")
            continue
        stored_mtime = record.get("source_mtime_ns")
        if stored_mtime is not None and source_mtime_ns(config, source) != stored_mtime:
            issues.append(f"modified note: {source}")
        if allowed and tuple(record["category_path"]) not in allowed:
            issues.append(f"category not in tree: {source} -> {' -> '.join(record['category_path'])}")

    for source in sorted(current_files - set(catalog)):
        issues.append(f"unindexed note: {source}")

    if args.log:
        event = {"timestamp": utc_now(), "action": "lint", "issues": issues}
        append_log_event(config, event)

    print(json.dumps({"issues": issues, "indexed_notes": len(catalog)}, indent=2))
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight wiki indexer.")
    parser.add_argument("--config", help="Path to wiki config JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add note classifications to the wiki log and rebuild views.")
    add_parser.add_argument("files", nargs="*", help="Source markdown note paths.")
    add_parser.add_argument("--packet", help="Path to a JSON packet or packet list.")
    add_parser.set_defaults(func=cmd_add)

    index_parser = subparsers.add_parser(
        "index",
        aliases=["reconcile"],
        help="Scan source notes, record removals, report modifications, and rebuild generated views.",
    )
    index_parser.set_defaults(func=cmd_reconcile)

    search_parser = subparsers.add_parser("search", help="Search notes via obsidian-cli or rg, plus generated docs.")
    search_parser.add_argument("query", help="Query string.")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum matches per result set.")
    search_parser.set_defaults(func=cmd_search)

    lint_parser = subparsers.add_parser("lint", help="Validate tree coverage and indexed notes.")
    lint_parser.add_argument("--log", action="store_true", help="Append lint findings to log.md.")
    lint_parser.set_defaults(func=cmd_lint)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
