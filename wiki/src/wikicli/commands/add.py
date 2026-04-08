from __future__ import annotations

import json
from pathlib import Path

from wikicli.config import ensure_layout, load_config, read_json
from wikicli.core import (
    active_catalog,
    append_log_event,
    apply_category_property,
    extract_packet_from_note,
    gather_source_files,
    normalize_packet,
    normalize_path,
    utc_now,
)
from wikicli.tree import rebuild_generated_views


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("add", help="Add note classifications to the wiki log and rebuild views.")
    parser.add_argument("files", nargs="*", help="Source markdown note paths.")
    parser.add_argument("--packet", help="Path to a JSON packet or packet list.")
    parser.set_defaults(func=run)


def run(args) -> int:
    config = load_config(args.config)
    ensure_layout(config)
    if not config.category_tree_path.exists():
        raise SystemExit(f"missing category tree: {config.category_tree_path}")

    packets: list[dict[str, object]] = []
    if args.packet:
        payload = read_json(Path(args.packet).expanduser().resolve(), None)
        if payload is None:
            raise SystemExit(f"packet file not found: {args.packet}")
        packets.extend(payload if isinstance(payload, list) else [payload])
    for file_arg in args.files:
        packets.append(extract_packet_from_note(Path(file_arg).expanduser().resolve(), config))

    added = []
    for packet in packets:
        normalized = normalize_packet(packet)
        source_path = (config.notebook_root / normalized["source"]).resolve()
        if not source_path.exists():
            raise SystemExit(f"missing source note: {normalized['source']}")
        apply_category_property(source_path, normalized["category_path"])
        event = {"timestamp": utc_now(), "action": "add", "source_mtime_ns": source_path.stat().st_mtime_ns, **normalized}
        append_log_event(config, event)
        added.append(normalized)

    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    artifacts = rebuild_generated_views(config, sorted(current_files - set(active_catalog(config))))
    print(json.dumps({"added": added, "indexed_notes": len(artifacts["catalog"]), "category_pages": artifacts["category_pages"]}, indent=2))
    return 0
