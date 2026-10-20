# Lecture 11: Three Trend Systems, End to End

*Systematic Trading: Lecture Notes (MSc) · Oct 20, 2026 · Max Gnesi*

Part II built the pieces one at a time: what a market offers (Lecture 5), how a design decides what is captured (Lecture 6), how to compare systems (Lecture 7), filters (Lecture 8) and sizing (Lecture 9). This capstone puts them together, building three trend systems end to end on futures, one from each family of Lecture 6, from the raw data to a running system. *Draft: written step by step; §1 and §2 so far.*

## 1. The question of this lecture

What does it take to build a trend system properly, from data to positions, and what do the choices of Part II change once they are made together rather than one at a time?

| System | Family (Lecture 6) | What it teaches that the others cannot |
|---|---|---|
| EWMAC, blended over a few speeds | Linear filters | A continuous forecast that is always in the market; partial trading, costs and the choice of speed matter most |
| Turtle-style breakout | Channel breakouts | On-or-off positions with flat periods; stops built into the system; time in the market and the marginal contribution of a system that is often idle |
| Kalman slope, weighted by its uncertainty | Model-based | A system that knows how sure it is: positions scale with the evidence, and the surprises flag when the model is wrong |

Each system goes through the same steps:

| Step | From |
|---|---|
| Get the data and build continuous futures series | §2–§3 of this lecture |
| Check what the market offers: drift, frictions, gaps | Lecture 5 |
| Design: direction, speed, exits | Lecture 6 |
| Signal, forecast, sizing, partial trading, costs | Lectures 6 and 9 |
| Compare fairly; marginal contribution to the other systems | Lecture 7 |
| Filters, if any earn their place | Lecture 8 |
| Combine the three; run them live | This lecture, and Lecture 4b, §4.3, for storing state |

The capstone uses futures rather than the ETFs of Lectures 5 to 9. Futures are what trend followers trade: they are margined, so risk rather than cash is the scarce resource (Lecture 7, §4.4), they cover every asset class, and they are cheap to trade. They also bring a problem ETFs hide: every contract expires, so a backtest needs one series stitched together from many contracts. §3 builds it.

## 2. Getting futures data

### 2.1 What a futures backtest needs

| Data | Why |
|---|---|
| Daily open, high, low, close and volume for every contract month, not only the front month | To decide when to roll and to build an adjusted continuous series (§3) |
| Open interest per contract, if possible | One of the rules for when to roll |
| The contract specifications: tick size, multiplier, expiry calendar | To turn price moves into money and positions into contracts |

Free sources usually provide only a single front-month series, unadjusted, with a jump on every roll date. A trend rule reads those jumps as moves that never happened, so for this lecture the individual contract months are needed.

### 2.2 Where to get it

| Source | What it offers | Cost | Fits this lecture |
|---|---|---|---|
| Yahoo Finance (for example ES=F) | One front-month series per market, unadjusted | Free | Only to look at; not for a backtest |
| Databento | Every contract month of CME, ICE and other exchanges, daily to tick level; continuous symbols that roll by calendar, volume or open interest, delivered unadjusted | Pay per request; USD 125 of free credit on sign-up; the cost of a request can be checked before downloading | **Yes**: the choice for this lecture |
| Interactive Brokers | Historical data through a brokerage account | Free with an account, with request limits and short histories for expired contracts | For live trading more than for long backtests |
| Paid end-of-day vendors (for example Norgate, Portara, CSI Data) | Clean, already back-adjusted continuous series and contract histories | Subscription or one-off purchase | When long, clean histories are worth paying for |

### 2.3 Step by step: a Databento account

1. **Sign up** at databento.com with an email address. The free credit is added to the account; check its terms and expiry in the portal.
2. **Create an API key** in the portal. The key identifies you and spends your credit, so treat it like a password.
3. **Store the key outside the code.** Set it as an environment variable, `DATABENTO_API_KEY`, or in a `.env` file that is never committed; the repository's `.gitignore` excludes `.env` files. A notebook should read the key from the environment, never contain it.
4. **Install the client:** `pip install databento`.
5. **Check the cost before every download.** The client has a free cost estimate; a request for daily bars is cheap, a request for tick data can be expensive.
6. **Download daily bars for every contract month of one market**, then check the result before adding markets.

```python
import os
import databento as db

client = db.Historical(os.environ["DATABENTO_API_KEY"])     # the key comes from the environment
request = dict(dataset="GLBX.MDP3",                         # CME Globex
               schema="ohlcv-1d",                           # daily open, high, low, close, volume
               symbols=["ES.FUT"], stype_in="parent",       # every contract month of the E-mini S&P 500
               start="2015-01-01", end="2026-10-01")
print("estimated cost, USD:", client.metadata.get_cost(**request))
bars = client.timeseries.get_range(**request).to_df()       # only after checking the cost
```

Dataset names, symbols and parameters follow Databento's documentation; check them against the current version before running.

### 2.4 The markets

One market per asset class keeps the capstone readable and still diversified.

| Asset class | Market | Exchange |
|---|---|---|
| Equity index | E-mini S&P 500 | CME |
| Government bonds | 10-year US Treasury note | CBOT |
| Energy | WTI crude oil | NYMEX |
| Metals | Gold | COMEX |
| Currencies | Euro FX | CME |

*Next: §3, building continuous series: when to roll, how to back-adjust, and what the roll yield is.*
