from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from wikicli.classify import extract_packet_from_note
from wikicli.config import WikiConfig
from wikicli.fs import ensure_layout, normalize_path
from wikicli.log import active_catalog, is_system_note
from wikicli.text import (
    STOPWORDS,
    format_layer_label,
    safe_title,
    slugify,
    summarize_text,
    tokenize,
)
from wikicli.tree import flatten_tree_paths, parse_category_tree_structure, tree_from_paths


def category_page_path(config: WikiConfig, path_parts: Sequence[str]) -> Path:
    """
    Determine the file path for a category index page.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        path_parts (Sequence[str]): The category layers.
        
    Returns:
        Path: The absolute path to the category's index.md file.
    """
    current = config.categories_dir
    for part in path_parts:
        current = current / slugify(part)
    return current / "index.md"


def branch_intro(path_parts: Sequence[str], notes: list[dict[str, Any]], child_names: list[str]) -> str:
    """
    Generate a dynamic introduction paragraph for a category page.
    
    Args:
        path_parts (Sequence[str]): The category layers.
        notes (list[dict[str, Any]]): A list of notes in this category.
        child_names (list[str]): A list of subcategory names.
        
    Returns:
        str: A synthesized introductory text block.
    """
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
    """
    Format the category lineage as a list of layer strings.
    
    Args:
        path_parts (Sequence[str]): The category layers.
        
    Returns:
        list[str]: A list of formatted bullet point strings.
    """
    return [f"- {format_layer_label(index + 1, part)}" for index, part in enumerate(path_parts)]


def relative_category_link(path_parts: Sequence[str], target_parts: Sequence[str]) -> str:
    """
    Compute a relative path link from one category page to another.
    
    Args:
        path_parts (Sequence[str]): The source category path.
        target_parts (Sequence[str]): The destination category path.
        
    Returns:
        str: A relative URL suitable for a markdown link.
    """
    target = Path(*[slugify(part) for part in target_parts]) / "index.md"
    if not path_parts:
        return normalize_path(Path("categories") / target)
    current = Path(*[slugify(part) for part in path_parts]) / "index.md"
    return normalize_path(Path(os.path.relpath(target, start=current.parent)))


def branch_keywords(path_parts: Sequence[str], notes: list[dict[str, Any]], child_names: list[str]) -> list[str]:
    """
    Extract the most common keywords for a category branch.
    
    Args:
        path_parts (Sequence[str]): The category layers.
        notes (list[dict[str, Any]]): Notes within the category.
        child_names (list[str]): Subcategories.
        
    Returns:
        list[str]: A list of top keywords for search cues.
    """
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


def render_category_page(path_parts: Sequence[str], child_names: list[str], notes: list[dict[str, Any]]) -> str:
    """
    Generate the markdown content for a category index page.
    
    Args:
        path_parts (Sequence[str]): The category layers.
        child_names (list[str]): Subcategories.
        notes (list[dict[str, Any]]): Notes within the category.
        
    Returns:
        str: The full markdown document string.
    """
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
    """
    Generate inferred packets for a list of unindexed source notes.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        sources (list[str]): A list of relative paths for unindexed notes.
        
    Returns:
        list[dict[str, Any]]: A list of generated note metadata packets.
    """
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
    """
    Merge the active catalog with suggested unindexed packets.
    
    Args:
        catalog (dict[str, dict[str, Any]]): The confirmed, indexed notes.
        suggested (list[dict[str, Any]]): The inferred packets.
        
    Returns:
        list[dict[str, Any]]: A combined and sorted list of all notes.
    """
    merged = {source: dict(note) for source, note in catalog.items()}
    for note in suggested:
        merged.setdefault(note["source"], dict(note))
    return sorted(merged.values(), key=lambda item: item["source"].lower())


def render_category_tree(tree: list[dict[str, Any]], notes: list[dict[str, Any]]) -> str:
    """
    Render the combined category tree and note mappings as markdown.
    
    Args:
        tree (list[dict[str, Any]]): The pre-existing category tree.
        notes (list[dict[str, Any]]): All valid notes mapped to their paths.
        
    Returns:
        str: The rendered '## Category Tree' markdown block.
    """
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
    """
    Reconstruct the entire wiki generated folder layout.
    
    This rewrites the main index.md, all nested category pages, and removes
    orphaned category pages.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        unindexed (list[str] | None): Relative paths to notes not yet indexed.
        
    Returns:
        dict[str, Any]: A dictionary of summary metrics regarding the rebuild.
    """
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
