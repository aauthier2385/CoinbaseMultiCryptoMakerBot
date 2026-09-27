# Changelog

## v2.2

### Multi-crypto
- Added BTC-USD, ETH-USD, XRP-USD, and SOL-USD selection.
- Added per-market state, signal, order, trade, and intelligence logging.

### Order management
- Added balance-aware sizing and funding reserve.
- Added product increment handling and downward rounding.
- Replaced repeated insufficient-funds loops with controlled resize/retry/abort behavior.
- Added funding circuit breaker.
- Added confirmed cancellation before funds are reused for repricing.
- Improved passive post-only price handling.
- Added order-management diagnostic events.

### Market Intelligence
- Added BULL / BEAR / RANGE classification and confidence.
- Added advisory regime-performance tracking.
- Added context for spread, momentum, volatility, maker fills, fees, exit reason, and net P&L.
- Learning remains recommendation/test-only and does not automatically change live parameters.

## v2.1

- Baseline maker-order architecture used for the v2.2 build.
- Post-only maker entry and take-profit with market risk exits.
- EMA/trend, ATR, volume, spread, volatility sizing, cooldown, circuit breaker, and hourly trend gate.
