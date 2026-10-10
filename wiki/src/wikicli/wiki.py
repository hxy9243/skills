from __future__ import annotations

import json
import os
import re
import tempfile
import stat
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .category import (
    CategoryPath,
    WikiCategoryTree,
    category_page_path,
)
from .config import WikiConfig
from .notebook import Notebook, Note, NoteMetadata, NewNote


class IssueType(str, Enum):
    NOTE_MISSING = "note_missing"
    NOTE_MODIFIED = "note_modified"
    UNINDEXED = "unindexed"
    INVALID_CATEGORY = "invalid_category"
    EMPTY_CATEGORY = "empty_category"
    ORPHAN_PAGE = "orphan_page"


@dataclass(frozen=True)
class Issue:
    """Structured problem report returned in command JSON instead of stderr text."""

    code: IssueType | str
    message: str
    severity: str = "error"
    source: str | None = None
    path: str | None = None
    line: int | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize for stable CLI JSON, omitting unset optional fields."""
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class CatalogEntry:
    """Active catalog record after replaying add/remove log events."""

    source: str
    title: str
    summary: str
    category: str
    tags: tuple[str, ...]
    search_terms: tuple[str, ...] = ()
    source_mtime_ns: int | None = None
    updated_at: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize catalog entries for command responses."""
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "category": self.category,
            "tags": list(self.tags),
            "search_terms": list(self.search_terms),
            "source_mtime_ns": self.source_mtime_ns,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class SearchResult:
    """Normalized search hit from source notes, generated pages, or metadata."""

    source: str
    title: str
    hierarchy: str
    score: int
    match_reasons: tuple[str, ...]
    snippets: tuple[str, ...]
    tags: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        """Serialize tuple fields as JSON arrays for CLI responses."""
        data = asdict(self)
        data["match_reasons"] = list(self.match_reasons)
        data["snippets"] = list(self.snippets)
        data["tags"] = list(self.tags)
        return data


class WikiIndex:
    """Generated wiki state: category tree, catalog, listings, search, and lint."""

    def __init__(self, config: WikiConfig, notebook: Notebook) -> None:
        self.config = config
        self.notebook = notebook

    # --- tree ---

    def read_tree(self) -> WikiCategoryTree:
        """Parse the approved category tree from `index.md`."""
        if not self.config.index_path.exists():
            return WikiCategoryTree.empty()
        return WikiCategoryTree.parse(
            self.config.index_path.read_text(encoding="utf-8")
        )

    def tree(self, *, depth: int | None = None) -> dict[str, Any]:
        """Return a deterministic category tree with note counts and leaf notes."""
        tree = self.read_tree()
        grouped = self._grouped_catalog_entries()

        def render_node(node: Any, prefix: tuple[str, ...]) -> dict[str, Any]:
            path = CategoryPath((*prefix, node.name))
            notes = sorted(grouped.get(path, ()), key=lambda item: item.source.casefold())
            current_depth = len(path.parts)
            include_children = depth is None or current_depth < depth
            children = [render_node(child, path.parts) for child in node.children] if include_children else []
            is_leaf_view = not node.children or not include_children
            page_path = category_page_path(self.config.categories_dir, path)
            page_rel = str(page_path.relative_to(self.config.notebook_root))
            return {
                "name": node.name,
                "path": page_rel,
                "category": path.display(),
                "depth": current_depth,
                "page": page_rel,
                "note_count": len(notes),
                "leaf": len(node.children) == 0,
                "notes": [
                    {
                        "source": entry.source,
                        "title": entry.title,
                        "summary": entry.summary,
                    }
                    for entry in notes
                ] if is_leaf_view else [],
                "children": children,
            }

        roots = [render_node(root, ()) for root in tree.roots]
        return {"roots": roots}

    def add_category(self, path: str | CategoryPath) -> WikiCategoryTree:
        """Add a category path to the tree in index.md."""
        if isinstance(path, str):
            path = CategoryPath.parse(path)
        self._preflight(extra_paths={CategoryPath(path.parts[:depth]) for depth in range(1, len(path.parts) + 1)})
        self._ensure_layout()
        tree = self.read_tree()
        if tree.contains(path):
            return tree

        paths = set(tree.all_paths())
        for depth in range(1, len(path.parts) + 1):
            paths.add(CategoryPath(path.parts[:depth]))

        original = _read_text(self.config.index_path)
        # Append a complete lineage; the parser merges repeated ancestors.
        # Never replace the user-approved tree or its surrounding annotations.
        lineage = {CategoryPath(path.parts[:depth]) for depth in range(1, len(path.parts) + 1)}
        tree_block = _render_tree_block(self.config.categories_dir, lineage)
        updated = _append_tree_block(original, tree_block)
        _write_if_changed(self.config.index_path, updated, expected=original)
        return self.read_tree()

    # --- catalog ---

    def catalog(self) -> dict[str, CatalogEntry]:
        """Replay add/remove log events into the current active catalog."""
        events, _ = self._read_events()
        result: dict[str, CatalogEntry] = {}
        for event in events:
            source = event.get("source")
            if not isinstance(source, str):
                continue
            try:
                source = Notebook.normalize_source(source)
            except ValueError:
                continue
            action = event.get("action")
            if action == "remove":
                result.pop(source, None)
                continue
            if action != "add":
                continue
            title = str(event.get("title") or Path(source).stem)
            summary = str(event.get("summary") or "")
            category = str(
                event.get("category") or event.get("category_path") or ""
            )
            if not category:
                continue
            try:
                category = CategoryPath.parse(category).display()
            except ValueError:
                continue
            tags = _string_tuple(event.get("tags", ()))
            search_terms = _string_tuple(event.get("search_terms", ()))
            mtime = event.get("source_mtime_ns")
            result[source] = CatalogEntry(
                source=source,
                title=title,
                summary=summary,
                category=category,
                tags=tags,
                search_terms=search_terms,
                source_mtime_ns=mtime if isinstance(mtime, int) else None,
                updated_at=str(event.get("timestamp") or ""),
            )
        return dict(sorted(result.items(), key=lambda item: item[0].casefold()))

    # --- listing ---

    def list(
        self,
        category: str | CategoryPath | None = None,
        *,
        recursive: bool = False,
        include_body: bool = False,
    ) -> dict[str, Any]:
        """List subcategories and catalog entries at a category level.

        Without ``--recursive``, behaves like ``ls``:
        - Shows direct child categories of the given path.
        - Shows entries whose category exactly matches the given path.

        With ``--recursive``, returns all entries under the subtree.

        Returns a dict with ``subcategories`` (list of child category names)
        and ``entries`` (list of CatalogEntry).
        """
        all_entries = list(self.catalog().values())
        tree = self.read_tree()

        if category is not None:
            cat_str = (
                category.display()
                if isinstance(category, CategoryPath)
                else category
            )
        else:
            cat_str = None

        if recursive:
            # Flat list of everything under this subtree (or everything).
            if cat_str is not None:
                entries = [
                    e
                    for e in all_entries
                    if e.category == cat_str
                    or e.category.startswith(cat_str + " > ")
                ]
            else:
                entries = all_entries
            return {"subcategories": [], "entries": entries}

        # Non-recursive: show direct children + entries at this exact level.
        try:
            cat_path = CategoryPath.parse(cat_str) if cat_str else None
        except ValueError:
            cat_path = None

        children = tree.children(cat_path)
        subcategories = [node.name for node in children]
        entries = [e for e in all_entries if e.category == cat_str] if cat_str else []
        return {"subcategories": subcategories, "entries": entries}

    # --- mutations ---

    def add_note(
        self, note: NewNote, *, allow_undeclared: bool = False
    ) -> dict[str, Any]:
        """Apply an accepted new note: update frontmatter, append log, render views."""
        source_path = self.notebook._write_path(note.source)
        proposed = {CategoryPath(note.category.parts[:depth]) for depth in range(1, len(note.category.parts) + 1)} if allow_undeclared else set()
        self._preflight(extra_paths=proposed)
        self.notebook.discover()
        # Validate all source metadata and category conflicts before any mutation.
        NoteMetadata.add_property(_read_text(source_path), "category", note.category.display())
        previous = self.catalog().get(note.source)
        if previous and previous.category != note.category.display():
            raise ValueError("existing catalog category differs; explicit recategorization is required")
        if previous:
            note = replace(note,
                title=previous.title,
                summary=_merge_text(previous.summary, note.summary),
                tags=tuple(dict.fromkeys((*previous.tags, *note.tags))),
                search_terms=tuple(dict.fromkeys((*previous.search_terms, *note.search_terms))),
            )
        self._ensure_layout()
        if allow_undeclared and not self.read_tree().contains(note.category):
            self.add_category(note.category)
        source_path = self.notebook._write_path(note.source)
        changed_files: list[str] = []
        if NoteMetadata.write_category(source_path, note.category.display()):
            changed_files.append(note.source)
        event_needed = not previous or any((
            previous.title != note.title, previous.summary != note.summary,
            previous.tags != note.tags, previous.search_terms != note.search_terms,
            previous.source_mtime_ns != source_path.stat().st_mtime_ns,
        ))
        if event_needed:
            self._append_event(
                {
                    "timestamp": _utc_now(),
                    "action": "add",
                    "title": note.title,
                    "summary": note.summary,
                    "category": note.category.display(),
                    "tags": list(note.tags),
                    "search_terms": list(note.search_terms),
                    "source": note.source,
                    "source_mtime_ns": source_path.stat().st_mtime_ns,
                },
            )
            changed_files.append(str(self.config.log_path.relative_to(self.config.notebook_root)))
        rebuild = self._rebuild_generated()
        changed_files.extend(rebuild["changed_files"])
        catalog = self.catalog()
        return {
            "packet": note.to_json(),
            "changed_files": sorted(set(changed_files)),
            "indexed_count": len(catalog),
            "category_pages": rebuild["category_pages"],
            "orphan_pages": rebuild["orphan_pages"],
        }

    def index(self) -> dict[str, Any]:
        """Scan notebook state, record missing catalog entries, and regenerate views."""
        self._preflight()
        # Parse every source before layout, event, or generated-page writes.
        notes = {note.source: note for note in self.notebook.discover()}
        self._ensure_layout()
        catalog = self.catalog()
        removed: list[str] = []
        for source in sorted(set(catalog) - set(notes), key=str.casefold):
            # Excluded or out-of-scope notes still exist; do not remove their catalog history.
            if self.notebook.resolve(source).exists():
                continue
            self._append_event(
                {
                    "timestamp": _utc_now(),
                    "action": "remove",
                    "source": source,
                    "reason": "source note missing",
                },
            )
            removed.append(source)
        catalog = self.catalog()
        modified = sorted(
            source
            for source, entry in catalog.items()
            if source in notes and self._entry_is_stale(entry, notes[source])
        )
        for source in modified:
            note = notes[source]
            entry = catalog[source]
            metadata = NoteMetadata.read(note.path)
            summary = _merge_text(entry.summary, str(metadata.frontmatter.get("summary") or ""))
            self._append_event(
                {
                    "timestamp": _utc_now(),
                    "action": "add",
                    "title": entry.title,
                    "summary": summary,
                    "category": self._resolved_category(note, entry),
                    "tags": list(dict.fromkeys((*entry.tags, *note.tags))),
                    "search_terms": list(entry.search_terms),
                    "source": source,
                    "source_mtime_ns": note.path.stat().st_mtime_ns,
                }
            )
        catalog = self.catalog()
        unindexed = sorted(set(notes) - set(catalog), key=str.casefold)
        rebuild = self._rebuild_generated(unindexed=unindexed)
        return {
            "indexed_count": len(catalog),
            "removed_notes": removed,
            "modified_notes": modified,
            "unindexed_notes": unindexed,
            "category_pages": rebuild["category_pages"],
            "changed_files": rebuild["changed_files"],
            "orphan_pages": rebuild["orphan_pages"],
        }

    # --- search ---

    def find(
        self,
        query: str | None = None,
        *,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> list[SearchResult]:
        """Return ranked search results for a query."""
        catalog = self.catalog()

        # Tag-only filtering
        if tags:
            requested = set(tags)
            catalog = {
                s: e
                for s, e in catalog.items()
                if requested & set(e.tags)
            }

        if query:
            terms = Notebook.tokenize(query)
        else:
            terms = ()

        if not terms and not tags:
            return []
        if limit <= 0:
            return []

        results: list[SearchResult] = []
        for entry in catalog.values():
            score = 0
            reasons: list[str] = []
            snippets: list[str] = []

            if terms:
                haystacks = {
                    "title": entry.title,
                    "summary": entry.summary,
                    "hierarchy": entry.category,
                    "tags": " ".join(entry.tags),
                    "search_terms": " ".join(entry.search_terms),
                }
                for reason, text in haystacks.items():
                    overlap = _overlap(terms, text)
                    if not overlap:
                        continue
                    score += _weight(reason) * len(overlap)
                    reasons.append(reason)
                    if reason in {"title", "summary", "hierarchy"}:
                        snippets.append(
                            Notebook.snippet_around(text, overlap)
                        )
                try:
                    note = self.notebook.read(entry.source)
                except OSError:
                    note = None
                if note is not None:
                    body_text = Notebook.clean_body_text(note.body)
                    overlap = _overlap(terms, body_text)
                    if overlap:
                        score += len(overlap)
                        reasons.append("content")
                        snippets.append(
                            Notebook.snippet_around(body_text, overlap)
                        )
            else:
                # Tag-only search — score by tag match count
                score = len(set(tags) & set(entry.tags))
                reasons.append("tags")

            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source=entry.source,
                    title=entry.title,
                    hierarchy=entry.category,
                    score=score,
                    match_reasons=tuple(dict.fromkeys(reasons)),
                    snippets=tuple(dict.fromkeys(snippets))[:3],
                    tags=entry.tags,
                )
            )
        results.sort(key=lambda item: (-item.score, item.source.casefold()))
        return results[:limit]

    # --- checks ---

    def lint(self) -> tuple[Any, ...]:
        """Run read-only workspace integrity checks."""
        issues: list[Issue] = []

        notes = {note.source: note for note in self.notebook.discover()}
        catalog = self.catalog()
        tree = self.read_tree()
        leaf_paths = tree.leaf_paths()
        catalog_categories = {entry.category for entry in catalog.values()}

        for source, entry in catalog.items():
            if source not in notes:
                issues.append(
                    Issue(
                        IssueType.NOTE_MISSING,
                        f"indexed source note is missing: {source}",
                        source=source,
                    )
                )
                continue
            if self._entry_is_stale(entry, notes[source]):
                issues.append(
                    Issue(
                        IssueType.NOTE_MODIFIED,
                        f"indexed source note has changed: {source}",
                        severity="warning",
                        source=source,
                    )
                )
            resolved_category = self._resolved_entry_category(source, entry, tree=tree)
            if resolved_category is None:
                issues.append(
                    Issue(
                        IssueType.INVALID_CATEGORY,
                        f"catalog category is invalid: {entry.category}",
                        source=source,
                    )
                )
                continue
            if not tree.contains(resolved_category):
                issues.append(
                    Issue(
                        IssueType.INVALID_CATEGORY,
                        f"catalog category is not present in the approved tree: {resolved_category.display()}",
                        source=source,
                    )
                )

        for source in sorted(set(notes) - set(catalog), key=str.casefold):
            issues.append(
                Issue(
                    IssueType.UNINDEXED,
                    f"source note is not indexed: {source}",
                    severity="warning",
                    source=source,
                )
            )

        for category in sorted(leaf_paths, key=lambda item: item.display().casefold()):
            if category.display() in catalog_categories:
                continue
            issues.append(
                Issue(
                    IssueType.EMPTY_CATEGORY,
                    f"leaf category has no indexed notes: {category.display()}",
                    severity="warning",
                    path=str(category_page_path(self.config.categories_dir, category)),
                )
            )
        valid = {category_page_path(self.config.categories_dir, category).resolve() for category in tree.all_paths()}
        for page in sorted(self.config.categories_dir.rglob("*.md")):
            if page.resolve() not in valid:
                issues.append(Issue(IssueType.ORPHAN_PAGE, "page is outside the current tree; retained unchanged", severity="warning", path=str(page.relative_to(self.config.notebook_root))))
        return tuple(issues)

    # --- private helpers ---

    def _preflight(self, *, extra_paths: set[CategoryPath] | None = None) -> None:
        """Reject ambiguous or unsafe inputs before making any workspace changes."""
        targets = [self.config.generated_root, self.config.index_path, self.config.log_path]
        seen: dict[Path, CategoryPath] = {}
        for category in self.read_tree().all_paths() | (extra_paths or set()):
            target = category_page_path(self.config.categories_dir, category)
            if target in seen and seen[target] != category:
                raise ValueError(f"category paths collide: {seen[target].display()} and {category.display()}")
            if any(not part for part in category.slug_parts()):
                raise ValueError(f"category has an empty filesystem name: {category.display()}")
            seen[target] = category
            targets.append(target)
        for target in targets:
            _check_write_path(target, self.config.notebook_root)
            if target != self.config.generated_root and target.exists() and not target.is_file():
                raise ValueError(f"expected a file, found another object: {target}")
            if any(parent.exists() and not parent.is_dir() for parent in target.parents):
                raise ValueError(f"output parent is not a directory: {target}")
            if target == self.config.generated_root and target.exists() and not target.is_dir():
                raise ValueError(f"wiki root is not a directory: {target}")
            if target.is_file() and target.suffix == ".md":
                NoteMetadata.parse(_read_text(target))
        # Rebuild also reads cataloged sources outside today's include roots.
        self._grouped_catalog_entries()
        # Even orphaned pages are user content: reject invalid metadata, never delete.
        for target in self.config.categories_dir.rglob("*.md"):
            _check_write_path(target, self.config.notebook_root)
            NoteMetadata.parse(_read_text(target))

    def _ensure_layout(self) -> None:
        """Create the generated wiki directory and required files."""
        self.config.generated_root.mkdir(parents=True, exist_ok=True)
        self.config.categories_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.log_path.exists():
            _create_if_missing(self.config.log_path, "# Wiki Log\n\n")
        if not self.config.index_path.exists():
            _create_if_missing(self.config.index_path,
                "# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n")

    def _append_event(self, event: dict[str, Any]) -> None:
        """Append one JSON event to `log.md`."""
        self._ensure_layout()
        _check_write_path(self.config.log_path, self.config.notebook_root)
        existing = _read_text(self.config.log_path)
        newline = "\r\n" if "\r\n" in existing else "\n"
        with self.config.log_path.open("a", encoding="utf-8", newline="") as handle:
            if existing and not existing.endswith(("\n", "\r")):
                handle.write(newline)
            handle.write(f"- {json.dumps(event, ensure_ascii=True, sort_keys=True)}{newline}")

    def _rebuild_generated(self, unindexed: list[str] | None = None) -> dict[str, Any]:
        """Rewrite index, category pages, and homepage with lightweight metadata."""
        tree = self.read_tree()
        child_map = tree.child_names()
        all_paths = sorted(tree.all_paths(), key=lambda item: (len(item.parts), item.display().casefold()))
        grouped = self._grouped_catalog_entries()

        valid_pages: set[Path] = set()
        changed_files: list[str] = []
        for path in all_paths:
            page = category_page_path(self.config.categories_dir, path)
            page.parent.mkdir(parents=True, exist_ok=True)
            original = _read_text(page) if page.exists() else None
            content = self._render_category_page(
                path,
                child_map.get(path, ()),
                grouped.get(path, ()),
            )
            if _write_if_changed(page, content, expected=original):
                changed_files.append(str(page.relative_to(self.config.notebook_root)))
            valid_pages.add(page.resolve())

        orphan_pages = sorted(
            str(path.relative_to(self.config.notebook_root))
            for path in self.config.categories_dir.rglob("*.md")
            if path.resolve() not in valid_pages
        )

        original_index = _read_text(self.config.index_path)
        index_content = self._render_index(tree, grouped, unindexed or [])
        if _write_if_changed(self.config.index_path, index_content, expected=original_index):
            changed_files.append(str(self.config.index_path.relative_to(self.config.notebook_root)))

        return {
            "category_pages": len(valid_pages),
            "changed_files": changed_files,
            "orphan_pages": orphan_pages,
        }

    def _render_index(
        self,
        tree: WikiCategoryTree,
        grouped: dict[CategoryPath, list[CatalogEntry]],
        unindexed: list[str],
    ) -> str:
        """Add missing navigation without replacing the approved tree or manual text."""
        original = _read_text(self.config.index_path) if self.config.index_path.exists() else "# Wiki Index\n"
        entries = []
        for category in sorted(grouped, key=lambda item: item.display().casefold()):
            for entry in grouped[category]:
                marker = f"[[{entry.source}]]"
                if marker not in original and all(marker not in row for row in entries):
                    entries.append(f"- {marker} — {entry.category}")
        text = _append_section_items(original, "Indexed Notes", entries)
        return _append_section_items(text, "Skipped System Notes", [
            f"- [[{source}]]" for source in unindexed if f"[[{source}]]" not in text
        ])

    def _append_tree_lines(
        self,
        lines: list[str],
        node: Any,
        prefix: tuple[str, ...],
        grouped: dict[CategoryPath, list[CatalogEntry]],
    ) -> None:
        """Render one category subtree into the index."""
        current = CategoryPath((*prefix, node.name))
        depth = len(current.parts)
        indent = "  " * (depth - 1)
        rel = category_page_path(self.config.categories_dir, current).relative_to(self.config.generated_root).as_posix()
        lines.append(f"{indent}- layer{depth}: [{node.name}]({rel})")
        for child in node.children:
            self._append_tree_lines(lines, child, current.parts, grouped)
        if not node.children:
            for entry in sorted(grouped.get(current, ()), key=lambda item: item.source.casefold()):
                lines.append(f"{indent}  - [[{entry.source}]]")

    def _render_category_page(
        self,
        path: CategoryPath,
        child_names: tuple[str, ...],
        notes: tuple[CatalogEntry, ...] | list[CatalogEntry],
    ) -> str:
        """Add missing metadata/navigation while preserving every existing byte."""
        page_path = category_page_path(self.config.categories_dir, path)
        notes = list(notes)
        timestamp = _utc_now()
        frontmatter = {
            "category": path.display(), "created": timestamp, "modified": timestamp,
            "summary": "", "tags": ["#wiki", "#synthesis"],
            "wiki_role": "synthesis", "wiki_depth": len(path.parts),
            "wiki_kind": "leaf" if not child_names else "branch",
            "wiki_note_count": len(notes), "wiki_child_count": len(child_names),
            "wiki_status": "empty" if not notes else "active",
        }
        if len(path.parts) > 1:
            parent = CategoryPath(path.parts[:-1])
            rel = Path(os.path.relpath(category_page_path(self.config.categories_dir, parent), start=page_path.parent)).as_posix()
            frontmatter["parent"] = f"[[{rel}|{parent.parts[-1]}]]"
        if page_path.exists():
            text = _read_text(page_path)
            existing = NoteMetadata.parse(text)
            for key, value in frontmatter.items():
                if key not in existing.frontmatter:
                    text = NoteMetadata.add_property(text, key, value)
        else:
            text = NoteMetadata(frontmatter, f"# layer{len(path.parts)}: {path.parts[-1]}\n\n## Synthesis\n\n").render()
        children = []
        for child in child_names:
            child_path = CategoryPath((*path.parts, child))
            rel = Path(os.path.relpath(category_page_path(self.config.categories_dir, child_path), start=page_path.parent)).as_posix()
            if f"]({rel})" not in text:
                children.append(f"- [layer{len(path.parts) + 1}: {child}]({rel})")
        text = _append_section_items(text, "Subcategories", children)
        references = [f"- [[{entry.source}]] - {entry.summary}" for entry in sorted(notes, key=lambda item: item.title.casefold()) if f"[[{entry.source}]]" not in text]
        return _append_section_items(text, "References", references)

    def _grouped_catalog_entries(self) -> dict[CategoryPath, list[CatalogEntry]]:
        """Group active catalog entries under every ancestor path.

        If a source note's current frontmatter category differs from the last logged
        category and the new category is part of the approved tree, prefer the source
        note. This keeps generated pages and counts aligned with moved notes even
        before the log is refreshed.
        """
        tree = self.read_tree()
        grouped: dict[CategoryPath, list[CatalogEntry]] = defaultdict(list)
        for source, entry in self.catalog().items():
            resolved = self._resolved_entry_category(source, entry, tree=tree)
            if resolved is None:
                continue
            effective = entry if resolved.display() == entry.category else replace(entry, category=resolved.display())
            for depth in range(1, len(resolved.parts) + 1):
                grouped[CategoryPath(resolved.parts[:depth])].append(effective)
        return grouped

    def _resolved_entry_category(
        self,
        source: str,
        entry: CatalogEntry,
        *,
        tree: WikiCategoryTree | None = None,
    ) -> CategoryPath | None:
        """Return the best current category for one catalog entry."""
        try:
            logged = CategoryPath.parse(entry.category)
        except ValueError:
            logged = None

        if tree is None:
            tree = self.read_tree()
        note_path = self.notebook.resolve(source)
        if note_path.exists():
            metadata = NoteMetadata.read(note_path)
            raw = metadata.frontmatter.get("category")
            if isinstance(raw, str) and raw.strip():
                try:
                    current = CategoryPath.parse(raw)
                except ValueError:
                    current = None
                else:
                    if tree.contains(current):
                        return current
        return logged

    def _resolved_category(self, note: Note, entry: CatalogEntry | None = None) -> str:
        """Pick the note's current category, falling back to catalog if needed."""
        raw = note.frontmatter.get("category")
        if isinstance(raw, str) and raw.strip():
            try:
                return CategoryPath.parse(raw).display()
            except ValueError:
                pass
        if entry is not None:
            return entry.category
        raise ValueError(f"note has no valid category: {note.source}")

    @staticmethod
    def _entry_is_stale(entry: CatalogEntry, note: Note) -> bool:
        """Return true when the catalog entry no longer matches the source note."""
        if entry.source_mtime_ns is None:
            return False
        return note.path.stat().st_mtime_ns != entry.source_mtime_ns

    def _read_events(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Read valid log events and return malformed line diagnostics separately."""
        if not self.config.log_path.exists():
            return [], []
        events: list[dict[str, Any]] = []
        malformed: list[dict[str, Any]] = []
        for line_no, line in enumerate(
            self.config.log_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            raw = stripped[2:].strip()
            if not raw.startswith("{"):
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                malformed.append({"line": line_no, "message": exc.msg})
                continue
            if isinstance(event, dict):
                events.append(event)
            else:
                malformed.append(
                    {"line": line_no, "message": "event must be a JSON object"}
                )
        return events, malformed


# --- private helpers ---


def _utc_now() -> str:
    """Return a UTC timestamp suitable for log events."""
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


def _overlap(terms: tuple[str, ...], text: str) -> tuple[str, ...]:
    tokens = set(Notebook.tokenize(text))
    return tuple(term for term in terms if term in tokens)


def _weight(reason: str) -> int:
    return {
        "title": 8,
        "search_terms": 6,
        "tags": 5,
        "hierarchy": 4,
        "summary": 3,
    }.get(reason, 1)


def _create_if_missing(path: Path, content: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
    except FileExistsError:
        pass


def _write_if_changed(path: Path, content: str, *, expected: str | None) -> bool:
    """Atomically apply a prepared additive edit; reject intervening changes."""
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"refusing to write through a symlink: {path}")
    current = _read_text(path) if path.exists() else None
    if current != expected:
        raise ValueError(f"file changed while preparing wiki update: {path}")
    if current == content:
        return False
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"refusing to write through a symlink: {path}")
        if (_read_text(path) if path.exists() else None) != expected:
            raise ValueError(f"file changed while preparing wiki update: {path}")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def _render_tree_block(categories_dir: Path, paths: set[CategoryPath]) -> str:
    canonical_tree = WikiCategoryTree.from_paths(paths)
    lines: list[str] = []

    def walk(nodes: tuple[Any, ...], prefix: tuple[str, ...]) -> None:
        for node in nodes:
            path = CategoryPath((*prefix, node.name))
            depth = len(path.parts)
            indent = "  " * (depth - 1)
            rel = category_page_path(categories_dir, path).relative_to(
                categories_dir.parent
            ).as_posix()
            lines.append(f"{indent}- layer{depth}: [{node.name}]({rel})")
            walk(node.children, path.parts)

    walk(canonical_tree.roots, ())
    return "\n".join(lines) if lines else "- None"


def _merge_text(existing: str, incoming: str) -> str:
    """Retain accepted catalog information; append a distinct additional summary."""
    if not incoming or incoming == existing or f"\n\n{incoming}\n\n" in f"\n\n{existing}\n\n":
        return existing
    return f"{existing}\n\n{incoming}" if existing else incoming


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _check_write_path(path: Path, root: Path) -> None:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError(f"refusing to write through a symlink: {path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"write path escapes notebook root: {path}") from exc


def _append_section_items(text: str, heading: str, items: list[str]) -> str:
    """Insert only absent lines; never replace an existing section or its prose."""
    items = list(dict.fromkeys(item for item in items if item not in text.splitlines()))
    if not items:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    addition = newline.join(items) + newline
    match = re.search(rf"(?m)^## {re.escape(heading)}[ \t]*\r?$", text)
    if match:
        # Append at the end of this section, without interpreting prose or headings.
        tail = text[match.end():]
        end_match = re.search(r"(?m)^##[ \t]+", tail)
        position = match.end() + end_match.start() if end_match else len(text)
        prefix = text[:position]
        return prefix + ("" if prefix.endswith(newline) else newline) + addition + text[position:]
    return text + ("" if text.endswith(newline) else newline) + newline + f"## {heading}" + newline + newline + addition


def _append_tree_block(text: str, block: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    block = block.replace("\n", newline)
    marker = "## Category Tree"
    if marker not in text:
        return text + ("" if text.endswith(newline) else newline) + newline + marker + newline + newline + block + newline + newline + "---" + newline
    position = text.find(newline + "---" + newline, text.index(marker))
    if position < 0:
        position = len(text)
    prefix = text[:position]
    return prefix + ("" if prefix.endswith(newline) else newline) + block + newline + text[position:]
