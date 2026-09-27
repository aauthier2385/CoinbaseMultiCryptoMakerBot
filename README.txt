COINBASE MULTI-CRYPTO MAKER BOT — VERSION 2.2

SUPPORTED MARKETS
- BTC-USD
- ETH-USD
- XRP-USD
- SOL-USD
Choose one market in Setup & Strategy before starting. v2.2 runs one selected market at a time and keeps separate state and CSV logs per market.

ORDER-MANAGEMENT FIXES
- Balance-aware BUY sizing: ORDER_USD is a maximum allocation, not a command to spend every cent.
- Default USD funding reserve; configurable.
- Product-specific base/quote increments read from Coinbase; sizes/prices rounded down to valid increments.
- Insufficient-fund rejection refreshes/resizes and retries in a controlled way instead of looping until timeout.
- Funding circuit breaker pauses new entries after repeated funding failures.
- Repricing occurs only after Coinbase accepted the prior order.
- Cancel -> confirm terminal cancellation -> then reuse funds/reprice.
- Post-only BUY price constrained below the current ask.
- Diagnostic order events include ORDER_RESIZED, ENTRY_ABORT_FUNDING, and CANCEL_UNCONFIRMED.

MARKET INTELLIGENCE / LEARNING — RECOMMEND/TEST MODE
- Classifies completed 15-minute candles as BULL / BEAR / RANGE with confidence using trend, ATR and volume context.
- Logs regime/confidence into per-market signals and intelligence CSVs.
- Closed trades retain entry regime/confidence so actual net P&L can be grouped by regime.
- Learning recommendations remain advisory; they do not automatically rewrite live parameters.

CARRIED FORWARD
- 15-minute EMA momentum strategy, trend EMA, ATR/volume/spread filters, volatility sizing, loss cooldown and API-error circuit breaker.
- Hourly trend gate.
- Post-only maker BUY and maker TP; market stop/time/manual exits.
- Windows DPAPI credential storage and GUI themes/dashboard.

SECURITY
Never commit Coinbase credentials, .env files, local state, or sensitive runtime logs. The repository .gitignore excludes common secret/runtime files.

SETUP
Run Start_Maker_Bot.bat. Python 3 is required. The launcher checks/installs the Coinbase Advanced Trade SDK and optionally ttkbootstrap, then launches the GUI.

IMPORTANT
Start in PAPER mode after upgrading. Fee tiers, liquidity and volatility differ by market. Trading crypto can lose money and no setting guarantees profit.
