from __future__ import annotations

import argparse

from wikicli.app import WikiCli


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("search", help="Search indexed wiki notes")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.set_defaults(handler=run)


def run(app: WikiCli, args: argparse.Namespace):
    return app.search(args.query, limit=args.limit)
