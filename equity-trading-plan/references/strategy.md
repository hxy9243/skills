# Equity Trading Strategy Reference

## Purpose

Create weekday market briefs and candidate equity-only trade plans for a small tactical broker account. Focus on growth-market momentum and short-term volatility swings. No options. No crypto execution. Evaluate on overall profit, token burn, tax-aware opportunity cost, and volatility.

## Current Theme

The preferred theme is **growth-led swing capture with volatility-aware sizing**:

1. Keep a small broad ETF anchor so the account is not purely single-name noise.
2. Overweight QQQ/SMH/XLK/IGV when AI/chip/software/growth news and price action align.
3. Use tactical single names only for liquid, time-boxed catalysts or clean swing setups.
4. Preserve cash when growth gaps fade, rates/yields pressure duration assets, or volatility gets disorderly.

## Base Allocation Bands

- Defensive: SPY/VOO 15-30%, QQQ 0-15%, growth/sector ETF 0-10%, tactical single-name 0%, cash 60-85%.
- Selective: SPY/VOO 25-35%, QQQ 25-35%, growth/sector ETF 10-20%, tactical single-name 0-10%, cash 20-30%.
- Risk-on: SPY/VOO 20-30%, QQQ 30-40%, growth/sector ETF 15-25%, tactical single-name 5-15%, cash 10-20%.
- No-trade: keep current allocation or cash; only monitor.

For a small account, favor clear conviction sizing and meaningful cash. Position count and fractional-share usage should be configured locally.

## Watchlist

- Core anchor: SPY, VOO.
- Growth ETFs: QQQ, SMH, XLK, IGV, ARKK.
- Secondary rotation: IWM, XLF, XLE, XLV.
- Tactical liquid growth/high-vol names: NVDA, MSFT, AVGO, AMD, GOOGL, META, AMZN, TSLA, PLTR, CRWD, COIN, JPM.

## Signal Stack

Score each candidate from -2 to +2:

- News/catalyst: earnings, guidance, AI capex, regulation, macro, M&A, product launch.
- Tape: QQQ/SMH/XLK trend, breadth, relative strength, gap behavior, intraday reversal.
- Sector leadership: chips/tech, financials, energy, healthcare, small caps.
- Volatility: VIX/news shock proxy, large gap, failed breakout, concentrated downside.
- Macro: Fed/rates, CPI/jobs/FOMC calendar, oil/geopolitics, dollar/yields.

## Decision Rules

- Add exposure only when total signal is positive and no hard risk veto is present.
- Cut or avoid exposure on earnings/guidance misses, rate shock, oil shock, broad risk-off, or failed breakout.
- Rebalance candidates must include thesis, invalidation, max loss, expected holding window, and whether the setup is breakout continuation or pullback support.
- Never recommend going all-in. Never chase a vertical move without a cool-down or pullback plan.
- Use three scheduled checkpoints: initial market-open bias, pre-close confirmation/fade detection, and end-of-day review.

## Risk Controls

- Maximum single rebalance: 25% of account value unless the user explicitly overrides.
- Maximum single-name sleeve by default: 10% of account value, 15% only for exceptional liquid mega-cap setups.
- Maximum growth/high-vol sleeve by default: 45-60% in risk-on, 30-45% in selective, 0-20% in defensive.
- Maximum equity exposure by default: 80-90% in risk-on, 60-80% in selective, 15-40% in defensive.
- Keep at least 10-20% cash unless regime is clearly risk-on.
- Default max drawdown tolerance before defensive reset: 5-8% from recent high-water mark.
- Default turnover target: low; do not rebalance on small signal changes.
- Tax awareness: log cost basis assumptions and flag potential tax-loss harvesting candidates, but do not wash-trade or churn purely for tax optics.

## Autonomy Boundary

Treat user auto-trade preference as strategic preference, not permission to bypass broker/tool safety contracts. If the available broker or MCP tool requires review or explicit confirmation, obey the tool contract. Apply conservative defaults first: no options, no leverage, max 25% single rebalance, max 15% single-name sleeve, keep cash reserve, and pause after abnormal volatility.

## Brief Output

Use this structure:

1. Market regime.
2. Index/sector signal table.
3. News catalysts.
4. Candidate allocation.
5. Invalidation and risk controls.
6. Next check time.
