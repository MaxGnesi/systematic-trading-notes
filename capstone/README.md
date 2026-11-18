# Capstone: a live trend bot on Deribit

The code of Lecture 24: a simple short-term trend strategy on Deribit's BTC perpetual (`BTC-PERPETUAL`),
run from backtest to a live **testnet** account, with every order, fill and decision recorded and
reconciled against the exchange, and a read-only dashboard. Built step by step; this folder grows with
each step.

**Free and safe by design.** Market data is public and needs no account. Trading runs only on Deribit's
free testnet (play money). Keys are created by you, kept outside the repository, never printed.

**Why Deribit.** The order-book lectures used Bybit's data, but exchanges are not open to everyone:
Bybit's testnet refused an account from our country for regulatory reasons. That is a lesson in itself:
check where a venue is available before building on it. And it shows what the connector layer is for:
only `connectors/` knows the exchange; swapping it leaves everything else unchanged.

## The layers

| Folder | Its one job | Status |
|---|---|---|
| `connectors/` | Talk to Deribit and understand its API: public REST (instrument details, candles, server time), the public WebSocket (order book, trades) with heartbeat, reconnect and gap checks; an exchange-neutral local order book; one-minute bars | Step 1, done |
| `database/` | Remember everything and make it checkable: numbered migrations; orders, their history, fills, positions, reconciliation, decisions, bot events, bars. SQLite by default, Postgres by changing `DATABASE_URL` | Step 1, done |
| `security/` | Keep secrets out of every log line and message (`scrub()`, `install_log_scrubbing()`) | Step 1, done |
| `executors/` | Sign in by signature (Ed25519) and send, amend and cancel orders, with our own labels; read balance, position and open orders | Step 2, done |
| `strategies/trend/` | The strategy: a simple signal, stop loss, take profit, time limit, trailing stop, cooldown, kill switch; settings in `params.toml` | Step 3 |
| `backtest/` | The same strategy code run on recorded bars | Step 3 |
| `run_bot.py` | The live loop: reconcile at start, heartbeat, reconnect, kill switch | Step 4 |
| `dashboard/` | Read-only pages: health, position, strategy, orders and fills, reconciliation, live against backtest | Step 5 |

Each layer may call the ones below it, never the ones above: the strategy never talks to the exchange
directly, and nothing in `connectors/` decides anything.

## The instrument

`BTC-PERPETUAL` is an **inverse** contract: amounts are in USD, in steps of 10 USD (one contract), while
profit, loss and margin are in BTC. Tick 0.5 USD. Checked live on mainnet and testnet, 17 November 2026.

## Step 1: record the market (no account needed)

Python 3.11 or later, with `requests` and `websockets` (`pip install requests websockets`). From the
repository root:

```
python -m capstone.database.migrate                      # create the database (capstone/data/capstone.db)
python -m capstone.tools.record_market --minutes 5       # past candles, then five minutes of the live feed
python -m capstone.tests.test_step1                      # tests, no network needed
```

The recorder logs one line per finished one-minute bar and, at the end, the feed's health: connections,
reconnects, book gaps, heartbeats, trades and book updates. `--env testnet` records the testnet's market,
the one the test orders of step 2 will meet.

## Step 2: the testnet account (your own free account and key)

Create a free account on **test.deribit.com**, a **subaccount** for the bot (its own funds and positions,
so nothing else you run on the testnet interferes), move some test BTC to it, and create an API key on the
subaccount: your own **Ed25519** public key (`openssl genpkey -algorithm ed25519 -out key.pem`, then
`openssl pkey -in key.pem -pubout`), permissions **Account: Read** and **Trade: Read & Write** only, never
Wallet. Put the Client ID and the path to the private key in `capstone/configs/.env` (see `env.example`).
Never paste them anywhere else.

```
pip install cryptography
python -m capstone.tools.check_account        # read-only: login by signature, balance, position
python -m capstone.tools.safe_order_test      # a post-only order that cannot fill: submit, amend, cancel, reconcile
python -m capstone.tests.test_step2           # signature, safety rules, history, reconciliation; no network
```

The safe test prices its buy about 2.5% below the best bid: inside Deribit's price band (about +-3% of the
mark), so it is accepted, and far enough below the market not to fill in the seconds it lives.

## Rules that hold in every file

1. **Verify every claim about the exchange live**, and write down when it was checked. The docstrings say
   what was verified and how.
2. **`Decimal`, never `float`**, for prices, sizes and fees: money is stored and read back exact.
3. **Secrets never leave a program as text.** Every program calls `install_log_scrubbing()` after setting
   up logging; credentials live in `capstone/configs/.env` (git-ignored, see `configs/env.example`), never
   in code, chat, screenshots or logs. `tests/test_step1.py` fails if a secret file is tracked or a
   program logs without scrubbing.
4. **One bad message never stops the bot**, and a book that may be wrong is never traded on.
