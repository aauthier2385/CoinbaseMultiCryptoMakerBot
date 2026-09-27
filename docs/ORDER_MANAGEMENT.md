# v2.2 Order-Management Design

## Entry sequence

1. Receive a valid strategy entry signal.
2. Fetch the selected product metadata and available USD balance.
3. Treat configured order size as a maximum allocation.
4. Subtract the configured funding reserve.
5. Calculate base quantity and round down to the product's valid increment.
6. Fetch a fresh bid/ask and calculate a passive post-only BUY price.
7. Submit the maker order.
8. Only begin maker repricing if Coinbase accepted the order.
9. Before replacing an accepted order, cancel it and confirm terminal cancellation before reusing the funds.

## Insufficient funds

An insufficient-funds rejection is not treated like an unfilled maker order. The bot refreshes funding information, resizes where appropriate, and performs only the configured controlled retry. Continued funding failure aborts the current entry. Repeated funding problems trigger the funding circuit breaker.

## Post-only rejection

If the limit price is no longer passive when Coinbase processes the request, the book is refreshed and the bot recalculates a valid maker price rather than repeatedly resubmitting a stale price.

## Logging

Important diagnostic events include:

- `ORDER_RESIZED`
- `ENTRY_ABORT_FUNDING`
- `CANCEL_UNCONFIRMED`

These events are intended to make it possible to separate strategy failures from execution/funding failures when reviewing `orders.csv`.
