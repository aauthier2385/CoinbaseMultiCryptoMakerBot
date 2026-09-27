# Coinbase Multi-Crypto Maker Bot

**Current version: v2.2**

Windows desktop maker-order trading/research bot for Coinbase Advanced Trade. v2.2 adds multi-crypto selection, stronger order management, and an advisory Market Intelligence layer.

## Supported markets

- BTC-USD
- ETH-USD
- XRP-USD
- SOL-USD

The current build trades one selected market at a time and keeps separate state and CSV logs per market.

## v2.2 order-management improvements

- Balance-aware BUY sizing: configured order size is a maximum allocation.
- Configurable USD funding reserve.
- Product-specific base/quote increments and downward rounding.
- Insufficient-funds handling refreshes/resizes and performs a controlled retry rather than looping until timeout.
- Funding circuit breaker after repeated funding failures.
- Repricing only after Coinbase accepts the prior order.
- Cancel → confirm terminal cancellation → reuse funds/reprice.
- Post-only BUY prices constrained below the current ask.
- Dedicated diagnostic events such as `ORDER_RESIZED`, `ENTRY_ABORT_FUNDING`, and `CANCEL_UNCONFIRMED`.

## Market Intelligence

The advisory layer classifies completed 15-minute candles as BULL / BEAR / RANGE and records regime/confidence alongside momentum, volatility, spread/fill behavior, fees, exit reason, and net P&L. Its purpose is to distinguish a maker fill from a **good** maker fill and determine which market conditions produce better results.

The learning layer does **not** automatically rewrite live parameters or override entry logic.

## Existing strategy features

- 15-minute EMA momentum strategy.
- Longer trend EMA.
- ATR, volume, and spread filters.
- Volatility-scaled sizing.
- Loss cooldown and API-error circuit breaker.
- Hourly trend gate.
- Post-only maker BUY and maker take-profit.
- Market stop-loss, time exit, and manual flatten.
- Windows DPAPI credential storage.
- GUI themes, dashboard, trade history, and persistent state.

## Running

Run `Start_Maker_Bot.bat`. It checks Python, installs required Coinbase dependencies if necessary, optionally installs `ttkbootstrap`, and launches the application.

Start in PAPER mode after upgrading or changing markets. Fee tiers, liquidity, spread, and volatility differ across BTC, ETH, XRP, and SOL; BTC settings should not automatically be assumed optimal for another market.

Do not run two LIVE instances against the same Coinbase account/position simultaneously.

## Repository layout

- `CoinbaseBTCMakerBot.py` — primary application source.
- `Start_Maker_Bot.bat` — Windows launcher.
- `VERSION.txt` — current version identifier.
- `CHANGELOG.md` — version history.
- `docs/` — order-management and learning documentation.
- `jeep_icon.*` — application artwork.
- `CoinbaseMultiCryptoMakerBot_v2.2.zip` — portable snapshot of the current build.

Runtime CSV files, state files, credentials, private keys, logs, virtual environments, and local build output are intentionally excluded from version control.

## Security

Never commit Coinbase API credentials. Keep the repository private unless it is deliberately prepared for public release.
