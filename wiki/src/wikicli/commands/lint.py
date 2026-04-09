from __future__ import annotations

import json

from wikicli.config import ensure_layout, load_config
from wikicli.core import (
    active_catalog,
    append_log_event,
    apply_category_property,
    category_value,
    frontmatter_category_path,
    gather_source_files,
    normalize_path,
    parse_index_note_assignments,
    source_mtime_ns,
    utc_now,
)
from wikicli.tree import parse_category_tree


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("lint", help="Validate tree coverage and indexed notes.")
    parser.add_argument("--log", action="store_true", help="Append lint findings to log.md.")
    parser.set_defaults(func=run)


def run(args) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    issues: list[str] = []
    fixes: list[str] = []
    seen_issues: set[str] = set()
    seen_fixes: set[str] = set()

    def add_issue(message: str) -> None:
        if message not in seen_issues:
            seen_issues.add(message)
            issues.append(message)

    def add_fix(message: str) -> None:
        if message not in seen_fixes:
            seen_fixes.add(message)
            fixes.append(message)

    if not config.category_tree_path.exists():
        add_issue("missing index.md")

    allowed = parse_category_tree(config.category_tree_path)
    catalog = active_catalog(config)
    index_assignments = parse_index_note_assignments(config.category_tree_path)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}

    for source, category_path in sorted(index_assignments.items()):
        if source not in current_files:
            add_issue(f"missing source note: {source}")
            continue
        if allowed and tuple(category_path) not in allowed:
            add_issue(f"category not in tree: {source} -> {' -> '.join(category_path)}")

    for source, record in sorted(catalog.items()):
        if source not in current_files:
            add_issue(f"missing source note: {source}")
            continue
        source_path = (config.notebook_root / source).resolve()
        expected_category = index_assignments.get(source, record["category_path"])
        current_frontmatter = frontmatter_category_path(source_path.read_text(encoding="utf-8"))
        changed = False

        if expected_category != record["category_path"]:
            changed = True
            add_fix(f"catalog category synced from index: {source} -> {category_value(expected_category)}")

        if current_frontmatter != expected_category:
            if apply_category_property(source_path, expected_category):
                changed = True
                add_fix(f"frontmatter category updated: {source} -> {category_value(expected_category)}")

        current_mtime = source_mtime_ns(config, source)
        if changed:
            append_log_event(
                config,
                {
                    "timestamp": utc_now(),
                    "action": "add",
                    "title": record["title"],
                    "summary": record["summary"],
                    "category_path": expected_category,
                    "tags": record.get("tags", []),
                    "source": source,
                    "source_mtime_ns": current_mtime,
                },
            )
            record = {**record, "category_path": expected_category, "source_mtime_ns": current_mtime}

        stored_mtime = record.get("source_mtime_ns")
        if stored_mtime is not None and current_mtime != stored_mtime:
            add_issue(f"modified note: {source}")
        if allowed and tuple(expected_category) not in allowed:
            add_issue(f"category not in tree: {source} -> {' -> '.join(expected_category)}")

    for source in sorted(current_files - set(catalog)):
        add_issue(f"unindexed note: {source}")

    if args.log:
        append_log_event(config, {"timestamp": utc_now(), "action": "lint", "issues": issues, "fixes": fixes})

    print(json.dumps({"issues": issues, "fixes": fixes, "indexed_notes": len(catalog)}, indent=2))
    return 1 if issues else 0
