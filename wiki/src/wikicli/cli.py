from __future__ import annotations

import argparse
from typing import Sequence

from wikicli.commands import add, index, lint, search, synthesize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight wiki indexer.")
    parser.add_argument("--config", help="Path to wiki config JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add.register_parser(subparsers)
    index.register_parser(subparsers)
    search.register_parser(subparsers)
    lint.register_parser(subparsers)
    synthesize.register_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
