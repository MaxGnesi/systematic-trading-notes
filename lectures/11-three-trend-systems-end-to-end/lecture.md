# Lecture 11: Three Trend Systems, End to End

*Systematic Trading: Lecture Notes (MSc) · Oct 20, 2026 · Max Gnesi*

Part II built the pieces one at a time: what a market offers (Lecture 5), how a design decides what is captured (Lecture 6), how to compare systems (Lecture 7), filters (Lecture 8) and sizing (Lecture 9). This capstone puts them together, building three trend systems end to end on futures, from the raw data to a combined portfolio. Data: twelve futures markets from Kaggle and two Treasury funds, 1999–2022; results from 2001, after two years of warm-up.

## 1. The question of this lecture

What does it take to build a trend system properly, from data to positions, and what do the choices of Part II change once they are made together rather than one at a time?

| System | Family (Lecture 6) | What it teaches that the others cannot |
|---|---|---|
| EWMAC, blended over a few speeds | Linear filters | A continuous forecast that is always in the market; partial trading, costs and the choice of speed matter most |
| Turtle-style breakout | Channel breakouts | On-or-off positions with flat periods; stops built into the system; time in the market and the marginal contribution of a system that is often idle |
| Cross-sectional momentum | Linear filters, applied across markets rather than over time (Lecture 6, §2.4 and card 11) | A relative trend: long the strongest markets and short the weakest at the same time, so its net exposure, and its payoff, differ from the other two |

A model-based system, the Kalman slope of Lecture 4, was the first candidate for the third place. On these markets it trades almost like EWMAC, with daily returns that correlate 0.93 to 0.95 at equal speed, and it earns less; it appears in §5 as a variant of EWMAC. Cross-sectional momentum correlates 0.64 to 0.69 with the other two at medium speed, adds return to EWMAC (§8.2) and takes the third place.

Each system goes through the same steps:

| Step | From |
|---|---|
| Get the data and build continuous futures series | §2–§3 of this lecture |
| Check what the market offers: drift, frictions, gaps | Lecture 5 |
| Design: direction, speed, exits | Lecture 6 |
| Signal, forecast, sizing, partial trading, costs | Lectures 6 and 9 |
| Compare fairly; marginal contribution to the other systems | Lecture 7 |
| Filters, if any earn their place | Lecture 8 |
| Combine the three into one portfolio; test out of sample | This lecture |

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

## 3. From contracts to returns

A futures position is held in one contract at a time and moved to the next before expiry. A backtest needs one series per market that records what such a position experienced. This section builds that series: when to roll (§3.2), how to remove the jump at each roll (§3.3), which series each kind of system needs and how to compute its profit (§3.4), where each method breaks (§3.5), what rolling itself earns or costs (§3.6), and the same steps for the two bond funds (§3.7).

### 3.1 One roll, three series

Crude oil in April 2020 shows the problem at its sharpest. The May contract (CLK20) was about to expire into a market with no storage left; the June contract (CLM20) was priced far higher. A position rolled from May into June at the close of 13 April, six trading days before May's expiry ([chart J.1](#j1-one-roll-three-series-31)).

| | 9 April | 13 April | Change |
|---|---|---|---|
| May contract, CLK20 | 22.76 | 22.41 | −0.35 (−1.5%) |
| June contract, CLM20 | 28.82 | 29.26 | +0.44 |
| **Raw series** (the contract held each day) | 22.76 (May) | 29.26 (June) | **+6.50 (+28.6%)** |
| **Additive series** (back-adjusted, §3.3) | 16.94 | 16.59 | −0.35 |
| **Ratio series** (back-adjusted, §3.3) | 32.02 | 31.53 | −1.5% |

Over these two days the position was in the May contract, which lost 35 cents. The raw series shows a gain of 6.50 dollars, 29%: the gap of 6.85 dollars between June and May on the roll day, which no position earned. A trend rule on the raw series would read it as a strong rally. Both adjusted series show what the position actually did: the additive series the loss in dollars, the ratio series the loss in percent. Their levels, 16.59 and 31.53, are not prices that ever traded; §3.3 explains why.

A week later, on 20 April, the May contract settled at **−37.63 dollars**, the first negative settlement of a major physically delivered futures contract. CME had prepared its systems for negative prices twelve days earlier (CME Clearing Advisory 20-152, 8 April 2020). The rolled position was already in June and was not exposed. A position still in May would have lost 55.90 dollars a barrel in one day, 306% of the previous price.

### 3.2 When to roll

| Rule | How it works | Strengths | Weaknesses |
|---|---|---|---|
| Volume crossover | Roll on the first day the next contract trades more than the current one | Follows where trading actually is | Volume swings from day to day and can cross back and forth |
| Open-interest crossover | Roll on the first day the next contract has more open positions | Steadier: it counts positions held, not one day's trading | Lags volume in some markets |
| Fixed calendar | Roll a fixed number of trading days before the last trading day, set per market | Known in advance; the same in a backtest and in practice; no look-ahead | Must be set once from the history of crossovers, and checked from time to time |
| Before first notice | For contracts delivered physically, roll before the first day a holder can be asked to take delivery | Avoids delivery | Applies only to physically delivered contracts; the dates come from the exchange |

On our data, the two crossovers come at these points, in trading days before each contract's last trading day (median, 2000–2022):

| Markets | Volume crossover | Open-interest crossover |
|---|---|---|
| E-mini S&P 500, Nasdaq-100 | 5 | 2–3 |
| Euro, yen, dollar index | 2 | 2 |
| Crude oil | 2 | 7 |
| Natural gas | 2 | 10 |
| Gold | 20 | 23 |
| Corn, soybeans, wheat | 15–18 | 22–23 |
| Cocoa | 24 | 27 |

Gold and the agricultural markets roll three to five weeks before the last trading day, because they are delivered physically and positions leave before the first notice day. The financial contracts are settled in cash and roll in the final days.

**Does the rule matter?** It changes the annual return of holding and rolling by less than 0.2 percentage points in equity indices, currencies and gold, by 1 to 2 points in crude oil and the grains, and by 4.6 points in natural gas, where the gap between neighbouring contracts is largest. This matches the literature: Ma, Mercer and Walker (1992) showed that the choice of roll date can change research results, and Carchano and Pardo (2009) found that for stock index futures the choice makes little difference.

**The capstone uses a fixed calendar per market**, set at the median open-interest crossover: 2 to 3 trading days before the last trading day for equity indices and currencies, 7 for crude oil, 10 for natural gas, and 22 to 27 for gold, grains and cocoa.

### 3.3 The adjustment techniques

**The right adjustment depends on how the position is held.** Each adjusted series is the exact record of one way of holding a futures position through its rolls:

| The position | Its exact record | Why |
|---|---|---|
| A fixed number of contracts | **Additive series** | The profit of one contract is the sum of the point changes of the contracts held. The additive series keeps every point change, so its change times the contract's multiplier is the profit in dollars |
| A fixed amount of money, with the number of contracts reset at each roll | **Ratio series** | The return of such a position is the return of each contract held, compounded across rolls. The ratio series keeps every percentage change |

The six techniques in use, each shown on the April 2020 roll:

| Technique | How it works | Keeps exactly | Distorts | Use for |
|---|---|---|---|---|
| **No adjustment** (raw series) | Chain the price of the contract held each day | The prices that actually traded | Every roll appears as a move: +6.50 dollars on 13 April 2020 | Contract values, position sizes and costs; never for signals or for profit across a roll |
| **Additive** (difference, or "Panama", adjustment) | At each roll, add the gap (new minus old on the roll day) to all earlier prices: every price before 13 April 2020 rises by 6.85 dollars. The latest contract stays unchanged | Point changes, hence profit in dollars per contract; distances such as channel widths and the average true range | Levels far in the past, which drift by the sum of all later gaps and can fall below zero; percentage returns | Signals in price points; profit in dollars |
| **Ratio** (proportional adjustment) | At each roll, multiply all earlier prices by new over old: every price before 13 April 2020 is multiplied by 29.26 / 22.41 = 1.306 | Percentage changes, hence compounded returns and the logarithm of the price | Point changes and distances in the past; fails when a price is zero or negative | Signals on returns or log prices; volatility in percent |
| **Returns index** | Compound the daily returns of the contract held, starting from 100 | The same as the ratio series, anchored at the start instead of today | As for ratio | Research and portfolio returns; the usual construction in academic studies of trend following, for example Moskowitz, Ooi and Pedersen (2012) |
| **Rolling over several days** | Move the position in equal parts over several days instead of at once. The S&P GSCI commodity index moves 20% a day from the fifth to the ninth business day of the month | Less dependence on one day's prices; smaller trades in the market | Still needs one of the methods above to build a series | Large positions and indices |
| **Constant maturity** | Blend the two nearest contracts with weights that keep a fixed time to expiry, for example 60 days | A smooth series, comparable over time | Not one tradable contract: holding it needs two contracts in weights that change every day | Research on the term structure and on carry |

Adjusting backwards, so that the latest prices are the real ones, is the convention: the most recent part of the series, which a live system uses, then shows real prices. Every new roll changes all earlier values of the series again, which is harmless as long as signals use only changes or ratios that the adjustment preserves.

### 3.4 Match the series to the algorithm, and the profit to the position

**Signals.** A signal must be computed on the series whose changes have the same units as the signal.

| What the signal uses | Series | Example in this lecture |
|---|---|---|
| Differences of prices in points, divided by volatility in points | Additive | EWMAC: the difference of two moving averages divided by the volatility of daily point changes (§5) |
| Price levels against recent highs and lows, distances in points | Additive | Breakout: price against its 50-day high and low; stops in multiples of the average true range (§6) |
| Returns, or the logarithm of the price | Ratio | Kalman filter on the log price (§7) |

When the units match, the choice between the two adjusted series hardly matters; when they do not, it does. On our twelve markets, 2000–2022:

| Comparison | Equity indices, currencies, gold | Crude oil, natural gas, grains |
|---|---|---|
| EWMAC forecast, additive against ratio series (correlation) | 1.000 | 0.998–1.000 |
| Breakout position, additive against ratio series (share of days the same) | 99–100% | 98–100% |
| EWMAC forecast, additive against **raw** series (correlation) | 0.99–1.00 | 0.93–0.97 |
| Breakout position, additive against **raw** series (share of days the same) | 96–98% | 85–92% |
| EWMAC forecast with **mixed units**, a difference in points divided by a volatility in percent of the adjusted price (correlation with the correct forecast) | 0.96–1.00 | 0.81–0.89 |

The raw series and the mixed units do the damage, and they do it where roll gaps are large.

**Profit.** The profit must be computed the way the position is held:

| Step | Calculation | Series |
|---|---|---|
| 1. Dollar risk of one contract | Volatility of daily point changes × multiplier | Additive (point changes) |
| 2. Position in contracts | Risk budget in dollars ÷ dollar risk of one contract | — |
| 3. Daily profit in dollars | Contracts held × point change of the contract held × multiplier | Additive, or the raw contract held, which have the same point changes |
| 4. Portfolio return | Total profit in dollars ÷ capital | — |

Two shortcuts are wrong: a percentage return computed from the additive series divides by a price that never traded, and a profit in dollars read from the ratio series uses point changes that the ratio adjustment has rescaled. Booking profit in dollars needs no division by a price, so it works even when a price is negative.

| Market | Multiplier: dollars per point | Tick: size and value |
|---|---|---|
| E-mini S&P 500 | 50 | 0.25 = 12.50 |
| E-mini Nasdaq-100 | 20 | 0.25 = 5.00 |
| Euro FX (125,000 euros) | 125,000 | 0.00005 = 6.25 |
| Japanese yen (12.5 million yen; price per 100 yen) | 125,000 | 0.00005 = 6.25 |
| US dollar index | 1,000 | 0.005 = 5.00 |
| WTI crude oil (1,000 barrels) | 1,000 | 0.01 = 10.00 |
| Natural gas (10,000 MMBtu) | 10,000 | 0.001 = 10.00 |
| Gold (100 troy ounces) | 100 | 0.10 = 10.00 |
| Corn, soybeans, wheat (5,000 bushels; price in cents) | 50 | 0.25 = 12.50 |
| Cocoa (10 tonnes) | 10 | 1 = 10.00 |

Contract sizes and ticks follow the exchanges' specifications; check them against the current ones before trading.

### 3.5 Where each adjustment breaks, and what to do

| Problem | Where it shows in our data | What to do |
|---|---|---|
| **The ratio series needs positive prices** | A series that held the May 2020 crude contract to its last day records a return of −306% on 20 April and has a negative price as the base of the next day's return: the return is undefined | Roll before expiry (the calendar of §3.2 left May on 13 April). Book profit in dollars, which needs no division, and measure returns on capital: a future requires no investment, so its return is profit divided by the capital set aside for it, not by its price. A model that needs log prices, such as the Kalman filter of §7, runs on prices in levels in a market that can go below zero |
| **The additive series drifts and can fall below zero** | Soybeans: the additive series is below zero on 61% of the days from 2000 to 2008, for the last time in December 2008, and as low as −408 cents. Crude oil: −1.10 dollars on 21 April 2020 ([chart J.2](#j2-the-same-contracts-three-series-35)) | Never compute percentage returns or log prices from it; measure volatility from point changes; take percentages from the raw contract held |
| **Level-based rules see levels that never traded** | Both adjusted series: in July 2008 crude oil's ratio series reaches 828 dollars and its additive series 211, against a highest traded price of 146 | Use levels only relative to recent levels of the same series (channels, moving averages), never as absolute prices, for example "buy below 50 dollars" |

**Where the ratio adjustment is unsafe**: markets whose prices can come near zero or go below it, such as crude oil under storage stress, natural gas and power at regional delivery points, calendar spreads, and any series quoted as a difference. **Where the additive adjustment is unsafe for percentages**: long histories in markets with large roll gaps of one sign, such as natural gas, the grains, crude oil and soybeans. For the systems of this lecture the solution is the same in both cases: signals in matching units, profit in dollars.

### 3.6 Roll yield: what rolling earns or costs

When later contracts are more expensive than the one held (**contango**), each roll sells low and buys high, and a holder loses relative to the price; when they are cheaper (**backwardation**), the holder gains. The difference between the change of the price and the return of holding and rolling is the roll yield ([chart J.3](#j3-roll-yield-36)):

| Market | Change of the front-month price, % a year | Return of holding and rolling, % a year | Roll yield, % a year |
|---|---|---|---|
| Natural gas | +5.0 | −22.8 | −27.8 |
| Wheat | +4.8 | −7.8 | −12.6 |
| Corn | +5.2 | −3.8 | −8.9 |
| WTI crude oil | +5.1 | −1.8 | −6.9 |
| Cocoa | +4.9 | +1.1 | −3.7 |
| Gold | +8.4 | +6.0 | −2.4 |
| Japanese yen | −1.3 | −3.1 | −1.8 |
| E-mini Nasdaq-100 | +4.8 | +3.4 | −1.4 |
| Euro FX | +0.1 | −0.5 | −0.7 |
| US dollar index | +0.2 | −0.2 | −0.4 |
| E-mini S&P 500 | +4.3 | +4.3 | −0.1 |
| Soybeans | +5.1 | +7.2 | +2.1 |

The price of natural gas rose 5% a year from 2000 to 2022; a holder lost 23% a year, because the market was in steep contango almost throughout. In financial futures the roll yield is small and reflects the gap between interest rates and the income of the asset: dividends for equity indices, the interest rate of the other currency for currencies. The literature on commodity futures separates the two sources in the same way (Gorton and Rouwenhorst, 2006; Erb and Harvey, 2006).

For a trend follower this matters in two ways. The adjusted series include the roll, so a trend rule sees the holder's return: a market in steady contango shows a downtrend even when its price is flat, and a long-short rule tends to be short it. And the shape of the curve carries information of its own. Traded on its own, the roll yield is a carry strategy, which is not part of this lecture. Used as a condition on a trend signal, it is a filter: take long trends only in backwardation and short trends only in contango, or only when the roll yield is above or below its own average. Studies of commodity futures combine trend and term-structure signals in this way (Fuertes, Miffre and Rallis, 2010); §10 tests one such filter on our markets.

### 3.7 The bond funds: price, total and excess returns

| Series | What it measures | VFITX, % a year, 2000–2022 | VUSTX, % a year, 2000–2022 |
|---|---|---|---|
| Price (Yahoo's Close) | The fund's price, which falls each time it pays out interest | −0.1 | −0.4 |
| Total return (Yahoo's Adj Close) | Price with the payouts reinvested | +4.1 | +5.1 |
| **Excess return** | Total return minus the three-month Treasury bill rate (1.5% a year on average) | **+2.5** | **+3.5** |

The price alone misses almost the whole return of a bond fund, which comes from the interest paid out. The total return includes it, but also includes the cash rate that a futures position does not earn, because a future ties up only margin. The excess return removes the cash rate and puts the funds on the same footing as the futures: daily excess return = daily total return − bill rate of the previous day ÷ 252. Volatility is 4.8% a year for VFITX and 12.2% for VUSTX. The funds pay out monthly and have no roll, so the excess-return series is the only series they need.

### 3.8 What to store

| Stored | Used for |
|---|---|
| The raw contracts, as downloaded, never changed, with problem rows flagged | The source of everything; the prices actually traded; position sizes and costs |
| The roll calendar: date, old and new contract, both prices and the gap | Builds both adjusted series; every roll can be checked; the roll yield |
| The additive series | Signals in points; profit in dollars |
| The ratio series | Signals on returns or log prices; volatility in percent; compounded returns |
| For the bond funds: total and excess returns | Signals and profit |

Both adjusted series are rebuilt from the raw contracts and the roll calendar in seconds. A different roll rule needs no new data, and every number can be traced back to a roll that was observed.

## 4. What the data contain

A backtest can only show how a system behaves in the conditions its history contains. Before building systems, it helps to know which conditions those are. Each episode below is defined by a simple rule that anyone can check, using US data from FRED and Yahoo Finance; spells less than three months apart (monthly data) or one month apart (daily data) count as one episode ([chart J.4](#j4-what-the-data-contain-4)).

| Episode | Rule | Number | When | Share of days |
|---|---|---|---|---|
| Recession | NBER dates (FRED series USREC) | 3 | 2001; 2008–2009; 2020 | 9% |
| Equity bear market | S&P 500 down 20% from its previous peak, counted from the peak to the trough | 4 | Mar 2000–Oct 2002; Oct 2007–Mar 2009; Feb–Mar 2020; Jan–Oct 2022 | 21% |
| High volatility | VIX above 30 for at least five days | 17 | Mostly 2001–2003, 2008–2009, 2011, 2020 and 2022 | 10.5% |
| Inflation above 4% | Consumer prices up more than 4% on a year earlier | 4 | 2005–2006 (twice, briefly); 2007–2008; 2021–2022, peaking at 9.0% in June 2022 | 13% |
| Deflation | Consumer prices lower than a year earlier | 2 | Dec 2008–Oct 2009, as low as −2.0%; Jan–Apr 2015 | 5% |
| Zero rates | Federal funds rate below 0.25% | 2 | Oct 2008–Jan 2016; Mar 2020–Mar 2022 | 40% |
| QE: the Fed buying bonds | Announced programmes | 4 | Nov 2008–Mar 2010; Nov 2010–Jun 2011; Sep 2012–Oct 2014; Mar 2020–Mar 2022 | 27% |
| QT: the Fed shrinking its balance sheet | Announced programmes | 2 | Oct 2017–Jul 2019; from Jun 2022 | 11% |
| The Fed raising rates | From the first to the last increase of a cycle | 3 | Jun 2004–Jun 2006; Dec 2015–Dec 2018; from Mar 2022 | 25% |

What this means for the backtests:

- **Stress is well represented.** Three recessions and four bear markets: on one day in five the S&P 500 was in a bear market. Crisis behaviour can be measured on several episodes, not on 2008 alone. Calm is common too: the VIX was below 15 on 32% of days.
- **Inflation is not.** There is one sustained inflation shock, 2021–2022, and it comes at the very end of the data. No decade resembles the 1970s, and results on inflation hedging rest on a single episode.
- **Monetary policy dominates the middle of the sample.** Rates were at zero on 40% of days and the Fed was buying bonds on 27%. Over the whole period the 10-year Treasury yield fell from 6.6% in January 2000 to 0.5% in August 2020, before rising to 3.9% by the end of 2022. A long bull market in bonds, followed by their worst year in decades, shapes every bond result in this lecture.
- **The rules are US rules.** Other markets had their own episodes, for example negative policy rates in the euro area from 2014 and in Japan from 2016, which the table does not show.

§9 uses these episodes to evaluate the systems in crises and across policy regimes, and some of them return as filters in §10.

## 5. EWMAC

### 5.1 How it works on futures

The rule is card 4 of Lecture 6: the difference between a fast and a slow exponential moving average, divided by volatility. On futures three things change, all following §3.4:

| Step | On futures | Why |
|---|---|---|
| Price series | The additive back-adjusted series | The signal is a difference of prices in points |
| Volatility | Exponentially weighted volatility of daily point changes, span 36 days, floored at half its median over the past ten years | Same units as the signal; the floor stops positions from growing without limit in calm markets |
| Forecast | Divided by its average absolute size to date and capped at ±2 | No single reading dominates (Lecture 9) |
| Position | Forecast × risk budget ÷ (volatility in points × multiplier), in contracts | Equal risk per market |
| Speeds | Seven, from 16/64 to 128/512, blended with equal weights | The plateau of §8 |
| Profit | Contracts × point change × multiplier, in dollars | Exact for a fixed number of contracts (§3.3) |

### 5.2 What each design step adds

Each step of Part II added one at a time, 2001–2022, after costs of 5 basis points per unit of notional traded:

| Step | Sharpe ratio | 2001–2008 | 2009–2022 | Full design without this step |
|---|---|---|---|---|
| 1. One speed (16/64), the same money in each market, 12 futures, equal weights | 0.03 | 0.18 | −0.08 | |
| 2. + volatility sizing, with floor (Lecture 9) | 0.17 | 0.22 | 0.14 | 0.44 |
| 3. + seven speeds blended (Lectures 6 and 7) | 0.31 | 0.46 | 0.23 | 0.29 |
| 4. + the two bond funds (§2.4) | 0.34 | 0.48 | 0.27 | 0.50 |
| 5. + equal risk per asset class (§11) | 0.43 | 0.49 | 0.40 | 0.43 |
| 6. + portfolio volatility target of 10%, leverage capped at 3 (Lecture 9, §5) | **0.54** | 0.53 | 0.55 | |

- **The order of the steps changes what each seems to add.** Added first, volatility sizing raises the Sharpe ratio fivefold; removed last from the full design, it costs 0.10, because equal risk per class and the portfolio volatility target already do part of its work. The last column is the fair measure of each step.
- **Blending speeds is the largest single contribution** in the full design: without it the Sharpe ratio falls from 0.54 to 0.29.
- **Every step is chosen in advance**, so the ladder involves no selection.

### 5.3 The volatility floor, checked

| | Plain volatility | Floor: half the 10-year median | Blend: 70% short-term, 30% 10-year mean |
|---|---|---|---|
| Sharpe ratio, one speed, before portfolio scaling | 0.34 | 0.34 | 0.33 |
| Worst day, in units of daily risk | −5.8 | −5.9 | −6.2 |
| Days beyond four units | 26 | 26 | 34 |
| Highest three-month volatility, relative to the average | 2.20 | 2.21 | 2.62 |
| Largest position relative to its median, median across markets | 3.2× | 2.8× | 2.3× |

The floor binds on 0.1% to 5% of days in most markets, 13% in natural gas and 17% in the Nasdaq. On this sample it costs nothing and changes little: insurance against a market that is calm until it jumps, which these 22 years rarely contain. The blend keeps positions smaller in calm times but reacts more slowly when volatility rises, so risk overshoots in the spikes. The floor is the rule; the blend is the comparison.

In gold, position size varies by up to seven times its median under every variant. This is correct: the price rose from about 280 to 1,800 dollars an ounce, so its volatility in points rose with it, and a constant risk needs fewer contracts.

### 5.4 The Kalman slope: a variant of EWMAC

The level-plus-slope Kalman filter of Lecture 4, run on the log of the ratio series, is in steady state a linear filter of past prices, like EWMAC (Lecture 4, §3). On our data it behaves like one:

| | Result |
|---|---|
| Correlation of its forecast with the best-matching EWMAC | 0.90–0.93 |
| Correlation of daily returns at equal speed | 0.93–0.95, in every market between 0.90 and 0.96 |
| Linking the filter's noise to current volatility | Brings it closer to EWMAC, not further: EWMAC divides by volatility too |
| Best Sharpe ratio across speeds, full design | 0.28, against 0.56 for EWMAC at a similar holding period ([chart J.5](#j5-three-systems-across-their-speeds-8)) |

What the Kalman filter adds is not a different return stream but two readings EWMAC does not have: the uncertainty around the slope, and the surprises, the gaps between forecast and price, which flag when the model no longer fits. Both are tools for monitoring a system rather than reasons to trade a second one.

**Margin.** Exchange margins are a few percent of the notional value for financial futures and more for commodities. At a 10% volatility target they tie up a small part of the capital and never constrain the positions. The rest of the capital earns the Treasury bill rate, which the excess returns of this lecture leave out.

## 6. Breakout

### 6.1 How it works on futures

The rule is card 5 of Lecture 6, the Turtle breakout: go long when the price closes above its highest close of the past N days, short below the lowest; exit a long when the price closes below the lowest close of the past N/2 days, and a short above the highest. Between an exit and the next breakout the position is flat. Signals use the additive series, since channels are levels compared with recent levels of the same series (§3.5). The position is sized by volatility as in §5.1, and four entry channels, 120, 160, 250 and 375 days, are blended with equal weights.

### 6.2 What is different

| | Single breakout, 120-day entry | Blend of four channels |
|---|---|---|
| Average holding period | 43 days | |
| Position changes per market per year | 1.7 | |
| Share of days with a position | | 92% |
| Sharpe ratio, full design, after 5 bp | 0.40 | 0.59 |

Each breakout is an on-or-off rule; blended over four channels, the system is rarely flat in every one at once. Its daily returns correlate 0.90 with EWMAC at medium speed, as in Lecture 6, and 0.94 as blends of their plateau speeds: the breakout reaches a similar return by different mechanics, entering at a level instead of gradually, and leaving a market alone between trends. §8 asks whether that difference adds anything.

## 7. Cross-sectional momentum

### 7.1 How it works on futures

The rule is card 11 of Lecture 6 (§2.4): rank the markets by their return over a lookback divided by its volatility, go long the top third and short the bottom third at equal risk. On these markets:

| Choice | Here | Why |
|---|---|---|
| Universe | All 14 markets ranked together, across asset classes | With one to four markets per class, a ranking within classes is too thin; Asness, Moskowitz and Pedersen (2013) rank within classes on much larger universes |
| Lookback | Five, from 126 to 504 days, blended | The plateau of §8 |
| Positions | About five markets long and five short each day; positions smoothed over an eighth of the lookback | Limits the trading caused by markets moving between thirds |
| Net exposure | Close to zero by construction | The defining difference from the other two (Goyal and Jegadeesh, 2018) |

### 7.2 What is different

At medium speed, cross-sectional momentum correlates 0.69 with EWMAC and 0.64 with the breakout, far less than the 0.90 between those two. As blends of their plateau speeds the gap narrows, to 0.87 and 0.86 against 0.94: slow relative trends and slow absolute trends often point the same way. In 2022 it gained about as much as EWMAC, 16.4% against 17.5%, but in a different way: long energy and short bonds at the same time, rather than short everything that fell.

## 8. Comparing the systems

### 8.1 Across speeds

Every system was run across a wide grid of speeds with the full design of §5.1 and costs of 5 bp ([chart J.5](#j5-three-systems-across-their-speeds-8), [chart J.6](#j6-parameter-surfaces-8)), and compared on one axis, the average holding period (Lecture 7, §2):

| System | Grid | Cliff: loses money after costs | Plateau | Sharpe ratio on the plateau |
|---|---|---|---|---|
| EWMAC | Fast span 2 to 128 days, slow span 2, 4 or 8 times the fast | Fast span below about 8 days, holding period under 15 days | Fast span 24 to 128 days, holding 30 to 42 days | 0.41–0.56, nearly the same for all three ratios |
| Breakout | Entry 10 to 500 days, exit a quarter, half or all of the entry | Entry below about 40 days | Entry 120 to 375 days, holding 35 to 61 days | 0.39–0.61, the exit matters little |
| Cross-sectional | Lookback 10 to 504 days | Lookback below about 40 days | Lookback 126 to 504 days, holding 34 to 63 days | 0.51–0.70 |
| Kalman (variant) | Eleven speeds | Holding period under 15 days | Slowest speeds | At most 0.28 |

At the fast end every system fails, and not only because of costs: even before costs the fastest variants earn almost nothing.

**How the speeds are chosen, without optimising.** Drop the region that does not work, then blend as many of the remaining speeds as possible with equal weights: seven for EWMAC, four for the breakout, five for cross-sectional momentum. Three speeds spread across the plateau give the same result (EWMAC 0.53 against 0.54, breakout 0.62 against 0.59, cross-sectional 0.72 against 0.73); the peak itself is never chosen. §12 tests this rule on markets it was not made on.

### 8.2 Does a system add anything?

Spanning regressions of monthly returns at the plateau blends (Lecture 7, §3):

| Test | Alpha, % a year | t-statistic | R² |
|---|---|---|---|
| Breakout on EWMAC and cross-sectional | +0.4 | 0.5 | 0.89 |
| Cross-sectional on EWMAC | **+2.7** | **3.1** | 0.79 |
| EWMAC on cross-sectional | −1.2 | −1.3 | 0.79 |
| EWMAC on the long portfolio of §9 | +4.4 | 2.3 | 0.07 |
| Cross-sectional on the long portfolio | +6.3 | 3.2 | 0.09 |

- **The breakout adds nothing** to the other two: they explain 89% of its monthly returns, with no alpha. It stays in the lecture for its mechanics and its comparison, not in the portfolio.
- **Cross-sectional momentum adds to EWMAC; on this sample, EWMAC adds nothing beyond it.**
- **Both add to a portfolio that is long the same markets.**

**The portfolio combines EWMAC and cross-sectional momentum at equal risk**, decided in advance. Dropping EWMAC because it is spanned here would be choosing the best point, which Lecture 7 warns against: the gap between the two is within the noise of §9, and cross-sectional momentum's edge rests on ranking only 14 markets in one sample.

## 9. Evaluating the results

### 9.1 The systems and the portfolio

All at 10% volatility, 2001–2022 ([chart J.10](#j10-the-final-portfolio-11)):

| | Sharpe ratio | Return, % a year | Maximum drawdown | Worst year | 2022 |
|---|---|---|---|---|---|
| EWMAC | 0.54 | 5.6 | −16.8% | −10.8% | +17.5% |
| Breakout | 0.59 | 6.1 | −21.3% | −11.5% | +13.0% |
| Cross-sectional | 0.73 | 7.5 | −17.5% | −9.1% | +16.4% |
| **EWMAC + cross-sectional, 5 bp** | **0.66** | **6.8** | **−16.6%** | **−10.5%** | **+18.5%** |
| The same, 10 bp | 0.54 | 5.6 | −18.4% | −11.8% | +17.6% |
| The same, no costs | 0.78 | 8.0 | −15.8% | −9.2% | +19.5% |
| Long the 14 markets, same sizing and weights | 0.50 | 5.1 | −36.7% | −17.1% | −7.2% |

The breakeven cost of the portfolio, at which its Sharpe ratio falls to zero, is 33 basis points per unit traded: more than six times the 5 bp assumed.

**How much these numbers can be trusted.** Over 22.8 years, a Sharpe ratio of 0.5 to 0.7 has a standard error of about 0.22 (Lo, 2002). Differences between the systems of 0.1 or 0.2 lie within that noise; the conclusions below rest on differences in payoff and in what each system adds, which are larger and steadier than differences in Sharpe ratio.

### 9.2 Long-short or long-or-flat

The same plateau blends, with shorts allowed or replaced by flat positions:

| | EWMAC long-short | EWMAC long-or-flat | Breakout long-short | Breakout long-or-flat |
|---|---|---|---|---|
| Sharpe ratio | 0.54 | 0.60 | 0.59 | 0.61 |
| Time in the market | 97% | 52% | 92% | 50% |
| Correlation with the S&P 500, monthly | −0.09 | 0.16 | −0.07 | 0.27 |
| Correlation with holding the same markets long, monthly | 0.27 | 0.60 | 0.23 | 0.59 |
| Average quarter, worst fifth of S&P 500 quarters | +4.7% | +1.8% | +4.4% | +1.2% |
| Average quarter, best fifth | +2.3% | +3.6% | +2.6% | +4.6% |
| Jan 2001–Oct 2002 | +18.2% | +0.6% | +19.0% | +8.7% |
| Oct 2007–Mar 2009 | +22.7% | +17.9% | +26.7% | +15.6% |
| Feb–Mar 2020 | +2.3% | −1.5% | −0.7% | −6.4% |
| Jan–Oct 2022 | +23.1% | +4.8% | +18.6% | −3.8% |

**Similar performance, a different product** ([chart J.7](#j7-the-smile-9)). The long-or-flat versions earn as much or slightly more, but they are out of the market half the time and, when in it, mostly long what a portfolio already holds: their correlation with the long portfolio doubles. Long-short makes money at both ends of the equity distribution, most in the worst quarters; long-or-flat keeps the right end and loses most of the left, and it gave up almost all of its gains in 2001–2002 and 2022. This is the smile of Lectures 5 and 6, on futures: the short side carries the crisis protection. As a diversifier of a portfolio that is already long, long-short is the better design.

### 9.3 Against the long benchmark

Holding the same markets long, with the same sizing and weights, is the natural benchmark: it earns the drift that the trend systems partly collect, without any timing.

| | Long the 14 markets | EWMAC | Breakout | Cross-sectional | Portfolio |
|---|---|---|---|---|---|
| Sharpe ratio | 0.50 | 0.54 | 0.59 | 0.73 | 0.66 |
| Maximum drawdown | −36.7% | −16.8% | −21.3% | −17.5% | −16.6% |
| Longest time under water | 10.9 years | 3.2 years | 5.0 years | 3.2 years | 3.2 years |
| Jan 2001–Oct 2002 | +25.6% | +18.2% | +19.0% | +31.6% | +28.4% |
| Oct 2007–Mar 2009 | +15.1% | +22.7% | +26.7% | +12.6% | +18.3% |
| Feb–Mar 2020 | −2.2% | +2.3% | −0.7% | +0.3% | +1.8% |
| Jan–Oct 2022 | −8.1% | +23.1% | +18.6% | +22.7% | +24.6% |

| Correlation with the long portfolio | EWMAC | Portfolio |
|---|---|---|
| When the long portfolio is less than 10% below its peak (58% of days) | +0.42 | +0.42 |
| When it is more than 10% below its peak (42% of days) | **−0.11** | **−0.06** |
| Correlation of the drawdown paths | 0.31 | 0.24 |

- **The long benchmark is not an equity portfolio.** With one sixth of the risk in each class, it holds bonds, gold and commodities as much as equities, which is why it gained in 2001–2002, when bonds, gold and the euro rose while equities fell. Its weakness is elsewhere: from 2008 it went almost eleven years without a new peak, through the fall of commodities, and in 2022 bonds fell with everything else.
- **Trend gained in the slow bear markets and was roughly flat in the fast one.** The COVID crash took five weeks, too fast for trends at these speeds to turn.
- **The correlation changes sign when it matters**, and the drawdowns rarely coincide.
- **Combined, they improve each other.** Half long portfolio and half trend portfolio, rescaled to 10% volatility, has a Sharpe ratio of 0.74 against 0.50 for the long portfolio alone, and a maximum drawdown of −17.5% against −36.7%. The trend portfolio's alpha against the long portfolio is 5.6% a year, with a t-statistic of 2.8.

### 9.4 Do the systems lose at the same time?

Between the systems the overlap is larger than their return correlations suggest: as blends of their plateau speeds, EWMAC and cross-sectional momentum correlate 0.87 in daily returns and 0.77 in drawdown paths; EWMAC and the breakout 0.94 and 0.83. At the speeds that work, the three systems are closer than their medium-speed versions suggest; they diversify a long portfolio far more than they diversify each other.

## 10. Two filters

Two filters from different sources of information, each tested with the tools of Lecture 8: a curve across thresholds, a comparison with 200 random filters that are on as often and for spells as long, and a market split.

### 10.1 Term structure (each market)

Allow a long EWMAC position only when the market is in backwardation by more than a threshold, a short only in contango by more than it (§3.6; Fuertes, Miffre and Rallis, 2010). The roll yield is measured from the two nearest contracts and known the day before.

| Threshold | Sharpe ratio, EWMAC | Sharpe ratio, portfolio | Share of positions removed |
|---|---|---|---|
| No filter | 0.54 | 0.66 | 0% |
| −5% (loose) | 0.48 | 0.62 | 7% |
| 0% | 0.53 | 0.66 | 31% |
| +5% (strict) | 0.20 | 0.53 | 62% |

The filter does not raise EWMAC's Sharpe ratio at any threshold ([chart J.9](#j9-filter-curves-10)). At 0% it removes almost a third of the positions at hardly any cost, and it beats 87% of random filters that remove positions as often and for as long: the positions it removes are worse than average. But removing them earns nothing either. In these markets the term structure is too one-sided to filter on (gold and the yen were almost never in backwardation, wheat on 7% of days, corn on 13%), and a trend rule already sees the roll, because the adjusted series contain it.

### 10.2 Correlation regime (the whole portfolio)

Halve the portfolio's risk when the average correlation between the 14 markets over the past 63 days is above a percentile of its own history to date.

| Threshold | Sharpe ratio | Maximum drawdown | Return, % a year | Share of days with half risk |
|---|---|---|---|---|
| No filter | 0.66 | −17.2% | 6.8 | 0% |
| 50th percentile | 0.75 | −12.6% | 6.0 | 55% |
| 70th percentile | 0.70 | −16.3% | 6.3 | 36% |
| 90th percentile | 0.71 | −16.7% | 7.1 | 12% |

- **When correlation is high the portfolio earns little**: a Sharpe ratio of 0.30 when it is above its median, 1.09 when below. Diversification is what a trend portfolio sells, and when everything moves together there is less of it.
- **The filter beats 97% of random filters** with the same share of days and length of spells.
- **On markets it was not chosen on, it mostly holds.** Chosen on one half of the markets, the threshold is the median both times; applied to the other half it raises the Sharpe ratio from 0.51 to 0.63 and from 0.61 to 0.67, while the drawdown improves in one half (−30.1% to −22.0%) and worsens in the other (−19.2% to −24.1%).
- **It costs return**: 6.0% a year instead of 6.8%, since the portfolio runs at half risk more than half the time.

Lecture 8 found a similar regime on ETFs that weakened out of sample in time. Here it holds across markets, but its evidence still comes from one period. The portfolio of §9 is reported without it; the filter is an option whose case rests on this table.

## 11. Building the portfolio

### 11.1 A map of methods

| Family | Idea | Strengths | Weaknesses |
|---|---|---|---|
| **Equal risk** (inverse volatility; equal risk per asset class, then per market) | Every class and every market gets the same risk budget | Needs only volatilities, so it is robust | Ignores correlation: near copies get double weight |
| Equal risk contribution, hierarchical risk parity | Each market or cluster contributes equally to the portfolio's risk | Handles clusters, such as equity indices that move together | Correlations are estimated, and change in crises (Lecture 3, §8) |
| Mean-variance | Maximise expected return per unit of risk | The theoretical optimum | Extremely sensitive to expected returns, which can hardly be estimated |
| Optimisation with constraints, for example simulated annealing over weights with limits on concentration and turnover | Searches for the best weights under practical limits | Flexible | Many choices, and the same sensitivity to estimated inputs; beyond this lecture |

### 11.2 Within each system: across markets

| Scheme | Weights | Effect |
|---|---|---|
| **A. Equal risk per asset class, then per market** (used) | Each of the six classes one sixth of the risk | EWMAC 0.54 |
| B. Equal risk per market | Agriculture 29% of the risk because it has four markets, metals 7% | EWMAC 0.43 |
| C. Traded dollar volume | Equities 69%, agriculture 4%, bond funds none | Not diversified: volume measures capacity, not risk; used only as a limit on position size |
| Equal risk contribution | From the covariance of the markets' returns over the past two years, monthly | EWMAC 0.47, maximum drawdown −30% |

**Equal risk contribution** solves: minimise $`\tfrac{1}{2}\,w^\top \Sigma\, w - \tfrac{1}{n}\sum_i \ln w_i`$, then rescale the weights to sum to one, with $`w_i`$ the weight of market $`i`$, $`\Sigma`$ the covariance matrix of the markets' returns and $`n`$ the number of markets (Maillard, Roncalli and Teïletche, 2010). The logarithm keeps every weight positive, and at the solution every market contributes the same share of risk, $`w_i (\Sigma w)_i`$. The problem is convex, so a solution exists and is unique whatever the correlations, and a simple solver that updates one weight at a time finds it (Griveau-Billion, Richard and Roncalli, 2013). *Watch out for* rules that rescale each weight by its risk contribution: a market that is negatively correlated with the rest has a negative contribution, and such rules break down.

It does worse here for a visible reason: it gives the largest weights to natural gas (16%) and cocoa (11%), whose trend returns are the least correlated with the rest; cocoa is also the worst market of the sample. Weighting by correlation chases diversification into whatever is uncorrelated, including markets that are uncorrelated because they do not work, and the correlations are estimated with noise. Equal risk needs no correlations. This matches the finding that simple weights are hard to beat out of sample (DeMiguel, Garlappi and Uppal, 2009).

### 11.3 Across systems

EWMAC and cross-sectional momentum at equal risk (§8.2), the sum scaled to 10% volatility with leverage capped at 3. The equal-risk-contribution version of the same combination has a Sharpe ratio of 0.55 against 0.66.

## 12. Out of sample

Three checks, chosen to guard against three different risks (Lecture 7, §5 and §6).

### 12.1 Choices fixed in advance

The main results involve no selection from results: all speeds on the plateau blended with equal weights, equal risk per class and market, the volatility floor, a 10% volatility target, the two systems at equal risk, costs of 5 bp. Choices fixed in advance cannot be overfitted.

### 12.2 Split by market

The only data-driven choice, which speeds to drop, is made on one half of the markets and tested on the other, over the same period, so the regime is held fixed. Each half contains markets from every class that has more than one. Rule: keep every variant whose Sharpe ratio on the choosing half is at least half that of the best variant there; blend the kept variants.

| System | Chosen on | Kept | Test half: blend of kept | Blend of all | Blend of dropped | Best variant of the choosing half |
|---|---|---|---|---|---|---|
| EWMAC | Half A | 19 of 39 | 0.42 | 0.11 | −0.20 | 0.45 |
| EWMAC | Half B | 21 of 39 | 0.52 | 0.21 | −0.28 | 0.39 |
| Breakout | Half A | 13 of 33 | 0.47 | 0.26 | +0.03 | 0.40 |
| Breakout | Half B | 15 of 33 | 0.49 | 0.22 | −0.04 | 0.41 |
| Cross-sectional | Half A | 5 of 9 | 0.51 | 0.36 | −0.02 | 0.47 |
| Cross-sectional | Half B | 6 of 9 | 0.64 | 0.44 | −0.08 | 0.76 |

The rule carries over. On markets it was not made on, the kept blend earns 0.42 to 0.64, the dropped variants −0.28 to 0.03, and blending everything about half as much. The kept blend matches or beats the single best variant of the choosing half in four of six cases, without having chosen one.

### 12.3 The probability of backtest overfitting

Across the whole grid of 92 variants, by combinatorially symmetric cross-validation on 16 blocks of time (Bailey et al., 2017):

| Variants | Probability of overfitting | Best in sample: median Sharpe ratio out of sample | Median variant out of sample |
|---|---|---|---|
| All 92 | 0.10 | 0.52 | 0.25 |
| EWMAC (39) | 0.15 | 0.44 | 0.29 |
| Breakout (33) | 0.16 | 0.43 | 0.25 |
| Cross-sectional (9) | 0.18 | 0.58 | 0.43 |

Picking the best of 92 variants would be overfitted one time in ten, and the best variant in sample earns a median of 0.52 out of sample: choosing among the slow variants is mostly noise, choosing the slow end is not. A rough bound gives a sense of scale: with 92 variants and a standard error of 0.22, luck alone can produce a best Sharpe ratio of about 0.67, close to the best variant found, 0.70 (Bailey and López de Prado, 2014, correct for this with the deflated Sharpe ratio). This is why the design blends a plateau instead of picking a point.

## 13. Summary, exercises and reading

### 13.1 Six takeaways

1. **Futures need a series that records what a position experienced.** Back-adjust from observed rolls; choose the adjustment by how the position is held, and compute signals and profit in matching units.
2. **The design steps of Part II add up**, from a Sharpe ratio of 0.03 for one speed with naive sizing to 0.54; blending speeds matters most.
3. **Choose speeds by dropping what fails and blending the rest.** The rule works on markets it was not made on; the plateau, not the peak, is what survives out of sample.
4. **Three systems, two in the portfolio.** The breakout adds nothing to EWMAC and cross-sectional momentum; the Kalman slope is a variant of EWMAC.
5. **Trend's value is its payoff.** It gained in the slow bear markets and in 2022, its correlation with a long portfolio turned negative in stress, and half long, half trend beat the long portfolio clearly (0.74 against 0.50). The long-or-flat version earns as much but gives up most of this.
6. **Simple weights and few filters.** Equal risk beat equal risk contribution; the term-structure filter added nothing, the correlation filter survived its checks but rests on one period.

### 13.2 Exercises

- [ ] Rebuild the ladder of §5.2 with costs of 10 bp. Which step loses most? (notebook §5)
- [ ] Rank the cross-sectional markets within three groups instead of across all 14 (financials, commodities, bonds). Does the correlation with EWMAC fall further? (notebook §7)
- [ ] Replace the additive series by the ratio series in EWMAC, with volatility in percent. Confirm that the forecasts barely change, as §3.4 claims. (notebook §3)
- [ ] Run the market split of §12.2 with a stricter rule, keeping variants within 80% of the best. Does the kept blend improve or only shrink? (notebook §12)

### 13.3 Reading

For futures data and rolling in practice, Carver's blog post on rolling (2015) and Ma, Mercer and Walker (1992). For the comparison and testing methods, Lecture 7 and its references. For portfolio construction, Maillard, Roncalli and Teïletche (2010) and DeMiguel, Garlappi and Uppal (2009).


## Appendix: charts

### J.1 One roll, three series (§3.1)

![WTI crude oil, March to April 2020: the May and June contracts, the raw series that switches on 13 April, and the additive and ratio series](figures/11_01_one_roll.png)

Left: the May and June contracts and the raw series, which jumps from May to June on the roll day (dashed line). The May contract's fall to −37.63 on 20 April happens after the roll. Right: both adjusted series move smoothly through the roll; their levels differ from the traded prices because they are adjusted back from December 2022.

### J.2 The same contracts, three series (§3.5)

![Crude oil and soybeans, 2000-2022: raw, additive and ratio series](figures/11_02_three_series.png)

All three series end at the December 2022 price. Going back, the additive series moves away from the traded price by the sum of all later roll gaps, and for soybeans falls below zero; the ratio series moves away by their product, and for crude oil reaches 828 dollars in July 2008.

### J.3 Roll yield (§3.6)

![Change of the front-month price and return of holding and rolling, per market, 2000-2022](figures/11_03_roll_yield.png)

Grey: what the price did. Blue: what a holder earned after rolling. Where blue lies left of grey, rolling cost money (contango); for soybeans it earned money (backwardation).

### J.4 What the data contain (§4)

![Timeline of recessions, bear markets, high volatility, inflation, deflation, zero rates, QE, QT and rate increases, 2000-2022](figures/11_04_episodes.png)

Each bar is one episode under the rules of §4. Stress clusters in 2000–2003, 2008–2009, 2020 and 2022; zero rates and QE fill most of 2009–2015; the only sustained inflation comes at the end.

### J.5 Three systems across their speeds (§8)

![Sharpe ratio against average holding period for EWMAC, the breakout, cross-sectional momentum and the Kalman variant](figures/11_05_speed_curves.png)

Every point is one variant with the full design, after 5 bp. Left of about 20 days (shaded) every system loses money; the plateau to the right is what the portfolio blends.

### J.6 Parameter surfaces (§8)

![Heat maps of the Sharpe ratio across EWMAC's fast span and ratio, and the breakout's entry and exit](figures/11_06_surfaces.png)

Red cells: the cliff of fast settings. Blue: the plateau. Within the plateau, neighbouring settings earn about the same, which is why choosing among them adds nothing.

### J.7 The smile (§9)

![Average quarterly return of EWMAC long-short and long-or-flat by quintile of S&P 500 quarters](figures/11_07_smile.png)

Long-short earns most in the worst quarters of the S&P 500; long-or-flat gives most of that up.

### J.8 Drawdowns (§9)

![Drawdowns of the long benchmark, the trend portfolio and a 50/50 mix](figures/11_08_drawdowns.png)

The long benchmark's long drawdown from 2008 and its fall in 2022 coincide with gains of the trend portfolio; the mix has shallower drawdowns than either.

### J.9 Filter curves (§10)

![Sharpe ratio across thresholds for the term-structure filter and the correlation filter](figures/11_09_filter_curves.png)

The first point of each curve is the system without the filter. The term-structure filter never rises above it; the correlation filter does at every threshold.

### J.10 The final portfolio (§11)

![Wealth of the final portfolio at 5 and 10 bp against the long benchmark, log scale](figures/11_10_final.png)

## References

- Asness, C., Moskowitz, T. and Pedersen, L.H. (2013). Value and momentum everywhere. *Journal of Finance* 68(3), 929–985. — cross-sectional momentum across asset classes (§7).
- Bailey, D., Borwein, J., López de Prado, M. and Zhu, Q. (2017). The probability of backtest overfitting. *Journal of Computational Finance* 20(4). — §12.3.
- Bailey, D. and López de Prado, M. (2014). The deflated Sharpe ratio: correcting for selection bias, backtest overfitting and non-normality. *Journal of Portfolio Management* 40(5), 94–107. — the luck of the best of many (§12.3).
- Carchano, Ó. and Pardo, Á. (2009). Rolling over stock index futures contracts. *Journal of Futures Markets* 29(7), 684–694. — the roll method matters little for stock index futures (§3.2).
- Carver, R. (2015). Systems building: futures rolling. *This Blog is Systematic*, 18 May 2015. — the additive ("Panama") method and its limits (§3.3).
- CME Group (2020). CME Clearing Advisory 20-152, 8 April 2020. — preparing for negative prices in crude oil (§3.1).
- Federal Reserve Bank of St. Louis. FRED economic data: series USREC (NBER recession indicator), CPIAUCSL, DFF, VIXCLS, DGS10, DTB3. — the episodes of §4 and the bill rate (§2.4, §3.7).
- DeMiguel, V., Garlappi, L. and Uppal, R. (2009). Optimal versus naive diversification: how inefficient is the 1/N portfolio strategy? *Review of Financial Studies* 22(5), 1915–1953. — simple weights out of sample (§11).
- Erb, C. and Harvey, C. (2006). The strategic and tactical value of commodity futures. *Financial Analysts Journal* 62(2). — roll yield and the term structure (§3.6).
- Fuertes, A.-M., Miffre, J. and Rallis, G. (2010). Tactical allocation in commodity futures markets: combining momentum and term structure signals. *Journal of Banking & Finance* 34(10), 2530–2548. — the term structure as a condition on momentum (§3.6).
- Gorton, G. and Rouwenhorst, K. G. (2006). Facts and fantasies about commodity futures. *Financial Analysts Journal* 62(2). — returns of rolled commodity futures (§3.6).
- Goyal, A. and Jegadeesh, N. (2018). Cross-sectional and time-series tests of return predictability: what is the difference? *Review of Financial Studies* 31(5), 1784–1824. — net exposure (§7).
- Griveau-Billion, T., Richard, J.-C. and Roncalli, T. (2013). A fast algorithm for computing high-dimensional risk parity portfolios. Working paper, SSRN 2325255. — the coordinate-descent solver (§11).
- Lo, A. (2002). The statistics of Sharpe ratios. *Financial Analysts Journal* 58(4), 36–52. — the standard error of a Sharpe ratio (§9).
- Ma, C. K., Mercer, J. M. and Walker, M. A. (1992). Rolling over futures contracts: a note. *Journal of Futures Markets* 12(2), 203–217. — the roll date can change research results (§3.2).
- Maillard, S., Roncalli, T. and Teïletche, J. (2010). The properties of equally weighted risk contribution portfolios. *Journal of Portfolio Management* 36(4), 60–70. — equal risk contribution (§11).
- Moskowitz, T., Ooi, Y. H. and Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics* 104(2), 228–250. — returns indices from the contracts held (§3.3).
- S&P Dow Jones Indices. S&P GSCI methodology. — the roll over five business days (§3.3).
