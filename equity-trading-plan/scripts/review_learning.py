#!/usr/bin/env python3
"""Summarize market snapshots and trade journal entries for strategy improvement."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    snapshots = read_jsonl(args.snapshots)
    journal = read_jsonl(args.journal)
    regimes = collections.Counter(entry.get("regime", "unknown") for entry in snapshots)
    actions = collections.Counter(entry.get("action", "unknown") for entry in journal)
    symbols = collections.Counter(entry.get("symbol", entry.get("asset", "unknown")) for entry in journal)

    latest = snapshots[-1] if snapshots else {}
    latest_scores = latest.get("signal_scores", {})
    latest_prices = latest.get("prices", {})

    lines = [
        "# Equity Trading Plan Learning Review",
        "",
        f"Snapshots reviewed: {len(snapshots)}",
        f"Journal entries reviewed: {len(journal)}",
        "",
        "## Regime Mix",
        *[f"- {name}: {count}" for name, count in regimes.most_common()],
        "",
        "## Journal Mix",
        *[f"- action/{name}: {count}" for name, count in actions.most_common()],
        *[f"- symbol/{name}: {count}" for name, count in symbols.most_common()],
        "",
        "## Latest Signals",
        *[f"- {asset}: {score:+d}" for asset, score in latest_scores.items()],
        "",
        "## Latest Prices",
    ]
    for symbol in ["SPY", "QQQ", "SMH", "XLK", "IGV", "ARKK", "NVDA", "AMD", "AVGO", "TSLA", "PLTR", "CRWD", "COIN"]:
        data = latest_prices.get(symbol, {}) if isinstance(latest_prices, dict) else {}
        price = data.get("close")
        change = data.get("change_pct_from_open")
        if price is not None:
            change_text = f"{change:+.2f}%" if isinstance(change, (int, float)) else "n/a"
            lines.append(f"- {symbol}: ${price:,.2f}, from open {change_text}")
    lines.extend([
        "",
        "## Improvement Prompts",
        "- Did the regime label match the next realized price move, or did it overreact to headlines?",
        "- Were losing decisions caused by bad thesis, bad timing, oversized position, or external shock?",
        "- Should ETF/single-name allocation bands tighten, widen, or stay unchanged?",
        "- Update `references/strategy.md` only after repeated evidence, not one noisy outcome.",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
