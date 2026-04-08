#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wikicli.config import ensure_layout, load_config
from wikicli.core import active_catalog, append_log_event, apply_category_property, utc_now
from wikicli.tree import rebuild_generated_views


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill frontmatter category properties for indexed wiki notes.")
    parser.add_argument("--config", help="Path to wiki config JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    ensure_layout(config)
    catalog = active_catalog(config)

    updated = 0
    missing: list[str] = []
    refreshed = 0

    for source, note in sorted(catalog.items()):
        source_path = (config.notebook_root / source).resolve()
        if not source_path.exists():
            missing.append(source)
            continue
        changed = apply_category_property(source_path, note["category_path"])
        if changed:
            updated += 1
        append_log_event(
            config,
            {
                "timestamp": utc_now(),
                "action": "add",
                "source": source,
                "title": note["title"],
                "summary": note["summary"],
                "category_path": note["category_path"],
                "tags": note.get("tags", []),
                "source_mtime_ns": source_path.stat().st_mtime_ns,
            },
        )
        refreshed += 1

    artifacts = rebuild_generated_views(config)
    print(
        {
            "updated_notes": updated,
            "refreshed_notes": refreshed,
            "missing_sources": missing,
            "indexed_notes": len(artifacts["catalog"]),
            "category_pages": artifacts["category_pages"],
        }
    )
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
