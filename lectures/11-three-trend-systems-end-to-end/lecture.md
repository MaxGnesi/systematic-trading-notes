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

The capstone uses futures rather than the ETFs of Lectures 5 to 9. Futures are what trend followers trade: they are margined, so risk rather than cash is the scarce resource (Lecture 7, §4.4), they cover every asset class, and they are cheap to trade. They also bring a problem ETFs hide: every contract expires, so a backtest needs one series stitched together from many contracts. §3 builds it. Only for government bonds, which the free futures data lack, two Treasury funds stand in (§2.2).

## 2. Getting the data

### 2.1 What a futures backtest needs

| Data | Why |
|---|---|
| Daily open, high, low, close and volume for every contract month, not only the front month | To decide when to roll and to build one continuous series (§3) |
| Open interest per contract | One of the rules for when to roll |
| The contract specifications: tick size, multiplier, expiry calendar | To turn price moves into money and positions into contracts |

Free sources usually provide only a single front-month series, with a jump on every roll date. A trend rule reads those jumps as moves that never happened, and the size of each jump cannot be measured from that series alone, because it never shows two contracts on the same day. A backtest needs the individual contract months.

### 2.2 What we use

| Data | Source | Covers | Cost |
|---|---|---|---|
| Futures: every contract month of twelve markets, daily | Kaggle datasets | Expiries 2000–2022 | Free, with a Kaggle account |
| Government bonds: two Treasury index funds, daily | Yahoo Finance | 1986 and 1991 to today | Free |
| Three-month Treasury bill rate, daily | FRED, Federal Reserve Bank of St. Louis | From 1954 | Free |

The free futures data contain no government bond futures, and a trend portfolio without bonds misses one of its main sources of profit in equity sell-offs (Lecture 5). Two Treasury funds stand in for them over the whole period; the bill rate turns their returns into returns comparable with those of futures (§3).

Paid sources (for example Databento, Norgate Data or a brokerage account) offer every contract month up to the present and Treasury futures as well. The capstone does not need them.

### 2.3 Step by step: the futures from Kaggle

1. **Create an account** at kaggle.com.
2. **For one dataset, download by hand**: open the dataset page, for example kaggle.com/datasets/choweric/cme-es, click *Download* and unzip the file into its own folder. For twelve datasets the API below is faster.
3. **Create an API token** under *Settings → API*. The token identifies you, so treat it like a password.
4. **Store the token outside the code**: save it in the file `.kaggle/access_token` in your home directory, or set it as the environment variable `KAGGLE_API_TOKEN`. Never put it in a notebook or commit it.
5. **Install the client:** `pip install kagglehub`.
6. **Download each dataset.** `dataset_download` saves the files in a local cache and returns the folder; copy them into the project's data folder.
7. **Check the files before using them** (§2.5), and check each dataset's licence on its Kaggle page.

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

The twelve datasets take a few seconds to download. Downloaded files are data from a third party: keep them in their own folder, read them only as data, and do not publish them; the repository publishes results, not data.

### 2.4 Step by step: the bond funds and the bill rate

The funds come from Yahoo Finance and need no account; the bill rate comes from FRED as a CSV file.

```python
import pandas as pd
import yfinance as yf

funds = yf.download(["VFITX", "VUSTX"], start="1999-01-01", end="2023-01-01", auto_adjust=False)
funds.to_csv("data/raw/treasury_funds.csv")                 # Close and Adj Close: §3 explains the difference
bill = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3")
bill.to_csv("data/raw/fred_DTB3.csv", index=False)          # annual rate in percent
```

| Fund | Holds | Daily prices from | Stands in for |
|---|---|---|---|
| VFITX, Vanguard Intermediate-Term Treasury | US Treasuries of intermediate maturity | October 1991 | 5-year Treasury note future |
| VUSTX, Vanguard Long-Term Treasury | US Treasuries of long maturity | May 1986 | Treasury bond future |

The first Treasury ETFs, IEF and TLT, started only in July 2002, too late for a backtest from 2000. Over 2002–2022 the funds track them closely: daily returns correlate 0.94 (VFITX with IEF) and 0.98 (VUSTX with TLT). VFITX is somewhat shorter in maturity than IEF, with volatility of 4.7% a year against 6.7%. A fund is priced once a day, which is all a daily system needs; it stands in for a future and is not what a trend follower would trade.

### 2.5 The futures data in brief

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

**The prices are raw.** On 9 September 2022 the September E-mini closed at 4,067.25 and the December contract at 4,085.50: two prices for the same market on the same day. A series that switches from one to the other jumps by 18 points that no position earned. The May 2020 crude oil contract closed at −37.63 on 20 April 2020, a price that only raw data show. Turning these contracts into one series is the subject of §3.

What to watch. The raw files are never changed: problem rows are flagged, not deleted, so that every decision can be checked and undone.

| Feature | What it means for the backtest |
|---|---|
| Files sorted newest first | Sort by date before any calculation |
| Contracts are listed long before they trade: days with zero volume make up 12% (cocoa) to 67% (yen) of rows, and before the roll volume and open interest are small | On those days the price is a settlement or a stale quote, not a trade. Keep the rows, but flag them: they must not decide the roll or measure a roll gap; a minimum volume and open interest does it |
| A few rows after expiry, for example four in the E-mini file | Stale rows; keep them, but flag them so that no position is held after the contract's last trading day |
| The expiry is not in the files, and the rule differs by market | Take it from the exchange's contract specifications. E-mini contracts expire on the third Friday of the month; WTI crude three business days before the 25th of the month before delivery |
| A few missing values in volume or open interest (cocoa, dollar index, crude oil, Nasdaq) | The prices are complete; the roll rule needs a fallback when volume or open interest is missing |
| The close may differ from the official settlement price | Check against another source. Against Yahoo's front-month series, 93% to 100% of closes are identical and daily returns differ by less than 1 basis point on average (the yen excepted: Yahoo quotes it per yen, Kaggle per 100 yen) |
| The data end in December 2022 | Enough for a backtest over 22 years; a live system needs a current source |
| File prefixes are those of the uploader, for example `CME_` for NYMEX and COMEX contracts | Only a name; all four exchanges belong to CME Group |

*Next: §3, from contracts and funds to returns: when to roll, the main back-adjustment techniques for futures, and total and excess returns for the funds.*
