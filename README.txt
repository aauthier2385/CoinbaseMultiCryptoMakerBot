COINBASE MULTI-CRYPTO MAKER BOT — VERSION 2.2

SUPPORTED MARKETS
- BTC-USD
- ETH-USD
- XRP-USD
- SOL-USD
Choose one market in Setup & Strategy before starting. v2.2 runs one selected market at a time and keeps separate state and CSV logs per market.

ORDER-MANAGEMENT FIXES
- Balance-aware BUY sizing: ORDER_USD is now a maximum allocation, not a command to spend every cent.
- Default $0.25 USD funding reserve; configurable.
- Product-specific base/quote increments are read from Coinbase and sizes/prices are rounded DOWN to valid increments.
- Insufficient-fund rejection: refresh/re-size and retry once (configurable), then abort that entry instead of retrying every 20 seconds until timeout.
- Funding circuit breaker pauses new entries for the run after repeated funding failures.
- Repricing occurs only after Coinbase accepted the prior order.
- Cancel -> confirm terminal cancellation -> then reuse funds/reprice. If cancellation cannot be confirmed, repricing stops.
- Post-only BUY price is constrained below the current ask. Post-only price rejections refresh the book instead of becoming a long rejection loop.
- New order events include ORDER_RESIZED, ENTRY_ABORT_FUNDING, and CANCEL_UNCONFIRMED.

MARKET INTELLIGENCE / LEARNING — RECOMMEND/TEST MODE
- Classifies each completed 15-minute candle as BULL / BEAR / RANGE with a confidence score using trend, ATR and volume context.
- Logs regime/confidence into each market's signals and intelligence CSV.
- Closed trades retain the ENTRY regime/confidence, allowing actual net P&L to be grouped by regime.
- After at least 5 completed exits in a regime, the dashboard reports that regime's sample count, profitable-exit rate and average net P&L and gives a test recommendation.
- It DOES NOT automatically rewrite live parameters or override the existing entry logic. Recommendations remain advisory until enough logs are reviewed/backtested.
- The same framework is intended to be compared with the Kalshi BTC 15-minute predictor logs: EMA, trend strength, 1-minute move, direction, entry, TP/SL, and outcomes by regime.
- For this maker bot, review spread/bid-ask position, momentum, volatility, regime, fill behavior, fees, exit reason and net P&L to distinguish a fill from a good fill.

PER-MARKET FILES
Example for BTC-USD:
  btc_usd_state.json
  btc_usd_trades.csv
  btc_usd_signals.csv
  btc_usd_orders.csv
  btc_usd_intelligence.csv
ETH/XRP/SOL use the same naming pattern. Existing v2.1 files are not overwritten.

CARRIED FORWARD FROM v2.1
- 15-minute EMA momentum strategy, 26-EMA trend filter, ATR/volume/spread filters, volatility sizing, loss cooldown and error circuit breaker.
- Hourly trend gate.
- Post-only maker BUY and maker TP; market stop/time/manual exits.
- Windows DPAPI credential storage and GUI themes/dashboard.

IMPORTANT
Start in PAPER mode after upgrading. Market-specific fee tiers, liquidity and volatility differ, so BTC settings should not be assumed optimal for ETH, XRP or SOL. The learning panel is intentionally recommendation/test-only. Trading crypto can lose money and no setting guarantees profit.

SETUP
Run Start_Maker_Bot.bat. It checks Python, installs the Coinbase Advanced Trade SDK if needed, optionally installs ttkbootstrap, and launches the app.
Do not run two LIVE instances against the same Coinbase account/position simultaneously.
