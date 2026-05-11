from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .app import CommandResult, WikiCli


def build_parser() -> argparse.ArgumentParser:
    """Build the complete CLI parser with all commands inline."""
    parser = argparse.ArgumentParser(prog="wiki")
    parser.add_argument("--config", help="Path to wiki config JSON")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- add ---
    add_parser = subparsers.add_parser(
        "add", help="Add one classified note to the wiki"
    )
    add_parser.add_argument(
        "--json", dest="json_packet", required=True, help="NewNote JSON object"
    )
    add_parser.add_argument(
        "--allow-undeclared",
        action="store_true",
        help="Allow categories outside the approved tree",
    )

    # --- index ---
    subparsers.add_parser(
        "index", help="Reconcile notebook state and regenerate wiki files"
    )

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List catalog entries")
    list_parser.add_argument(
        "category", nargs="?", default=None, help="Category to filter by"
    )
    list_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include subcategories",
    )
    list_parser.add_argument(
        "--include-body",
        action="store_true",
        help="Include cleaned note body text",
    )
    list_parser.add_argument(
        "--limit", type=int, default=None, help="Maximum entries to return"
    )

    # --- search ---
    search_parser = subparsers.add_parser(
        "search", help="Search indexed wiki notes"
    )
    search_parser.add_argument(
        "query", nargs="?", default=None, help="Search query text"
    )
    search_parser.add_argument(
        "--tag", dest="tags", action="append", default=[], help="Filter by tag"
    )
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument(
        "--include-body",
        action="store_true",
        help="Include cleaned note body text",
    )

    # --- lint ---
    subparsers.add_parser(
        "lint", help="Run read-only workspace integrity checks"
    )

    return parser


def print_result(result: CommandResult) -> None:
    """Print compact, deterministic JSON for machine consumers."""
    print(json.dumps(result.to_json(), sort_keys=True, separators=(",", ":")))


def print_text_output(result: CommandResult) -> None:
    """Print human-facing text for commands that support it."""
    if result.ok and result.command == "list" and "entries" in result.data:
        entries = result.data["entries"]
        if not entries:
            print("No entries found.")
        else:
            for entry in entries:
                print(f"- [{entry['category']}] {entry['title']} ({entry['source']})")
        return
    if result.ok and result.command == "search" and "results" in result.data:
        results = result.data["results"]
        if not results:
            print("No results found.")
        else:
            for hit in results:
                print(f"- [{hit['score']}] {hit['title']} ({hit['source']})")
        return
    # Fall back to JSON for everything else
    print_result(result)


def _config_error(message: str) -> CommandResult:
    """Convert config loading failures into the normal command result envelope."""
    from .app import Issue

    return CommandResult(
        False, "config", issues=(Issue("config_error", message),), exit_code=2
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse args, run one command, print output, and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        app = WikiCli.from_config_path(args.config)
    except (OSError, ValueError) as exc:
        result = _config_error(str(exc))
        print_result(result)
        return result.exit_code

    command = args.command
    try:
        if command == "add":
            result = app.add(
                args.json_packet, allow_undeclared=args.allow_undeclared
            )
        elif command == "index":
            result = app.index()
        elif command == "list":
            result = app.list(
                args.category,
                recursive=args.recursive,
                include_body=args.include_body,
            )
        elif command == "search":
            result = app.search(
                args.query,
                tags=tuple(args.tags),
                limit=args.limit,
                include_body=args.include_body,
            )
        elif command == "lint":
            result = app.lint()
        else:
            parser.error(f"unknown command: {command}")
            return 2  # unreachable
    except (OSError, ValueError) as exc:
        result = _config_error(str(exc))

    if args.format == "json":
        print_result(result)
    else:
        print_text_output(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
