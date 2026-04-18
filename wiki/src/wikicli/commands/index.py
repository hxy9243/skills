from __future__ import annotations

import json

from wikicli.config import load_config
from wikicli.fs import ensure_layout, gather_source_files, normalize_path, source_mtime_ns
from wikicli.log import active_catalog, append_log_event, utc_now
from wikicli.render import rebuild_generated_views


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "index",
        aliases=["reconcile"],
        help="Scan source notes, record removals, report modifications, and rebuild generated views.",
    )
    parser.set_defaults(func=run)


def run(args) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    if not config.category_tree_path.exists():
        raise SystemExit(f"missing category tree: {config.category_tree_path}")

    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    removed = []
    for source in sorted(set(catalog) - current_files):
        append_log_event(config, {"timestamp": utc_now(), "action": "remove", "source": source, "reason": "source note missing"})
        removed.append(source)

    catalog = active_catalog(config)
    modified = sorted(
        source
        for source, record in catalog.items()
        if source in current_files and record.get("source_mtime_ns") is not None and source_mtime_ns(config, source) != record.get("source_mtime_ns")
    )
    unindexed = sorted(current_files - set(catalog))
    artifacts = rebuild_generated_views(config, unindexed)
    catalog = artifacts["catalog"]
    unindexed = sorted(current_files - set(catalog))
    print(json.dumps({
        "indexed_notes": len(catalog),
        "removed_notes": removed,
        "modified_notes": modified,
        "unindexed_notes": unindexed,
        "category_pages": artifacts["category_pages"],
    }, indent=2))
    return 0
