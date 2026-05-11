from __future__ import annotations

import re
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class CategoryNode:
    """One node in the category tree with optional children."""

    name: str
    children: tuple["CategoryNode", ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-safe nested dict."""
        return {
            "name": self.name,
            "children": [child.to_json() for child in self.children],
        }


@dataclass(frozen=True)
class WikiCategoryTree:
    """In-memory category tree parsed from index.md. Pure structure."""

    roots: tuple[CategoryNode, ...]

    @classmethod
    def empty(cls) -> "WikiCategoryTree":
        """Return an empty tree."""
        return cls(())

    @classmethod
    def parse(cls, markdown: str) -> "WikiCategoryTree":
        """Parse `layerN:` bullets from index markdown into a category tree."""
        tree_section = _extract_tree_section(markdown)
        nodes: list[dict[str, Any]] = []
        stack: list[dict[str, Any]] = []
        for raw_line in tree_section.splitlines():
            match = _LAYER_RE.match(raw_line.lstrip())
            if not match:
                continue
            depth = max(1, int(match.group("depth")))
            node: dict[str, Any] = {
                "name": _markdown_label(match.group("label")),
                "children": [],
            }
            if depth == 1:
                nodes.append(node)
                stack = [node]
                continue
            while len(stack) >= depth:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
                stack.append(node)
        return cls(_dict_list_to_nodes(nodes))

    def is_leaf(self, path: CategoryPath) -> bool:
        """Return true if the path exists and has no children."""
        node = self._find_node(path)
        return node is not None and len(node.children) == 0

    def dump(self, format: str = "markdown") -> str:
        """Render the tree as indented markdown bullets or JSON string."""
        if format == "json":
            import json

            return json.dumps(
                [root.to_json() for root in self.roots],
                ensure_ascii=False,
                sort_keys=True,
            )
        lines: list[str] = []
        _dump_markdown(self.roots, 0, lines)
        return "\n".join(lines)

    def children(self, path: CategoryPath | None = None) -> tuple[CategoryNode, ...]:
        """Return direct children of a path, or roots if path is None."""
        if path is None:
            return self.roots
        node = self._find_node(path)
        if node is None:
            return ()
        return node.children

    def contains(self, path: CategoryPath) -> bool:
        """Return true if the path exists in the tree."""
        return self._find_node(path) is not None

    def leaf_paths(self) -> set[CategoryPath]:
        """Return all leaf category paths."""
        paths: set[CategoryPath] = set()

        def visit(node: CategoryNode, prefix: tuple[str, ...]) -> None:
            current = (*prefix, node.name)
            if not node.children:
                paths.add(CategoryPath(current))
            else:
                for child in node.children:
                    visit(child, current)

        for root in self.roots:
            visit(root, ())
        return paths

    def all_paths(self) -> set[CategoryPath]:
        """Return every category path in the tree, including branch nodes."""
        paths: set[CategoryPath] = set()

        def visit(node: CategoryNode, prefix: tuple[str, ...]) -> None:
            current = (*prefix, node.name)
            paths.add(CategoryPath(current))
            for child in node.children:
                visit(child, current)

        for root in self.roots:
            visit(root, ())
        return paths

    def child_names(self) -> dict[CategoryPath, tuple[str, ...]]:
        """Return direct child names keyed by category path."""
        result: dict[CategoryPath, tuple[str, ...]] = {}

        def visit(node: CategoryNode, prefix: tuple[str, ...]) -> None:
            path = CategoryPath((*prefix, node.name))
            result[path] = tuple(
                sorted((child.name for child in node.children), key=str.casefold)
            )
            for child in node.children:
                visit(child, path.parts)

        for root in self.roots:
            visit(root, ())
        return result

    def _find_node(self, path: CategoryPath) -> CategoryNode | None:
        """Locate a node by its full category path."""
        nodes = self.roots
        for part in path.parts:
            found = None
            for node in nodes:
                if node.name == part:
                    found = node
                    break
            if found is None:
                return None
            nodes = found.children
        return found


def category_page_path(categories_dir: Path, path: CategoryPath) -> Path:
    """Return the generated page path for one category path."""
    return categories_dir.joinpath(*path.slug_parts(), "index.md")


# --- private helpers ---


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


def _extract_tree_section(index_text: str) -> str:
    """Extract the generated category tree block from index markdown."""
    if "## Category Tree" not in index_text:
        return ""
    after_header = index_text.split("## Category Tree", 1)[1]
    tree_block, _, _ = after_header.partition("\n---\n")
    return tree_block.strip()


_LAYER_RE = re.compile(r"^\s*-\s*layer(?P<depth>\d+):\s*(?P<label>.+?)\s*$")
_LINK_RE = re.compile(r"^\[(?P<label>.*?)\]\(.*?\)$")


def _markdown_label(value: str) -> str:
    label = value.strip()
    match = _LINK_RE.match(label)
    if match:
        label = match.group("label")
    return label.strip()


def _dict_list_to_nodes(items: list[dict[str, Any]]) -> tuple[CategoryNode, ...]:
    """Convert the raw parsed dict tree into frozen CategoryNode tuples."""
    return tuple(
        CategoryNode(
            name=str(item["name"]),
            children=_dict_list_to_nodes(item.get("children", [])),
        )
        for item in items
    )


def _dump_markdown(
    nodes: tuple[CategoryNode, ...], depth: int, lines: list[str]
) -> None:
    """Recursively render nodes as indented markdown bullets."""
    indent = "  " * depth
    for node in nodes:
        lines.append(f"{indent}- {node.name}")
        _dump_markdown(node.children, depth + 1, lines)
