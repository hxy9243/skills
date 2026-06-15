#!/usr/bin/env python3
"""Generate a cron-safe U.S. equity news and market scan in Markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


WATCHLIST = [
    "SPY", "QQQ", "IWM", "DIA", "SMH", "XLK", "IGV", "ARKK", "XLF", "XLE", "XLV",
    "NVDA", "MSFT", "AVGO", "AMD", "GOOGL", "META", "AMZN", "TSLA", "PLTR", "CRWD", "COIN", "JPM",
]

ALIASES = {
    "SPY": ["s&p", "s&p 500", "spx", "spy"],
    "QQQ": ["nasdaq", "nasdaq 100", "qqq"],
    "IWM": ["small cap", "small-cap", "russell", "iwm"],
    "SMH": ["chip", "chips", "semiconductor", "semiconductors", "smh"],
    "XLK": ["technology", "tech", "xlk"],
    "IGV": ["software", "cloud software", "igv"],
    "ARKK": ["innovation", "high growth", "arkk", "cathie wood"],
    "XLF": ["banks", "financials", "xlf"],
    "XLE": ["energy", "oil", "xle"],
    "XLV": ["healthcare", "health care", "xlv"],
    "NVDA": ["nvidia", "nvda"],
    "MSFT": ["microsoft", "msft"],
    "AVGO": ["broadcom", "avgo"],
    "AMD": ["advanced micro", "amd"],
    "GOOGL": ["alphabet", "google", "googl"],
    "META": ["meta", "facebook"],
    "AMZN": ["amazon", "amzn"],
    "TSLA": ["tesla", "tsla"],
    "PLTR": ["palantir", "pltr"],
    "CRWD": ["crowdstrike", "crwd"],
    "COIN": ["coinbase", "coin"],
    "JPM": ["jpmorgan", "jpm"],
}

POSITIVE_TERMS = {
    "beat", "beats", "raise", "raises", "raised", "upgrade", "upgraded", "rally",
    "rebound", "breakout", "record", "growth", "strong", "surge", "surges", "buyback",
}

NEGATIVE_TERMS = {
    "miss", "misses", "cut", "cuts", "downgrade", "downgraded", "selloff", "plunge",
    "falls", "drop", "drops", "probe", "lawsuit", "warning", "weak", "inflation", "hike",
}

FEEDS = {
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Kiplinger": "https://www.kiplinger.com/investing/rss",
}


@dataclass
class Item:
    source: str
    title: str
    link: str
    published: str
    symbols: list[str]
    score: int


def fetch_url(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "equity-trading-plan/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def text_of(node: ET.Element, name: str) -> str:
    child = node.find(name)
    return html.unescape(child.text.strip()) if child is not None and child.text else ""


def mentions(lowered: str, term: str) -> bool:
    if " " in term or "&" in term:
        return term in lowered
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered) is not None


def classify(title: str) -> tuple[list[str], int]:
    lowered = title.lower()
    symbols = [symbol for symbol, terms in ALIASES.items() if any(mentions(lowered, term) for term in terms)]
    if not symbols and any(mentions(lowered, term) for term in ["stock", "stocks", "market", "fed", "rates", "earnings"]):
        symbols = ["SPY", "QQQ"]
    words = set(lowered.replace("-", " ").replace("/", " ").replace(":", " ").split())
    score = len(words & POSITIVE_TERMS) - len(words & NEGATIVE_TERMS)
    return sorted(set(symbols)), score


def fetch_feed(source: str, url: str, limit: int) -> list[Item]:
    try:
        root = ET.fromstring(fetch_url(url))
    except Exception as exc:
        return [Item(source, f"FEED ERROR: {exc}", url, "", [], 0)]

    results: list[Item] = []
    for node in root.findall(".//item")[: limit * 4]:
        title = text_of(node, "title")
        link = text_of(node, "link")
        published = text_of(node, "pubDate") or text_of(node, "published")
        symbols, score = classify(title)
        if symbols:
            results.append(Item(source, title, link, published, symbols, score))
        if len(results) >= limit:
            break
    return results


def fetch_prices(symbols: list[str]) -> dict[str, dict]:
    prices: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
        try:
            data = json.loads(fetch_url(url).decode("utf-8"))
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            quote = result["indicators"]["quote"][0]
            close_values = [value for value in quote.get("close", []) if value is not None]
            open_values = [value for value in quote.get("open", []) if value is not None]
            close = float(meta.get("regularMarketPrice") or close_values[-1])
            previous = float(meta.get("chartPreviousClose") or (close_values[-2] if len(close_values) > 1 else close))
            open_price = float(open_values[-1]) if open_values else previous
            change = ((close - open_price) / open_price * 100) if open_price else 0.0
        except Exception as exc:
            errors[symbol] = str(exc)
            continue
        prices[symbol] = {
            "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            "time": dt.datetime.now(dt.timezone.utc).time().isoformat(timespec="seconds"),
            "open": open_price,
            "close": close,
            "change_pct_from_open": change,
            "change_pct_from_previous_close": ((close - previous) / previous * 100) if previous else 0.0,
        }
    if errors and not prices:
        return {"error": {"message": json.dumps(errors, sort_keys=True)}}
    return prices


def signal_scores(items: list[Item]) -> dict[str, int]:
    scores = {symbol: 0 for symbol in WATCHLIST}
    for item in items:
        for symbol in item.symbols:
            scores[symbol] = scores.get(symbol, 0) + item.score
    return scores


def regime(items: list[Item], prices: dict[str, dict]) -> str:
    total_score = sum(item.score for item in items)
    core_changes = []
    for symbol in ["QQQ", "SMH", "XLK", "IGV"]:
        change = prices.get(symbol, {}).get("change_pct_from_open") if isinstance(prices, dict) else None
        if isinstance(change, (int, float)):
            core_changes.append(change)
    avg_change = sum(core_changes) / len(core_changes) if core_changes else 0
    if total_score <= -4 or avg_change <= -1.25:
        return "defensive"
    if total_score >= 3 and avg_change >= 0.4:
        return "risk-on"
    if total_score == 0 and abs(avg_change) < 0.25:
        return "no-trade"
    return "selective"


def allocation_for(regime_name: str) -> str:
    return {
        "risk-on": "SPY/VOO 20-30%, QQQ 30-40%, growth ETF 15-25%, tactical single-name 5-15%, cash 10-20%",
        "selective": "SPY/VOO 25-35%, QQQ 25-35%, growth ETF 10-20%, tactical single-name 0-10%, cash 20-30%",
        "defensive": "SPY/VOO 15-30%, QQQ 0-15%, growth/sector ETF 0-10%, cash 60%+",
        "no-trade": "No rebalance candidate; keep current allocation or cash.",
    }[regime_name]


def append_json_log(path: Path, items: list[Item], prices: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "regime": regime(items, prices),
        "allocation": allocation_for(regime(items, prices)),
        "prices": prices,
        "signal_scores": signal_scores(items),
        "headlines": [item.__dict__ for item in sorted(items, key=lambda entry: entry.score, reverse=True)[:40]],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def render(items: list[Item], prices: dict[str, dict]) -> str:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    regime_name = regime(items, prices)
    lines = [
        f"# Equity Trading Plan Scan — {now}",
        "",
        f"**Market regime:** {regime_name}",
        f"**Candidate allocation:** {allocation_for(regime_name)}",
        "",
        "This is an equity-only research brief, not an order. Any trade requires broker review and human confirmation when required by tool contract.",
        "",
        "## Prices",
    ]
    if "error" in prices:
        lines.append(f"- Price fetch error: {prices['error']['message']}")
    else:
        for symbol in WATCHLIST:
            data = prices.get(symbol)
            if not data:
                continue
            lines.append(f"- {symbol}: ${data['close']:,.2f}, from open {data['change_pct_from_open']:+.2f}%")

    lines.extend(["", "## Headlines"])
    if not items:
        lines.append("- No relevant equity headlines found in configured feeds.")
    for item in sorted(items, key=lambda entry: entry.score, reverse=True)[:25]:
        symbol_text = "/".join(item.symbols) if item.symbols else "market"
        lines.append(f"- [{symbol_text}] ({item.score:+d}) {item.title} — {item.source} <{item.link}>")

    scores = signal_scores(items)
    ranked_scores = sorted(scores.items(), key=lambda pair: abs(pair[1]), reverse=True)[:12]
    lines.extend([
        "",
        "## Signal Scores",
        *[f"- {symbol}: {score:+d}" for symbol, score in ranked_scores if score != 0],
        "",
        "## Next Review Checklist",
        "- Check Fed/rates and major macro calendar before any market order.",
        "- Prefer ETFs unless a single-name catalyst is specific and liquid.",
        "- Re-run broker equity review before any trade candidate (Robinhood agentic review is one valid example).",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Markdown output path. Defaults to stdout.")
    parser.add_argument("--json-log", type=Path, help="Append structured scan data to this JSONL file.")
    parser.add_argument("--per-feed", type=int, default=10)
    args = parser.parse_args()

    items: list[Item] = []
    for source, url in FEEDS.items():
        items.extend(fetch_feed(source, url, args.per_feed))
    items = [item for item in items if item.symbols]
    prices = fetch_prices(WATCHLIST)
    markdown = render(items, prices)
    if args.json_log:
        append_json_log(args.json_log, items, prices)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
