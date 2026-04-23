from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, order=True)
class CategoryPath:
    """Normalized category lineage such as `Computer Science > AI Systems`."""

    parts: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> "CategoryPath":
        """Parse a `>`-delimited category string into canonical path parts."""
        parts = tuple(part.strip() for part in value.split(">") if part.strip())
        if not parts:
            raise ValueError("category must not be empty")
        return cls(parts)

    def display(self) -> str:
        """Render the path in packet/frontmatter display form."""
        return " > ".join(self.parts)

    def layer_labels(self) -> tuple[str, ...]:
        """Render prompt-friendly labels such as `layer1: Computer Science`."""
        return tuple(
            f"layer{index}: {part}" for index, part in enumerate(self.parts, start=1)
        )

    def slug_parts(self) -> tuple[str, ...]:
        """Render filesystem-safe path parts for generated category pages."""
        return tuple(_slugify(part) for part in self.parts)

    def to_json(self) -> str:
        """Serialize category paths as their display string."""
        return self.display()


def _slugify(value: str) -> str:
    """Make a stable lowercase slug for category page paths."""
    chars: list[str] = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")


def category_page_path(categories_dir: Path, path: CategoryPath) -> Path:
    """Return the generated page path for one category path."""
    return categories_dir.joinpath(*path.slug_parts(), "index.md")


def extract_tree_section(index_text: str) -> str:
    """Extract the generated category tree block from index markdown."""
    if "## Category Tree" not in index_text:
        return ""
    after_header = index_text.split("## Category Tree", 1)[1]
    tree_block, _, _ = after_header.partition("\n---\n")
    return tree_block.strip()


def parse_category_tree(index_text: str) -> list[dict[str, Any]]:
    """Parse `layerN:` bullets from index markdown into a nested tree."""
    tree: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for raw_line in extract_tree_section(index_text).splitlines():
        match = _LAYER_RE.match(raw_line.lstrip())
        if not match:
            continue
        depth = max(1, int(match.group("depth")))
        node = {"name": _markdown_label(match.group("label")), "children": []}
        if depth == 1:
            tree.append(node)
            stack = [node]
            continue
        while len(stack) >= depth:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
            stack.append(node)
    return tree


def leaf_paths(tree: list[dict[str, Any]]) -> set[CategoryPath]:
    """Return approved leaf category paths."""
    paths: set[CategoryPath] = set()

    def visit(node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        path = (*prefix, str(node["name"]))
        children = node.get("children", [])
        if not children:
            paths.add(CategoryPath(path))
            return
        for child in children:
            visit(child, path)

    for root in tree:
        visit(root, ())
    return paths


def all_paths(tree: list[dict[str, Any]]) -> set[CategoryPath]:
    """Return every category path in the tree, including branch nodes."""
    paths: set[CategoryPath] = set()

    def visit(node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        path = (*prefix, str(node["name"]))
        paths.add(CategoryPath(path))
        for child in node.get("children", []):
            visit(child, path)

    for root in tree:
        visit(root, ())
    return paths


def child_names(tree: list[dict[str, Any]]) -> dict[CategoryPath, tuple[str, ...]]:
    """Return direct child names keyed by category path."""
    children: dict[CategoryPath, tuple[str, ...]] = {}

    def visit(node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        path = CategoryPath((*prefix, str(node["name"])))
        node_children = tuple(str(child["name"]) for child in node.get("children", []))
        children[path] = tuple(sorted(node_children, key=str.casefold))
        for child in node.get("children", []):
            visit(child, path.parts)

    for root in tree:
        visit(root, ())
    return children


def tree_to_json(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a JSON-safe copy of a category tree."""
    return [
        {"name": str(node["name"]), "children": tree_to_json(node.get("children", []))}
        for node in tree
    ]


def tree_to_markdown(tree: list[dict[str, Any]]) -> str:
    """Render a category tree as indented Markdown bullets."""
    lines: list[str] = []

    def visit(nodes: list[dict[str, Any]], depth: int) -> None:
        indent = "  " * depth
        for node in nodes:
            lines.append(f"{indent}- {node['name']}")
            visit(node.get("children", []), depth + 1)

    visit(tree, 0)
    return "\n".join(lines)


_LAYER_RE = re.compile(r"^\s*-\s*layer(?P<depth>\d+):\s*(?P<label>.+?)\s*$")
_LINK_RE = re.compile(r"^\[(?P<label>.*?)\]\(.*?\)$")


def _markdown_label(value: str) -> str:
    label = value.strip()
    match = _LINK_RE.match(label)
    if match:
        label = match.group("label")
    return label.strip()
