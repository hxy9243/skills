from __future__ import annotations

import json

from wikicli.classify import normalize_packet
from wikicli.config import load_config
from wikicli.fs import ensure_layout
from wikicli.log import append_log_event, utc_now
from wikicli.markdown import apply_category_property
from wikicli.render import rebuild_generated_views


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "add", help="Add note classifications to the wiki log and rebuild views."
    )
    parser.add_argument(
        "--packet",
        required=True,
        help="A single packet JSON object.",
    )
    parser.set_defaults(func=run)


def run(args) -> None:
    config = load_config(args.config)
    ensure_layout(config)
    if not config.category_tree_path.exists():
        raise SystemExit(f"missing category tree: {config.category_tree_path}")

    try:
        payload = json.loads(args.packet)
    except json.JSONDecodeError as e:
        raise SystemExit(f"invalid packet JSON: {e}") from e

    if isinstance(payload, list):
        raise SystemExit("packet payload must be a single object, not a list")
    if not isinstance(payload, dict):
        raise SystemExit("packet payload must be a JSON object")

    normalized = normalize_packet(payload)

    source_path = (config.notebook_root / normalized["source"]).resolve()
    if not source_path.exists():
        raise SystemExit(f"missing source note: {normalized['source']}")
    apply_category_property(source_path, normalized["category"])

    append_log_event(
        config,
        {
            "timestamp": utc_now(),
            "action": "add",
            "source_mtime_ns": source_path.stat().st_mtime_ns,
            **normalized,
        },
    )
    artifacts = rebuild_generated_views(config)

    print(
        json.dumps(
            {
                "added": normalized,
                "indexed_notes": len(artifacts["catalog"]),
                "category_pages": artifacts["category_pages"],
            },
            indent=2,
        )
    )
