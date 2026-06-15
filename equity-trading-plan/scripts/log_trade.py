#!/usr/bin/env python3
"""Append a manual trade/decision entry to the crypto trading journal."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--symbol", required=True, help="Ticker symbol or CASH")
    parser.add_argument("--action", choices=["buy", "sell", "hold", "watch", "rebalance"], required=True)
    parser.add_argument("--quantity", default="")
    parser.add_argument("--price", default="")
    parser.add_argument("--thesis", required=True)
    parser.add_argument("--invalidation", default="")
    parser.add_argument("--news-summary", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    args.journal.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "symbol": args.symbol.upper(),
        "action": args.action,
        "quantity": args.quantity,
        "price": args.price,
        "thesis": args.thesis,
        "invalidation": args.invalidation,
        "news_summary": args.news_summary,
        "notes": args.notes,
    }
    with args.journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
