from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from wikicli.config import WikiConfig, ensure_layout
from wikicli.core import (
    LAYER_BULLET_RE,
    STOPWORDS,
    active_catalog,
    extract_packet_from_note,
    format_layer_label,
    is_system_note,
    markdown_label,
    normalize_path,
    safe_title,
    slugify,
    strip_layer_label,
    summarize_text,
    tokenize,
)


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
        stripped = raw_line.rstrip().lstrip()
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
    config.index_path.write_text("# Wiki Index\n\n" + tree_section + "\n\n---\n\n" + body_section, encoding="utf-8")
    return {"catalog": catalog, "category_pages": len(valid_pages), "suggested": suggested, "all_notes": all_notes}
