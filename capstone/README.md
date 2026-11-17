# Capstone: a live trend bot on Bybit

The code of Lecture 24: a simple short-term trend strategy on Bybit's BTCUSDT perpetual, run from backtest
to a live testnet account, with every order, fill and decision recorded and reconciled against the
exchange, and a read-only dashboard. Built step by step; this folder grows with each step.

**Free and safe by design.** Market data is public and needs no account. Trading runs only on Bybit's
free **testnet** (play money). Keys are created by you, kept outside the repository, never printed.

## The layers

| Folder | Its one job | Status |
|---|---|---|
| `connectors/` | Talk to Bybit and understand its API: public REST (instrument details, candles, server time), the public WebSocket (order book, trades) with heartbeat, reconnect and gap checks, the local order book, one-minute bars | Step 1, done |
| `database/` | Remember everything and make it checkable: numbered migrations; orders, their history, fills, positions, reconciliation, decisions, bot events, bars. SQLite by default, Postgres by changing `DATABASE_URL` | Step 1, done |
| `security/` | Keep secrets out of every log line and message (`scrub()`, `install_log_scrubbing()`) | Step 1, done |
| `executors/` | Sign requests and send, cancel and amend orders, with our own order ids | Step 2 |
| `strategies/trend/` | The strategy: a simple signal, stop loss, take profit, time limit, trailing stop, cooldown, kill switch; settings in `params.toml` | Step 3 |
| `backtest/` | The same strategy code run on recorded bars | Step 3 |
| `run_bot.py` | The live loop: reconcile at start, heartbeat, reconnect, kill switch | Step 4 |
| `dashboard/` | Read-only pages: health, position, strategy, orders and fills, reconciliation, live against backtest | Step 5 |

Each layer may call the ones below it, never the ones above: the strategy never talks to Bybit directly,
and nothing in `connectors/` decides anything.

## Step 1: record the market (no account needed)

Python 3.11 or later, with `requests` and `websockets` (`pip install requests websockets`). From the
repository root:

```
python -m capstone.database.migrate                      # create the database (capstone/data/capstone.db)
python -m capstone.tools.record_market --minutes 5       # past candles, then five minutes of the live feed
python -m capstone.tests.test_step1                      # tests, no network needed
```

The recorder logs one line per finished one-minute bar and, at the end, the feed's health: connections,
reconnects, book gaps, trades and book updates. The same feed runs on the testnet with `--env testnet`;
its book is a different, much quieter market, fine for checking the plumbing, not for realistic fills.

## Rules that hold in every file

1. **Verify every claim about the exchange live**, and write down when it was checked. The docstrings say
   what was verified and how.
2. **`Decimal`, never `float`**, for prices, sizes and fees: money is stored and read back exact.
3. **Secrets never leave a program as text.** Every program calls `install_log_scrubbing()` after setting
   up logging; credentials live in `capstone/configs/.env` (git-ignored, see `configs/env.example`), never
   in code, chat, screenshots or logs. `tests/test_step1.py` fails if a secret file is tracked or a
   program logs without scrubbing.
4. **One bad message never stops the bot**, and a book that may be wrong is never traded on.
