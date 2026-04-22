from __future__ import annotations

import argparse

from wikicli.app import WikiCli


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("status", help="Show wiki workspace status")
    parser.set_defaults(handler=run)


def run(app: WikiCli, args: argparse.Namespace):
    return app.status()
