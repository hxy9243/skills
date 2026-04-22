from __future__ import annotations

from collections.abc import Iterable

from .app import Issue
from .config import WikiConfig
from .category import CategoryPath
from .notebook import Note
from .wiki import active_catalog, approved_leaf_paths, malformed_log_lines


def lint_workspace(config: WikiConfig) -> Iterable[Issue]:
    """Yield read-only integrity issues for the resolved wiki workspace."""
    if not config.notebook_root.exists():
        yield Issue(
            "notebook_root_missing",
            "notebook root does not exist",
            path=str(config.notebook_root),
        )
    if not config.generated_root.exists():
        yield Issue(
            "generated_root_missing",
            "generated root does not exist",
            severity="warning",
            path=str(config.generated_root),
        )
        return
    if not config.index_path.exists():
        yield Issue("index_missing", "index.md is missing", path=str(config.index_path))
    if not config.log_path.exists():
        yield Issue("log_missing", "log.md is missing", path=str(config.log_path))
        return
    for item in malformed_log_lines(config):
        yield Issue(
            "log_line_malformed",
            f"malformed log event: {item['message']}",
            path=str(config.log_path),
            line=item.get("line"),
        )

    notes = {note.source: note for note in Note.discover(config)}
    catalog = active_catalog(config)
    leafs = approved_leaf_paths(config)
    for source, entry in catalog.items():
        if source not in notes:
            yield Issue(
                "source_missing",
                f"indexed source note is missing: {source}",
                source=source,
            )
            continue
        if (
            entry.source_mtime_ns is not None
            and notes[source].mtime_ns != entry.source_mtime_ns
        ):
            yield Issue(
                "source_modified",
                f"indexed source note has changed: {source}",
                severity="warning",
                source=source,
            )
        try:
            category = CategoryPath.parse(entry.category)
        except ValueError:
            yield Issue(
                "category_invalid",
                f"catalog category is invalid: {entry.category}",
                source=source,
            )
            continue
        if leafs and category not in leafs:
            yield Issue(
                "category_not_approved",
                f"category is not an approved leaf: {entry.category}",
                source=source,
            )
    for source in sorted(set(notes) - set(catalog), key=str.casefold):
        yield Issue(
            "source_unindexed",
            f"source note is not indexed: {source}",
            severity="warning",
            source=source,
        )
