from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from wikicli.fs import normalize_path
from wikicli.text import LAYER_BULLET_RE, NOTE_LINK_RE, markdown_label, strip_layer_label


def extract_tree_section(path: Path) -> str | None:
    """
    Extract the '## Category Tree' section from an index markdown file.
    
    Args:
        path (Path): The path to the index.md file.
        
    Returns:
        str | None: The raw text of the tree section, or None if not found.
    """
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if "## Category Tree" not in text or "\n---\n" not in text:
        return None
    after_header = text.split("## Category Tree", 1)[1]
    tree_block, _, _ = after_header.partition("\n---\n")
    return tree_block.strip()


def parse_allowed_category_paths(path: Path) -> set[tuple[str, ...]]:
    """
    Parse valid full category paths from the index tree.
    
    Reads the category tree and returns all defined paths down to at least depth 2.
    
    Args:
        path (Path): The path to the index.md file.
        
    Returns:
        set[tuple[str, ...]]: A set of category path tuples.
    """
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
    """
    Parse the assigned notes from the category tree index.
    
    Args:
        path (Path): The path to the index.md file.
        
    Returns:
        dict[str, list[str]]: A dictionary mapping note paths to their category path.
    """
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


def parse_category_tree_structure(path: Path) -> list[dict[str, Any]]:
    """
    Parse the category tree text into a nested hierarchical structure.
    
    Args:
        path (Path): The path to the index.md file.
        
    Returns:
        list[dict[str, Any]]: A list of root node dictionaries containing 'name' and 'children'.
    """
    text = extract_tree_section(path)
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
    """
    Extract leaf node category paths from the category tree.
    
    Args:
        path (Path): The path to the index.md file.
        
    Returns:
        set[tuple[str, ...]]: A set of category path tuples that represent leaf nodes.
    """
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


def flatten_tree_paths(tree: list[dict[str, Any]]) -> set[tuple[str, ...]]:
    """
    Convert a nested tree structure into a flat set of path tuples.
    
    Args:
        tree (list[dict[str, Any]]): The hierarchical tree structure.
        
    Returns:
        set[tuple[str, ...]]: A set of leaf path tuples.
    """
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


def tree_from_paths(paths: set[tuple[str, ...]]) -> list[dict[str, Any]]:
    """
    Convert a flat set of path tuples back into a nested tree structure.
    
    Args:
        paths (set[tuple[str, ...]]): A set of path tuples.
        
    Returns:
        list[dict[str, Any]]: A hierarchical list of dictionaries.
    """
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
