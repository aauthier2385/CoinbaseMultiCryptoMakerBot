# Market Intelligence Roadmap

The v2.2 learning layer is intentionally advisory.

## Data to correlate

- Selected crypto market.
- BULL / BEAR / RANGE regime and confidence.
- EMA momentum and longer trend.
- ATR / volatility.
- Volume confirmation.
- Bid/ask spread and maker price position.
- Maker fill time and reprice behavior.
- Entry and exit fees.
- Exit reason.
- Net P&L.

## Questions to answer

- Which regimes produce profitable maker fills rather than merely frequent fills?
- Does a fast fill indicate favorable momentum or adverse selection?
- Which spread and volatility ranges produce the best net results after fees?
- Which exit types account for most losses?
- Do BTC-derived parameters transfer to ETH, XRP, or SOL, or does each market require its own profile?

## Validation sequence

1. Collect enough completed trades per market and regime.
2. Measure fill quality and net results, not just fill rate.
3. Backtest candidate parameter changes.
4. Compare against held-out observations.
5. Keep recommendations advisory until improvements are repeatable.
6. Only then consider controlled automatic adaptation with hard risk limits and rollback behavior.
