from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from .app import CommandResult, Issue, WikiCli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wiki")
    parser.add_argument("--config", help="Path to wiki config JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    from .commands import add, index, lint, search, show, status, synthesize, tree

    for module in (add, index, search, synthesize, lint, tree, show, status):
        module.register(subparsers)

    reconcile = subparsers.add_parser("reconcile", help="Alias for index")
    reconcile.set_defaults(handler=lambda app, args: app.index())
    return parser


def print_result(result: CommandResult) -> None:
    print(json.dumps(result.to_json(), sort_keys=True, separators=(",", ":")))


def _config_error(message: str) -> CommandResult:
    return CommandResult(False, "config", issues=(Issue("config_error", message),), exit_code=2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        app = WikiCli.from_config_path(args.config)
        result: CommandResult = args.handler(app, args)
    except (OSError, ValueError) as exc:
        result = _config_error(str(exc))

    print_result(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
