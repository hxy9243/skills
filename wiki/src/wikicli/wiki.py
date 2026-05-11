from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from enum import Enum
from typing import Any

from .category import (
    CategoryPath,
    WikiCategoryTree,
    category_page_path,
)
from .config import WikiConfig
from .notebook import Notebook, NoteMetadata, NewNote


class IssueType(str, Enum):
    NOTE_MISSING = "note_missing"
    NOTE_MODIFIED = "note_modified"
    UNINDEXED = "unindexed"
    INVALID_CATEGORY = "invalid_category"


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

    def add_category(self, path: str | CategoryPath) -> WikiCategoryTree:
        """Add a category path to the tree in index.md (stub for future)."""
        if isinstance(path, str):
            path = CategoryPath.parse(path)
        # For now just return the current tree — full implementation deferred
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
        self._ensure_layout()
        source_path = self.notebook.resolve(note.source)
        changed_files: list[str] = []
        if NoteMetadata.write_category(source_path, note.category.display()):
            changed_files.append(note.source)
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
        changed_files.append(
            str(self.config.log_path.relative_to(self.config.generated_root))
        )
        render_result = self.render()
        changed_files.extend(render_result["changed_files"])
        catalog = self.catalog()
        return {
            "packet": note.to_json(),
            "changed_files": sorted(set(changed_files)),
            "indexed_count": len(catalog),
            "category_pages": render_result["category_pages"],
        }

    def index(self) -> dict[str, Any]:
        """Scan notebook state, record missing catalog entries, and regenerate views."""
        self._ensure_layout()
        catalog = self.catalog()
        notes = {note.source: note for note in self.notebook.discover()}
        removed: list[str] = []
        for source in sorted(set(catalog) - set(notes), key=str.casefold):
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
            if source in notes
            and entry.source_mtime_ns is not None
            and notes[source].last_modified.timestamp()
            != entry.source_mtime_ns / 1e9
        )
        unindexed = sorted(set(notes) - set(catalog), key=str.casefold)
        render_result = self.render(notes=list(notes.values()))
        return {
            "indexed_count": len(catalog),
            "removed_notes": removed,
            "modified_notes": modified,
            "unindexed_notes": unindexed,
            "category_pages": render_result["category_pages"],
            "changed_files": render_result["changed_files"],
        }

    # --- rendering ---

    def render(self, *, notes: list[Any] | None = None) -> dict[str, Any]:
        """Rewrite `index.md` and generated category pages from catalog and tree."""
        self._ensure_layout()
        tree = self.read_tree()
        catalog = self.catalog()
        leafs = tree.leaf_paths()
        renderable = [
            entry
            for entry in catalog.values()
            if CategoryPath.parse(entry.category) in leafs
        ]
        all_category_paths = sorted(
            tree.all_paths(), key=lambda item: item.display().casefold()
        )
        child_names = tree.child_names()
        changed_files: list[str] = []

        grouped: dict[CategoryPath, list[CatalogEntry]] = defaultdict(list)
        for entry in renderable:
            path = CategoryPath.parse(entry.category)
            for depth in range(1, len(path.parts) + 1):
                grouped[CategoryPath(path.parts[:depth])].append(entry)

        valid_pages: set[Path] = set()
        for path in all_category_paths:
            page = category_page_path(self.config.categories_dir, path)
            page.parent.mkdir(parents=True, exist_ok=True)
            text = _render_category_page(
                path, child_names.get(path, ()), grouped.get(path, [])
            )
            if _write_if_changed(page, text):
                changed_files.append(
                    str(page.relative_to(self.config.generated_root))
                )
            valid_pages.add(page.resolve())

        if self.config.categories_dir.exists():
            for page in sorted(
                self.config.categories_dir.rglob("*.md"), reverse=True
            ):
                if page.resolve() not in valid_pages:
                    page.unlink()
                    changed_files.append(
                        str(page.relative_to(self.config.generated_root))
                    )
            for directory in sorted(
                self.config.categories_dir.rglob("*"), reverse=True
            ):
                if directory.is_dir():
                    try:
                        directory.rmdir()
                    except OSError:
                        pass

        note_map = (
            {note.source: note for note in notes}
            if notes is not None
            else {note.source: note for note in self.notebook.discover()}
        )
        unindexed = sorted(set(note_map) - set(catalog), key=str.casefold)
        skipped_system = [
            source for source in unindexed if _is_system_note(source)
        ]
        index_text = _render_index(tree, renderable, skipped_system)
        if _write_if_changed(self.config.index_path, index_text):
            changed_files.append(
                str(
                    self.config.index_path.relative_to(
                        self.config.generated_root
                    )
                )
            )
        return {
            "changed_files": sorted(set(changed_files)),
            "category_pages": len(valid_pages),
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
            if (
                entry.source_mtime_ns is not None
                and notes[source].last_modified.timestamp()
                != entry.source_mtime_ns / 1e9
            ):
                issues.append(
                    Issue(
                        IssueType.NOTE_MODIFIED,
                        f"indexed source note has changed: {source}",
                        severity="warning",
                        source=source,
                    )
                )
            try:
                CategoryPath.parse(entry.category)
            except ValueError:
                issues.append(
                    Issue(
                        IssueType.INVALID_CATEGORY,
                        f"catalog category is invalid: {entry.category}",
                        source=source,
                    )
                )
                continue

        for source in sorted(set(notes) - set(catalog), key=str.casefold):
            issues.append(
                Issue(
                    IssueType.UNINDEXED,
                    f"source note is not indexed: {source}",
                    severity="warning",
                    source=source,
                )
            )
        return tuple(issues)

    # --- private helpers ---

    def _ensure_layout(self) -> None:
        """Create the generated wiki directory and required files."""
        self.config.generated_root.mkdir(parents=True, exist_ok=True)
        self.config.categories_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.log_path.exists():
            self.config.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
        if not self.config.index_path.exists():
            self.config.index_path.write_text(
                "# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n",
                encoding="utf-8",
            )

    def _append_event(self, event: dict[str, Any]) -> None:
        """Append one JSON event to `log.md`."""
        self._ensure_layout()
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"- {json.dumps(event, ensure_ascii=True, sort_keys=True)}\n"
            )

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


# --- rendering helpers ---


def _render_index(
    tree: WikiCategoryTree,
    entries: list[CatalogEntry],
    skipped_system: list[str],
) -> str:
    """Render the generated `index.md` page."""
    notes_by_path: dict[CategoryPath, list[CatalogEntry]] = defaultdict(list)
    for entry in entries:
        notes_by_path[CategoryPath.parse(entry.category)].append(entry)
    lines = [
        "# Wiki Index",
        "",
        "## Category Tree",
        "",
        "This tree is the classification reference for the wiki.",
        "",
    ]

    def render_node(
        node: Any, prefix: tuple[str, ...], depth: int
    ) -> None:
        path = CategoryPath((*prefix, str(node.name)))
        rel = Path("categories", *path.slug_parts(), "index.md").as_posix()
        indent = "  " * (depth - 1)
        lines.append(f"{indent}- layer{depth}: [{path.parts[-1]}]({rel})")
        if node.children:
            for child in node.children:
                render_node(child, path.parts, depth + 1)
            return
        for entry in sorted(
            notes_by_path.get(path, []),
            key=lambda item: item.source.casefold(),
        ):
            lines.append(f"{'  ' * depth}- [[{entry.source}]]")

    for root in tree.roots:
        render_node(root, (), 1)
    if not tree.roots:
        lines.append("- None")
    lines.extend(["", "---", "", "## Skipped System Notes"])
    if skipped_system:
        lines.extend(f"- [[{source}]]" for source in skipped_system)
    else:
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def _render_category_page(
    path: CategoryPath,
    children: tuple[str, ...],
    entries: list[CatalogEntry],
) -> str:
    """Render one generated category page."""
    depth = len(path.parts)
    now = _utc_now()
    lines = [
        "---",
        f'category: "{path.display()}"',
        f"created: {now}",
        f"modified: {now}",
        "tags:",
        "  - category-index",
        "---",
        f"# layer{depth}: {path.parts[-1]}",
        "",
        "## Layer Path",
        *[f"- {label}" for label in path.layer_labels()],
        "",
    ]
    if children:
        lines.append("## Subcategories")
        for child in children:
            child_path = CategoryPath((*path.parts, child))
            rel = Path(child_path.slug_parts()[-1], "index.md").as_posix()
            lines.append(f"- [layer{depth + 1}: {child}]({rel})")
        lines.append("")

    lines.append("## References")
    if entries:
        for entry in sorted(entries, key=lambda item: item.title.casefold()):
            tag_text = f" ({' '.join(entry.tags)})" if entry.tags else ""
            lines.append(
                f"- [[{entry.source}]] - {entry.summary}{tag_text}"
            )
    else:
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def _is_system_note(source: str) -> bool:
    """Return true for common dashboard/index notes that should not be indexed."""
    stem = (
        Path(source).stem.casefold().replace("_", "-").replace(" ", "-")
    )
    return stem in {
        "dashboard",
        "dashboard-index",
        "index",
        "readme",
        "summary",
        "log",
    }


def _write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


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
