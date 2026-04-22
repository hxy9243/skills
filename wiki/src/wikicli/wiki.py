from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .category import (
    CategoryPath,
    all_paths,
    category_page_path,
    child_names,
    leaf_paths,
    parse_category_tree,
)
from .config import WikiConfig
from .notebook import Note
from .packet import Packet


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


def ensure_layout(config: WikiConfig) -> None:
    """Create the generated wiki directory and required files."""
    config.generated_root.mkdir(parents=True, exist_ok=True)
    config.categories_dir.mkdir(parents=True, exist_ok=True)
    if not config.log_path.exists():
        config.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    if not config.index_path.exists():
        config.index_path.write_text(
            "# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n",
            encoding="utf-8",
        )


def read_tree(config: WikiConfig) -> list[dict[str, Any]]:
    """Parse the approved category tree from `index.md`."""
    if not config.index_path.exists():
        return []
    return parse_category_tree(config.index_path.read_text(encoding="utf-8"))


def approved_leaf_paths(config: WikiConfig) -> set[CategoryPath]:
    """Return approved leaf category paths from the current index."""
    return leaf_paths(read_tree(config))


def append_event(config: WikiConfig, event: dict[str, Any]) -> None:
    """Append one JSON event to `log.md`."""
    ensure_layout(config)
    with config.log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {json.dumps(event, ensure_ascii=True, sort_keys=True)}\n")


def read_events(
    config: WikiConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read valid log events and return malformed line diagnostics separately."""
    if not config.log_path.exists():
        return [], []
    events: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        config.log_path.read_text(encoding="utf-8").splitlines(), start=1
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


def active_catalog(config: WikiConfig) -> dict[str, CatalogEntry]:
    """Replay add/remove log events into the current active catalog."""
    events, _ = read_events(config)
    catalog: dict[str, CatalogEntry] = {}
    for event in events:
        source = event.get("source")
        if not isinstance(source, str):
            continue
        try:
            source = Note.normalize_source(source)
        except ValueError:
            continue
        action = event.get("action")
        if action == "remove":
            catalog.pop(source, None)
            continue
        if action != "add":
            continue
        title = str(event.get("title") or Path(source).stem)
        summary = str(event.get("summary") or "")
        category = str(event.get("category") or event.get("category_path") or "")
        if not category:
            continue
        try:
            category = CategoryPath.parse(category).display()
        except ValueError:
            continue
        tags = _string_tuple(event.get("tags", ()))
        search_terms = _string_tuple(event.get("search_terms", ()))
        mtime = event.get("source_mtime_ns")
        catalog[source] = CatalogEntry(
            source=source,
            title=title,
            summary=summary,
            category=category,
            tags=tags,
            search_terms=search_terms,
            source_mtime_ns=mtime if isinstance(mtime, int) else None,
            updated_at=str(event.get("timestamp") or ""),
        )
    return dict(sorted(catalog.items(), key=lambda item: item[0].casefold()))


def add_packet(config: WikiConfig, packet: Packet) -> dict[str, Any]:
    """Apply an accepted packet: update frontmatter, append log, render views."""
    ensure_layout(config)
    source_path = Note.resolve_source(config, packet.source)
    changed_files: list[str] = []
    if Note.write_category(source_path, packet.category.display()):
        changed_files.append(packet.source)
    append_event(
        config,
        {
            "timestamp": utc_now(),
            "action": "add",
            "title": packet.title,
            "summary": packet.summary,
            "category": packet.category.display(),
            "tags": list(packet.tags),
            "search_terms": list(packet.search_terms),
            "source": packet.source,
            "source_mtime_ns": source_path.stat().st_mtime_ns,
        },
    )
    changed_files.append(str(config.log_path.relative_to(config.generated_root)))
    render_result = rebuild_generated(config)
    changed_files.extend(render_result["changed_files"])
    catalog = active_catalog(config)
    return {
        "packet": packet.to_json(),
        "changed_files": sorted(set(changed_files)),
        "indexed_count": len(catalog),
        "category_pages": render_result["category_pages"],
    }


def index_workspace(config: WikiConfig) -> dict[str, Any]:
    """Scan notebook state, record missing catalog entries, and regenerate views."""
    ensure_layout(config)
    catalog = active_catalog(config)
    notes = {note.source: note for note in Note.discover(config)}
    removed: list[str] = []
    for source in sorted(set(catalog) - set(notes), key=str.casefold):
        append_event(
            config,
            {
                "timestamp": utc_now(),
                "action": "remove",
                "source": source,
                "reason": "source note missing",
            },
        )
        removed.append(source)
    catalog = active_catalog(config)
    modified = sorted(
        source
        for source, entry in catalog.items()
        if source in notes
        and entry.source_mtime_ns is not None
        and notes[source].mtime_ns != entry.source_mtime_ns
    )
    unindexed = sorted(set(notes) - set(catalog), key=str.casefold)
    render_result = rebuild_generated(config, notes=list(notes.values()))
    return {
        "indexed_count": len(catalog),
        "removed_notes": removed,
        "modified_notes": modified,
        "unindexed_notes": unindexed,
        "category_pages": render_result["category_pages"],
        "changed_files": render_result["changed_files"],
    }


def rebuild_generated(
    config: WikiConfig, *, notes: list[Note] | None = None
) -> dict[str, Any]:
    """Rewrite `index.md` and generated category pages from catalog and tree."""
    ensure_layout(config)
    tree = read_tree(config)
    catalog = active_catalog(config)
    leafs = leaf_paths(tree)
    renderable = [
        entry
        for entry in catalog.values()
        if CategoryPath.parse(entry.category) in leafs
    ]
    all_category_paths = sorted(
        all_paths(tree), key=lambda item: item.display().casefold()
    )
    children = child_names(tree)
    changed_files: list[str] = []

    grouped: dict[CategoryPath, list[CatalogEntry]] = defaultdict(list)
    for entry in renderable:
        path = CategoryPath.parse(entry.category)
        for depth in range(1, len(path.parts) + 1):
            grouped[CategoryPath(path.parts[:depth])].append(entry)

    valid_pages: set[Path] = set()
    for path in all_category_paths:
        page = category_page_path(config.categories_dir, path)
        page.parent.mkdir(parents=True, exist_ok=True)
        text = render_category_page(path, children.get(path, ()), grouped.get(path, []))
        if _write_if_changed(page, text):
            changed_files.append(str(page.relative_to(config.generated_root)))
        valid_pages.add(page.resolve())

    if config.categories_dir.exists():
        for page in sorted(config.categories_dir.rglob("*.md"), reverse=True):
            if page.resolve() not in valid_pages:
                page.unlink()
                changed_files.append(str(page.relative_to(config.generated_root)))
        for directory in sorted(config.categories_dir.rglob("*"), reverse=True):
            if directory.is_dir():
                try:
                    directory.rmdir()
                except OSError:
                    pass

    note_map = (
        {note.source: note for note in notes}
        if notes is not None
        else {note.source: note for note in Note.discover(config)}
    )
    unindexed = sorted(set(note_map) - set(catalog), key=str.casefold)
    skipped_system = [source for source in unindexed if is_system_note(source)]
    index_text = render_index(tree, renderable, skipped_system)
    if _write_if_changed(config.index_path, index_text):
        changed_files.append(str(config.index_path.relative_to(config.generated_root)))
    return {
        "changed_files": sorted(set(changed_files)),
        "category_pages": len(valid_pages),
    }


def render_index(
    tree: list[dict[str, Any]], entries: list[CatalogEntry], skipped_system: list[str]
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

    def render_node(node: dict[str, Any], prefix: tuple[str, ...], depth: int) -> None:
        path = CategoryPath((*prefix, str(node["name"])))
        rel = Path("categories", *path.slug_parts(), "index.md").as_posix()
        indent = "  " * (depth - 1)
        lines.append(f"{indent}- layer{depth}: [{path.parts[-1]}]({rel})")
        children = node.get("children", [])
        if children:
            for child in children:
                render_node(child, path.parts, depth + 1)
            return
        for entry in sorted(
            notes_by_path.get(path, []), key=lambda item: item.source.casefold()
        ):
            lines.append(f"{'  ' * depth}- [[{entry.source}]]")

    for root in tree:
        render_node(root, (), 1)
    if not tree:
        lines.append("- None")
    lines.extend(["", "---", "", "## Skipped System Notes"])
    if skipped_system:
        lines.extend(f"- [[{source}]]" for source in skipped_system)
    else:
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def render_category_page(
    path: CategoryPath, children: tuple[str, ...], entries: list[CatalogEntry]
) -> str:
    """Render one generated category page."""
    depth = len(path.parts)
    lines = [
        f"# layer{depth}: {path.parts[-1]}",
        "",
        "## Layer Path",
        *[f"- {label}" for label in path.layer_labels()],
        "",
        "## Topics Covered",
    ]
    for child in children:
        child_path = CategoryPath((*path.parts, child))
        rel = Path(child_path.slug_parts()[-1], "index.md").as_posix()
        lines.append(f"- [layer{depth + 1}: {child}]({rel})")
    for entry in sorted(entries, key=lambda item: item.title.casefold()):
        lines.append(f"- [[{entry.source}]] - {entry.title}")
    if not children and not entries:
        lines.append("- None")
    lines.extend(["", "## References"])
    if entries:
        for entry in sorted(entries, key=lambda item: item.title.casefold()):
            tag_text = f" ({' '.join(entry.tags)})" if entry.tags else ""
            lines.append(f"- [[{entry.source}]] - {entry.summary}{tag_text}")
    else:
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def catalog_notes(config: WikiConfig) -> list[dict[str, Any]]:
    """Return active catalog entries as JSON-safe sorted dictionaries."""
    return [entry.to_json() for entry in active_catalog(config).values()]


def get_entry(config: WikiConfig, source: str) -> CatalogEntry | None:
    """Return one active catalog entry by source path."""
    return active_catalog(config).get(Note.normalize_source(source))


def malformed_log_lines(config: WikiConfig) -> list[dict[str, Any]]:
    """Return malformed log line diagnostics for lint."""
    _, malformed = read_events(config)
    return malformed


def utc_now() -> str:
    """Return a UTC timestamp suitable for log events."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_system_note(source: str) -> bool:
    """Return true for common dashboard/index notes that should not be indexed."""
    stem = Path(source).stem.casefold().replace("_", "-").replace(" ", "-")
    return stem in {"dashboard", "dashboard-index", "index", "readme", "summary", "log"}


def _write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item).strip())
    return ()
