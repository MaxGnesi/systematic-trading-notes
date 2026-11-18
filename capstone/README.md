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
| `strategies/trend/` | The strategy: an hourly trend at two speeds (2 and 7 days), sized by six months of volatility, a 5-sigma take profit per speed, decisions at 23 minutes past the hour plus a random delay; settings in `params.toml`, checked by `params.py` | Step 3, done |
| `backtest/` | Download Deribit's history (one-minute candles, funding) and replay the strategy's own code on it, hour by hour, with the rivals of the hypotheses | Step 3, done |
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

## Step 3: the strategy and its backtest (no account needed)

The strategy and its rivals were fixed before any result: `lectures/24-a-live-trend-bot/results/hypotheses.md`.

```
python -m capstone.backtest.download --start 2019-01 --end 2026-10   # about 20 minutes, resumable
python -m capstone.backtest.run_backtest                             # strategy and rivals, about a minute
python -m capstone.tests.test_step3                                  # settings, take profit, inverse accounting
```

The account is kept in BTC, as the testnet account is: BTC-PERPETUAL is inverse, so a position of `A` USD
from price `p0` to `p1` earns `A x (1/p0 - 1/p1)` BTC. Fees (taker 3.5 bp), half a tick of spread and
Deribit's recorded funding are charged. Change any value in `strategies/trend/params.toml` and run again:
that is the student's job, within the ranges `params.py` allows.

## Step 4: run it 24 hours a day

The bot refuses to start twice: it locks `capstone/data/bot.lock` and exits with code 3 if another copy holds the lock. Every start reconciles with the exchange first.

| Where | How | Memory |
|---|---|---|
| Any machine, by hand | `python -X utf8 -m capstone.run_bot` from the repository root; Ctrl+C stops it and leaves the position as it is | the bot only |
| A Windows PC | `capstone\tools\supervise.bat` restarts the bot a minute after any exit; start it at log-on with Task Scheduler (below); create `capstone\data\NO_RESTART` to stop the loop | a few MB more |
| A Linux server | a systemd service with `Restart=always` (exercise in Lecture 24) | the bot only |
| Any machine with Docker | `docker compose -f capstone/docker-compose.yml up -d --build`; `restart: unless-stopped` | 1 to 2 GB for Docker Desktop on a PC |

**Task Scheduler, in PowerShell** (run once; adjust the path):

```powershell
$repo = "C:\path\to\systematic-trading-notes"
$bat = Join-Path $repo "capstone\tools\supervise.bat"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c start `"capstone bot`" /min `"$bat`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Capstone trend bot" -Action $action -Trigger $trigger -Settings $settings
```

The supervisor writes `capstone/data/supervisor.log` (each start and exit) and the bot's own log to `capstone/data/bot.out.log`. Never run two of these ways at once on the same account: the lock stops a second bot on the same machine, not one on another machine or in a container with its own data folder.

## Rules that hold in every file

1. **Verify every claim about the exchange live**, and write down when it was checked. The docstrings say
   what was verified and how.
2. **`Decimal`, never `float`**, for prices, sizes and fees: money is stored and read back exact.
3. **Secrets never leave a program as text.** Every program calls `install_log_scrubbing()` after setting
   up logging; credentials live in `capstone/configs/.env` (git-ignored, see `configs/env.example`), never
   in code, chat, screenshots or logs. `tests/test_step1.py` fails if a secret file is tracked or a
   program logs without scrubbing.
4. **One bad message never stops the bot**, and a book that may be wrong is never traded on.
