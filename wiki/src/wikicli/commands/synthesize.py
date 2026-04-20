from __future__ import annotations

import json

from wikicli.config import load_config
from wikicli.fs import gather_source_files, normalize_path
from wikicli.log import active_catalog
from wikicli.markdown import clean_note_text
from wikicli.render import combined_notes, suggest_unindexed_packets


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("synthesize", help="Experimental synthesis entrypoint.")
    parser.add_argument("--category", help="Filter notes by an exact category path segment joined with ' > '.")
    parser.add_argument("--tag", action="append", default=[], help="Filter notes by tag. Repeatable.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum notes to include.")
    parser.add_argument("--include-body", action="store_true", help="Include the full markdown body of the notes in the output.")
    parser.set_defaults(func=run)


def run(args) -> None:
    config = load_config(args.config)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    notes = combined_notes(catalog, suggest_unindexed_packets(config, sorted(current_files - set(catalog))))

    selected = notes
    if args.category:
        selected = [note for note in selected if note.get("category") == args.category]
    if args.tag:
        requested = set(args.tag)
        selected = [note for note in selected if requested & set(note.get("tags", []))]

    selected = selected[: args.limit]

    if args.include_body:
        for note in selected:
            source_path = config.notebook_root / note["source"]
            if source_path.exists():
                note["body"] = clean_note_text(source_path.read_text(encoding="utf-8"))

    print(json.dumps({
        "status": "experimental",
        "message": "Use this note bundle as input to the synthesize workflow.",
        "notes": selected,
    }, indent=2))
