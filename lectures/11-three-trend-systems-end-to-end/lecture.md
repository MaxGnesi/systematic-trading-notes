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
| Yahoo Finance (for example ES=F) | One front-month series per market, unadjusted | Free | Only to look at and to cross-check; not for a backtest |
| Kaggle datasets | Community uploads; the ones used here hold every contract month of twelve futures markets, daily, 2000–2022 | Free, with a Kaggle account; no payment card | **Yes**: the data of this lecture |
| Databento | Every contract month of CME, ICE and other exchanges, daily to tick level, up to the present | Pay per request; USD 125 of free credit on sign-up; the cost of a request can be checked before downloading | To extend the data beyond 2022 or add markets (§2.5) |
| Interactive Brokers | Historical data through a brokerage account | Free with an account, with request limits and short histories for expired contracts | For live trading more than for long backtests |
| Paid end-of-day vendors (for example Norgate, Portara, CSI Data) | Clean, already back-adjusted continuous series and contract histories | Subscription or one-off purchase | When long, clean histories are worth paying for |

### 2.3 Step by step: the data from Kaggle

1. **Create an account** at kaggle.com.
2. **For one dataset, download by hand**: open the dataset page, for example kaggle.com/datasets/choweric/cme-es, click *Download* and unzip the file into its own folder. For twelve datasets the API below is faster.
3. **Create an API token** under *Settings → API*. The token identifies you, so treat it like a password.
4. **Store the token outside the code**: save it in the file `.kaggle/access_token` in your home directory, or set it as the environment variable `KAGGLE_API_TOKEN`. Never put it in a notebook or commit it.
5. **Install the client:** `pip install kagglehub`.
6. **Download each dataset.** `dataset_download` saves the files in a local cache and returns the folder; copy them into the project's data folder.
7. **Check the files before using them** (§2.4), and check each dataset's licence on its Kaggle page.

```python
import shutil
from pathlib import Path
import kagglehub

DATASETS = ["cme-es", "cme-nasdaq", "cme-euro", "cme-jpy", "ice-us-dollar-index", "nymex-cl",
            "nymex-ng", "comex-gc", "cbot-corn", "cbot-soybeans", "cbot-wheat", "ice-cocoa"]
for name in DATASETS:
    cache = kagglehub.dataset_download(f"choweric/{name}")      # the token is read from ~/.kaggle or the environment
    shutil.copytree(cache, Path("data/raw/kaggle") / name, dirs_exist_ok=True)
```

The twelve datasets take a few seconds to download. Downloaded files are data from a third party: keep them in their own folder and read them only as data.

### 2.4 The dataset in brief

Twelve datasets of daily data, one per market, all uploaded by the same author (choweric) with the same layout. Each holds one CSV file per contract month, and the file name gives the contract: `CME_ESZ2022.csv` is the E-mini S&P 500 (ES) contract for December (Z) 2022. In total there are 1,832 contracts, 67 MB.

| Month code | F | G | H | J | K | M | N | Q | U | V | X | Z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |

| Column | Meaning |
|---|---|
| Date | Trading day, one row per day; the files are sorted from newest to oldest |
| Open, High, Low, Close | Daily prices of that contract, as traded: **not adjusted** |
| Volume | Contracts traded that day |
| Open Interest | Contracts open at the end of the day |

| Asset class | Market | Exchange | Contract months | Expiries |
|---|---|---|---|---|
| Equity index | E-mini S&P 500 | CME | Mar, Jun, Sep, Dec | 2000–2022 |
| | E-mini Nasdaq-100 | CME | Mar, Jun, Sep, Dec | 2000–2022 |
| Currencies | Euro FX | CME | Mar, Jun, Sep, Dec; every month from 2017 | 2000–2022 |
| | Japanese yen | CME | Mar, Jun, Sep, Dec | 2000–2022 |
| | US dollar index | ICE | Mar, Jun, Sep, Dec | 2000–2022 |
| Energy | WTI crude oil | NYMEX | Every month | 2000–2022 |
| | Natural gas | NYMEX | Every month | 2000–2022 |
| Metals | Gold | COMEX | Every month (most trading in Feb, Apr, Jun, Aug, Dec) | 2000–2022 |
| Agriculture | Corn | CBOT | Mar, May, Jul, Sep, Dec | 2000–2022 |
| | Soybeans | CBOT | Jan, Mar, May, Jul, Aug, Sep, Nov | 2000–2022 |
| | Wheat | CBOT | Mar, May, Jul, Sep, Dec | 2000–2022 |
| | Cocoa | ICE US | Mar, May, Jul, Sep, Dec | 2000–2022 |

**The prices are raw.** On 9 September 2022 the September E-mini closed at 4,067.25 and the December contract at 4,085.50. That is two prices for the same market on the same day, and a series that switches from one to the other jumps by 18 points. The gap is the cost of carry: three months of interest minus dividends. The May 2020 crude oil contract closed at −37.63 on 20 April 2020, a price that only raw data show. Building one series out of these contracts is the subject of §3.

What to watch. The raw files are never changed: problem rows are flagged, not deleted, so that every decision can be checked and undone.

| Feature | What it means for the backtest |
|---|---|
| Files sorted newest first | Sort by date before any calculation |
| Contracts are listed long before they trade: days with zero volume make up 12% (cocoa) to 67% (yen) of rows, and before the roll volume and open interest are small | On those days the price is a settlement or a stale quote, not a trade. Keep the rows, but flag them: they must not decide the roll or measure a roll gap; a minimum volume and open interest does it |
| A few rows after expiry, for example four in the E-mini file | Stale rows; keep them in the raw files, but flag them so that no position is held after the contract's last trading day |
| The expiry is not in the files, and the rule differs by market | Take it from the exchange's contract specifications. E-mini contracts expire on the third Friday of the month; WTI crude three business days before the 25th of the month before delivery |
| A few missing values in volume or open interest (cocoa, dollar index, crude oil, Nasdaq) | The prices are complete; the roll rule needs a fallback when volume or open interest is missing |
| The close may differ from the official settlement price | Spot-check a few dates against another source, for example Yahoo's front-month series |
| No government bond futures | A trend portfolio without bonds misses one of its main sources of profit in equity sell-offs (Lecture 5); a bond market can be added from another source (§2.5) |
| The data end in December 2022 | Enough for a backtest over 22 years; a live system needs a current source |
| File prefixes are those of the uploader, for example `CME_` for NYMEX and COMEX contracts | Only a name; all four exchanges belong to CME Group |

### 2.5 Extending the data: a Databento account

To add markets, such as the 10-year Treasury note, or to extend the series past 2022:

1. **Sign up** at databento.com. The free credit is added to the account; check its terms and expiry in the portal. Payment goes through card checks, and some cards, prepaid ones for example, may be declined.
2. **Create an API key** in the portal and store it like the Kaggle token: as the environment variable `DATABENTO_API_KEY`, or in a `.env` file that is never committed (the repository's `.gitignore` excludes `.env` files).
3. **Install the client** (`pip install databento`) and **check the cost before every download**: the estimate is free, daily bars are cheap, tick data can be expensive.

```python
import os
import databento as db

client = db.Historical(os.environ["DATABENTO_API_KEY"])     # the key comes from the environment
request = dict(dataset="GLBX.MDP3",                         # CME Globex
               schema="ohlcv-1d",                           # daily open, high, low, close, volume
               symbols=["ZN.FUT"], stype_in="parent",       # every contract month of the 10-year Treasury note
               start="2015-01-01", end="2026-10-01")
print("estimated cost, USD:", client.metadata.get_cost(**request))
bars = client.timeseries.get_range(**request).to_df()       # only after checking the cost
```

Dataset names, symbols and parameters follow Databento's documentation; check them against the current version before running.

*Next: §3, building continuous series: when to roll, how to back-adjust, and what the roll yield is.*
