from __future__ import annotations

import json

from wikicli.config import load_config
from wikicli.core import active_catalog, gather_source_files, normalize_path
from wikicli.tree import combined_notes, suggest_unindexed_packets


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("synthesize", help="Experimental synthesis entrypoint.")
    parser.add_argument("--category", help="Filter notes by an exact category path segment joined with ' > '.")
    parser.add_argument("--tag", action="append", default=[], help="Filter notes by tag. Repeatable.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum notes to include.")
    parser.set_defaults(func=run)


def run(args) -> int:
    config = load_config(args.config)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    notes = combined_notes(catalog, suggest_unindexed_packets(config, sorted(current_files - set(catalog))))

    selected = notes
    if args.category:
        selected = [note for note in selected if " > ".join(note.get("category_path", [])) == args.category]
    if args.tag:
        requested = set(args.tag)
        selected = [note for note in selected if requested & set(note.get("tags", []))]

    print(json.dumps({
        "status": "experimental",
        "message": "Use this note bundle as input to the synthesize workflow.",
        "notes": selected[: args.limit],
    }, indent=2))
    return 0
