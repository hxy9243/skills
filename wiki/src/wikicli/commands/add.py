from __future__ import annotations

import argparse

from wikicli.app import WikiCli


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add", help="Add one classified packet to the wiki")
    parser.add_argument("--packet", required=True, help="Packet JSON object")
    parser.add_argument("--allow-undeclared", action="store_true", help="Allow categories outside the approved tree")
    parser.set_defaults(handler=run)


def run(app: WikiCli, args: argparse.Namespace):
    return app.add_packet(args.packet, allow_undeclared=args.allow_undeclared)
