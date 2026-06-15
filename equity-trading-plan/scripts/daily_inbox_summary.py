#!/usr/bin/env python3
"""Create a daily Obsidian-ready equity trading summary with headline references."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "equity-summary"


def action_for(regime: str) -> str:
    return {
        "risk-on": "Review a starter ETF allocation; consider adding tactical exposure only after broker review.",
        "selective": "Stay selective: favor broad ETF core, keep cash reserve, avoid single-name chase trades.",
        "defensive": "Preserve cash; avoid new exposure unless risk signals improve.",
        "no-trade": "No trade; keep cash/current allocation and wait for cleaner signal.",
    }.get(regime, "No trade until signal is clearer.")


def rationale_for(regime: str, allocation: str) -> str:
    return (
        f"Regime is `{regime}`, so the plan is `{allocation}`. "
        "The system prioritizes low turnover, cash reserves, and ETF-first exposure; single-name trades need a specific, liquid catalyst."
    )


def render(snapshot: dict, journal: list[dict], schedule_label: str) -> tuple[str, str]:
    local_date = dt.datetime.now().astimezone().date().isoformat()
    regime = snapshot.get("regime", "unknown")
    allocation = snapshot.get("allocation", "No allocation available")
    headlines = snapshot.get("headlines", [])[:12]
    prices = snapshot.get("prices", {})
    latest_decision = journal[-1] if journal else None
    highlight = f"{regime}-equity-plan"

    lines = [
        "---",
        f"date: {local_date}",
        "type: trading-summary",
        "strategy: equity-trading-plan",
        f"regime: {regime}",
        "---",
        "",
        f"# Trading Summary — {local_date}",
        "",
        "## Trading Action",
        f"- {action_for(regime)}",
        "- No options. No crypto execution. Any broker order still requires supported equity workflow and required confirmation.",
        "",
        "## Summary",
        f"- Market regime: `{regime}`",
        f"- Candidate allocation: {allocation}",
    ]
    if latest_decision:
        lines.append(f"- Latest journal decision: `{latest_decision.get('action')}` `{latest_decision.get('symbol')}` — {latest_decision.get('thesis')}")

    lines.extend(["", "## Price Snapshot"])
    for symbol in ["SPY", "QQQ", "SMH", "XLK", "IGV", "ARKK", "NVDA", "AMD", "AVGO", "TSLA", "PLTR", "CRWD", "COIN"]:
        data = prices.get(symbol, {}) if isinstance(prices, dict) else {}
        close = data.get("close")
        change = data.get("change_pct_from_open")
        if close is not None:
            change_text = f"{change:+.2f}%" if isinstance(change, (int, float)) else "n/a"
            lines.append(f"- {symbol}: ${close:,.2f}, from open {change_text}")

    lines.extend(["", "## Trading Rationale", f"- {rationale_for(regime, allocation)}"])

    lines.extend(["", "## News References"])
    if not headlines:
        lines.append("- No headline references captured.")
    for item in headlines:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown")
        link = item.get("link", "")
        symbols = "/".join(item.get("symbols", [])) or "market"
        score = item.get("score", 0)
        if link:
            lines.append(f"- [{symbols}] ({score:+d}) [{title}]({link}) — {source}")
        else:
            lines.append(f"- [{symbols}] ({score:+d}) {title} — {source}")

    lines.extend([
        "",
        "## Next Check",
        f"- Next scheduled scan follows the local weekday schedule: {schedule_label}.",
    ])
    return slugify(highlight), "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-log", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--schedule-label", default="configured weekday cron")
    parser.add_argument("--date", default=dt.datetime.now().astimezone().date().isoformat())
    args = parser.parse_args()

    snapshots = read_jsonl(args.snapshot_log)
    if not snapshots:
        raise SystemExit("No market snapshots available for summary")
    journal = read_jsonl(args.journal)
    slug, markdown = render(snapshots[-1], journal, args.schedule_label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{args.date}-{slug}.md"
    output.write_text(markdown, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
