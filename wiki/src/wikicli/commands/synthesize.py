from __future__ import annotations

import argparse

from wikicli.app import WikiCli


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("synthesize", help="Return a deterministic synthesis bundle")
    parser.add_argument("--category")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--include-body", action="store_true")
    parser.set_defaults(handler=run)


def run(app: WikiCli, args: argparse.Namespace):
    return app.synthesize_bundle(
        category=args.category,
        tags=tuple(args.tag),
        limit=args.limit,
        include_body=args.include_body,
    )
