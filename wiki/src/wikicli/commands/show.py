from __future__ import annotations

import argparse

from wikicli.app import WikiCli


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("show", help="Show one source note entry")
    parser.add_argument("source")
    parser.set_defaults(handler=run)


def run(app: WikiCli, args: argparse.Namespace):
    return app.show(args.source)
