from __future__ import annotations

import json

from wikicli.config import ensure_layout, load_config
from wikicli.core import active_catalog, append_log_event, gather_source_files, normalize_path, source_mtime_ns, utc_now
from wikicli.tree import parse_category_tree


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("lint", help="Validate tree coverage and indexed notes.")
    parser.add_argument("--log", action="store_true", help="Append lint findings to log.md.")
    parser.set_defaults(func=run)


def run(args) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    issues: list[str] = []
    if not config.category_tree_path.exists():
        issues.append("missing index.md")

    allowed = parse_category_tree(config.category_tree_path)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    for source, record in sorted(catalog.items()):
        if source not in current_files:
            issues.append(f"missing source note: {source}")
            continue
        stored_mtime = record.get("source_mtime_ns")
        if stored_mtime is not None and source_mtime_ns(config, source) != stored_mtime:
            issues.append(f"modified note: {source}")
        if allowed and tuple(record["category_path"]) not in allowed:
            issues.append(f"category not in tree: {source} -> {' -> '.join(record['category_path'])}")

    for source in sorted(current_files - set(catalog)):
        issues.append(f"unindexed note: {source}")

    if args.log:
        append_log_event(config, {"timestamp": utc_now(), "action": "lint", "issues": issues})

    print(json.dumps({"issues": issues, "indexed_notes": len(catalog)}, indent=2))
    return 1 if issues else 0
