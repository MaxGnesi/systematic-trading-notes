# Lecture 24 (capstone): hypotheses, fixed before any result

Fixed 18 November 2026, with the user, before the strategy was coded or backtested. Every change after
a result is dated and labelled below, never made silently.

## The strategy, in one sentence

Hold Deribit's BTC perpetual long or short in the direction of an hourly trend, blended from two speeds
in the region Lecture 20 found working, sized by volatility over the past six months, and cut a speed's
trade when it has gained 5 sigma; a kill switch stops everything on a 10% drawdown or an unhealthy feed.

| Part | Rule | Source |
|---|---|---|
| Data | Hourly bars of BTC-PERPETUAL (Deribit; inverse contract, amounts in USD), built from one-minute candles and **ending at 23 minutes past the hour** | Lecture 20: decide once an hour; looking from 5 minutes to 4 hours hardly matters |
| Signal | EWMAC: fast average minus slow average, divided by the volatility of price changes; **fast spans 2 and 7 days**, slow span 4 times the fast; each scaled by its own average absolute size; blended with equal weights | Lecture 20's speed curve (2 days on the plateau, 7 days at its slow edge, still positive in both periods); the user's choice of two speeds about 3.5 times apart |
| Size | Signal x 10% annual target / the volatility of hourly returns over the past **6 months** (a setting from 6 to 12 months) | The user; Lecture 9 |
| Take profit | Per speed: once the open gain since that speed's signal last changed reaches **5 sigma** (its risk over its own horizon), that speed goes flat until its signal changes | The user; Lecture 8 §4.8 |
| Stop | None beyond the signal | Lecture 23: stops inside the noise pay fees |
| Buffer | Trade only when the target is more than 10% of its average size away from the position | Lecture 20 |
| Decision time | **23 minutes past each hour, plus a random delay of 0 to 120 s** drawn fresh each hour (the backtest uses the same draws) | Change of 18 Nov 2026 below |
| Execution | **Market orders (taker)** at the hourly decision; a patient post-only entry is a setting and a rival | The user: trend should take liquidity; Deribit fees checked live 18 Nov 2026: maker 1.5 bp, taker 3.5 bp |
| Kill switch | Close everything and stop on a drawdown of 10% from the peak of equity, or an unhealthy feed (stale or invalid book); restart by hand | Hummingbot's drawdown kill switch; Lecture 22 §9 |
| Settings | Every number in `params.toml`, with allowed ranges | The course author's Deribit backend |

## Rivals in the backtest

1. Each speed alone: 2 days, 7 days.
2. The blend without the take profit.
3. The blend with the patient entry instead of market orders.
4. **Timing inside the delay window** (the user, 18 Nov 2026): after the decision, trade at the end of the first minute if the price has moved in our favour by at least x bp (x = 2, 5, 10), else at the end of the second minute; market orders both ways; one-minute closes only, so nothing ahead is seen.

## Expectations

1. The blend's Sharpe ratio after costs lies between the two single speeds', with a milder worst month than either.
2. The 5-sigma take profit leaves the Sharpe ratio about unchanged (within its 90% band) and raises the skew of monthly returns, as in Lecture 8.
3. On Deribit's fees the patient entry changes the result by less than its 90% band: the 2 bp fee gap is small, and the fills it misses are the trend's best.
4. Timing inside the window changes the average fill price by less than its 90% band: if the price over two minutes is a fair game, no rule for when to trade within the window improves the expected price (optional stopping); any gain would need short-term predictability, of which Lecture 19 found little.

## Data and samples

Deribit's public candles of BTC-PERPETUAL, hourly. The settings above are not chosen on Deribit's data: they
come from Lecture 20's work on BTCUSDT (Bybit and Binance, chosen on 2021-2024). So the whole Deribit history
is out of sample for the choice of speeds; results are reported by year. Costs: the taker fee of 3.5 bp,
half a tick of spread, and funding as Deribit reports it. Bands from a block bootstrap of months.

## Live

On a Deribit testnet subaccount, with the same code. Measured: slippage against the price at the decision,
fills, reconciliation, uptime of the feed, and the gap between live and backtest over the same days.

## Changes before any result

- **18 November 2026, the user: do not trade at round hours.** Decisions at 23 minutes past the hour, away
  from the whole hour and the quarter hours, plus a random delay of 0 to 120 s so the timing is not
  predictable. Reason: volume bursts, quote withdrawals and wider spreads cluster just after whole minutes and
  hours (Lectures 21 and 23), fills in the first seconds of :00 and :30 were worse (Lecture 22, H5), and many
  bots act at the quarter hours; Lecture 20 found the signal insensitive to when it looks. Settings
  `decision_minute` and `jitter_seconds`. Made before the strategy was coded or run.
- **18 November 2026, the user: look for a better price inside the delay window.** Added as rival 4 with
  expectation 4, before any result. A proper test at the level of seconds needs tick data: an exercise.
