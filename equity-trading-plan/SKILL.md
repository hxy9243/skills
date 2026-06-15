---
name: equity-trading-plan
description: Conservative growth-and-volatility focused short-to-mid-term equity trading plan for news, earnings, sector rotation, AI/growth momentum, and market swing opportunities. Use when asked to monitor U.S. growth equities, capture short-term volatility, build an equity-only trade plan, scan market news, rebalance ETFs/stocks, manage a small tactical broker account, or evaluate performance by profit, token burn, tax drag, and volatility. Robinhood agentic accounts are a valid example deployment, but the skill should remain broker-agnostic. Do not use for options or crypto execution.
---

# Equity Trading Plan

## Operating Rule

Optimize for conservative short-to-mid-term, risk-adjusted gains in an equity-only strategy. Live broker tools may still require supported instruments, pre-trade review, and explicit confirmation when the tool contract requires it. Do not trade options. Do not treat crypto news as an execution signal unless it affects public equities.

Evaluate performance on four axes: overall profit, token burn, tax-aware harvesting/opportunity cost, and volatility/drawdown. A lower-volatility strategy that preserves capital and uses fewer tokens is preferred over noisy overtrading.

## Public Skill Boundary

This skill should stay publishable and path-agnostic.

- Keep public docs focused on trading logic, workflow, heuristics, pitfalls, and generic script interfaces.
- Do not hardcode user-specific paths, vault locations, account identifiers, cron installs, or private MCP/ACP invocation details here.
- Store local operational config in the user's workspace notes or tool memory layer.

## Core Workflow

1. Run `scripts/equity_news_scan.py` to gather market headlines, ETF/stock price snapshots, and keyword signals.
2. Read `references/strategy.md` before recommending allocations, trade sizing, or risk posture.
3. Classify the market regime: `risk-on`, `selective`, `defensive`, or `no-trade`.
4. Produce a concise brief: market tape, catalysts, candidate allocation, invalidation, and watchlist.
5. Log any human-approved decision with `scripts/log_trade.py`, including thesis, invalidation, price, and news summary.
6. If a user asks to trade, use the available broker review tools first, show costs/alerts, then wait for explicit confirmation. Robinhood agentic equity workflows are a valid example when supported.

## Strategy Theme

Use growth-led market swing capture: broad-market anchor, growth ETF overweight, and small tactical high-volatility sleeves:

- **Core anchor**: SPY/VOO for market beta and drawdown control.
- **Growth ETFs**: QQQ, SMH, XLK, IGV, and selective ARKK for AI/software/innovation swings.
- **Tactical high-vol names**: Only liquid, news-driven growth names such as NVDA, AMD, AVGO, MSFT, GOOGL, META, AMZN, TSLA, PLTR, CRWD, COIN.
- **Cash**: Active volatility reserve. Use it to buy pullbacks or avoid bad chop.
- **Cash**: Active risk-control sleeve. Raise cash when Fed/rate, AI-capex, earnings, or geopolitical headlines conflict.

## Default Brief Format

- **Market Regime**: one of `risk-on`, `selective`, `defensive`, `no-trade`.
- **Top Signals**: 3-5 bullets from index moves, sector moves, macro/Fed, earnings, and major headlines.
- **Candidate Allocation**: ETFs/stocks/cash percentages with max position size and invalidation.
- **Action**: `hold`, `watch`, `rebalance candidate`, or `trade candidate pending approval`.
- **Risks**: rate shock, earnings miss, AI-capex reset, failed breakout, broad volatility spike, tax churn.

## Guardrails

- Do not trade options.
- Prefer growth ETFs over single names unless a catalyst is specific, liquid, and time-boxed.
- Keep single-name positions at or below 10-15% of account value by default.
- Use the late-session scan as the main pre-close checkpoint: add only if the day’s move still holds into the close; cut/avoid if the move fades.
- Do not chase gap-ups blindly; require either pullback support or clean breakout continuation.
- Prefer no trade over forced trade when signals conflict.
- Keep cron scans deterministic and cheap; only spend LLM tokens when a report has material changes or the user asks for judgment.
- Prefer low-turnover decisions to reduce tax complexity unless tax-loss harvesting creates a clear benefit.
- For broker or MCP orders, use only supported equity workflows and the configured account. Robinhood agentic accounts are a valid example, not a requirement.

## Learning Loop

- Append every scheduled scan to `logs/market_snapshots.jsonl`.
- Append every trade, hold, watch, or rebalance decision to `logs/trading_journal.jsonl`.
- Run scheduled scans in three phases: market-open posture, pre-close review, and end-of-day plus after-hours summary.
- During the end-of-day run, optionally write a notebook/inbox summary with trading action, summary, rationale, and headline references when the local environment config requests it.
- Run `scripts/review_learning.py` daily or weekly to compare decisions against subsequent prices and recurring news themes.
- Improve the strategy only from repeated evidence: regime errors, bad sizing, recurring false-positive headlines, or missed catalysts.
- Prefer tightening risk controls over increasing aggression after a few wins.

## Resources

- `scripts/equity_news_scan.py`: Scheduled-scan-safe RSS/news + price snapshot generator.
- `scripts/log_trade.py`: Manual decision/trade journal appender.
- `scripts/review_learning.py`: Learning review generator from market snapshots and journal entries.
- `scripts/daily_inbox_summary.py`: Optional notebook/inbox summary exporter with news references.
- `references/strategy.md`: Equity strategy logic, allocation defaults, risk rules, and source themes.
