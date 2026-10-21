# Lecture 12: Tick Data, the Tape

*Systematic Trading: Lecture Notes (MSc) · Oct 21, 2026 · Max Gnesi*

Parts I and II worked with bars: a day of trading compressed into an open, high, low, close and volume. Part III goes underneath the bar, to the record of every trade. This lecture describes that record, which practitioners call the tape: how to get it, what one row of it means, how to check it, and what it shows that a bar cannot. It builds no strategy; Lectures 13 to 17 do. *Draft: written step by step; §1 to §4 so far.*

## 1. The question of this lecture

What does a bar hide, and what does the record of every trade add?

Lecture 2 described a bar as compression: thousands of trades reduced to five numbers. The compression keeps the path's endpoints and extremes and the total volume, and throws away everything else. The tape keeps it all:

| | A daily bar (Lectures 2 to 11) | The tape |
|---|---|---|
| Unit of observation | One day | One trade, or a burst of trades within a tenth of a second |
| Time | The close of the day | The millisecond |
| Price | Four prices: open, high, low, close | Every price traded |
| Size | Total volume | The size of every trade |
| Who traded | Unknown; estimated in Lecture 3 from the bar (on-balance volume, bulk volume classification) | Recorded: whether the buyer or the seller was the aggressor |
| Rows per year, one market | About 250 (futures) or 365 (crypto) | Hundreds of millions |

| Question | Section |
|---|---|
| Where does the data come from, and how is it stored? | §2 |
| What is the instrument? | §3 |
| What does one row mean? | §4 |
| Is the data clean? | §5 |
| What does the tape look like statistically? | §6 |
| What exactly does a bar lose? | §7 |

The market throughout is the **BTCUSDT perpetual** on Binance: the most traded futures contract in crypto, open every hour of the year, with a free and complete public archive.

## 2. Getting the data

### 2.1 What the archive offers

Binance publishes its market data as daily and monthly files at data.binance.vision, free and without an account.

| Market | Data | What a row is | Used in |
|---|---|---|---|
| Spot, USDⓈ-M futures (settled in USDT), COIN-M futures (settled in the coin) | `trades` | One fill between one aggressive and one resting order | Mentioned only |
| | **`aggTrades`** | **All fills within 100 milliseconds at the same price on the same side, combined** | **This lecture and Part III** |
| | `klines` | A candle: open, high, low, close, volume, at intervals from one second to one month | §7, as a check |
| USDⓈ-M futures | `bookTicker` | The best bid and best ask, with their sizes, at every change | Lecture 16 |
| | `fundingRate`, `metrics` | Funding payments; open interest and positioning | §3 |

**Why aggregated trades.** Single fills multiply the number of rows by about 2.7 without adding information a trader can act on: the fills of one burst share a price, a side and a tenth of a second. Aggregated trades are the standard unit for research on the tape.

### 2.2 Step by step

The data are kept on disk as Parquet, a compressed column format, and every monthly file is checked before its download is deleted.

| Step | What | Why |
|---|---|---|
| 1. Download one month | `BTCUSDT-aggTrades-YYYY-MM.zip` from the folder `futures/um/monthly/aggTrades/BTCUSDT/` | Monthly files keep the number of downloads small |
| 2. Verify | Compare the file's SHA-256 hash with the `.CHECKSUM` file published next to it | Detects a broken or incomplete download before anything is built on it |
| 3. Convert | Read the CSV inside the zip with explicit column types and write it as Parquet with zstd compression | A third smaller than the zip, and read in seconds instead of minutes |
| 4. Check the Parquet file | Same number of rows as the CSV; the trade identifiers increase by exactly one from row to row; no timestamp earlier than the one before | Proves the conversion is complete and the month has no missing rows |
| 5. Delete the zip, log the month | Only after step 4 passes; append rows, first and last identifier and timestamp, sizes and the hash to a manifest | Saves disk space; the manifest records what was checked |

Older files have no header row and newer ones do; step 3 has to handle both. Like the futures data of Lecture 11, the files stay local and are never committed or published.

**Sizes.** September 2026 alone has 36.0 million aggregated trades: 437 MB as a zip, 285 MB as Parquet, converted and checked in 77 seconds. The five years from October 2021 to September 2026 come to about 20 GB of Parquet.

### 2.3 Reading it

A month of tape does not need to fit in memory to be analysed. Polars and DuckDB read Parquet lazily: they load only the columns and rows a query needs, and Parquet stores the minimum and maximum of each column per block, so a filter on time skips the blocks outside it.

```python
import polars as pl

tape = pl.scan_parquet("data/raw/binance/um/aggTrades/BTCUSDT/parquet/*.parquet")   # nothing is read yet
daily = (tape.with_columns(pl.from_epoch("transact_time", time_unit="ms").alias("time"))
             .group_by_dynamic("time", every="1d")
             .agg(pl.len().alias("trades"), (pl.col("price") * pl.col("quantity")).sum().alias("usd"))
             .collect())                                                             # five years, one pass
```

## 3. What a perpetual is

A perpetual future is a futures contract that never expires. There is no roll, so none of the machinery of Lecture 11, §3, is needed: one contract, one price series. What replaces expiry is a payment that keeps the contract's price close to the price of the coin itself.

| Element | How it works on the BTCUSDT perpetual |
|---|---|
| Contract | Long or short bitcoin against USDT, quantity in bitcoin; profit in USDT = quantity × price change |
| Index price | A weighted average of the bitcoin price on several spot exchanges: what the contract is meant to track |
| Last price | The price of the latest trade on the contract: what the tape records |
| Mark price | The index price adjusted by a smoothed basis; used to value positions and trigger liquidations, so that one trade cannot force them |
| **Funding** | Every 8 hours, at 00:00, 08:00 and 16:00 UTC, longs pay shorts (or shorts pay longs, if the rate is negative) a percentage of their position. The rate has a fixed interest part of 0.01% per period and a premium part that rises when the contract trades above the index and falls when it trades below |
| Margin and leverage | A position needs only margin, a fraction of its value; leverage of up to 125 times is allowed for small positions, less for large ones |
| **Liquidation** | When losses consume a position's margin, the exchange closes it with a market order |
| Tick and lot | Prices move in steps of $0.10 (since February 2022; $0.01 before), quantities in steps of 0.001 bitcoin; orders must be worth at least $50 |

**Funding is the perpetual's carry.** In Lecture 11 a futures holder earned or paid the roll yield at each roll (§3.6); on a perpetual the same carry is paid continuously, three times a day. Over the five years from October 2021:

| Funding, BTCUSDT perpetual, Oct 2021–Sep 2026 | |
|---|---|
| Payments | 5,478, every 8 hours |
| Average rate per payment | 0.0066% |
| Paid by longs to shorts per year, on average | **7.3%** |
| Share of payments positive | 85% |
| Share of payments at exactly the default 0.01% | 29% |
| Range per payment | −0.12% to +0.09% |

A long position paid about 7% a year for holding bitcoin through the perpetual, about what a holder of crude oil futures lost through its rolls in Lecture 11 (6.9% a year). The sign reflects demand: more traders want to be long with leverage than short, and they pay for it.

**Liquidations are forced trades.** When the price moves fast, positions that run out of margin are closed with market orders, which push the price further and can liquidate the next layer. These are the liquidation cascades of Lecture 5, §3.3: one of the frictions that create persistence, here visible in the tape as bursts of aggressive trades on one side. Lecture 15 studies them.

## 4. What a row represents

### 4.1 An aggregated trade

A trade happens when an aggressive order meets a resting order. The resting order was waiting in the order book at its price: its owner is the **maker**, who supplied liquidity. The aggressive order arrived and crossed the spread to take it: its owner is the **taker**. A large aggressive order can be filled against several resting orders at the same price, and several aggressive orders can arrive within a tenth of a second. On USDⓈ-M futures, Binance combines all fills within 100 milliseconds at the same price on the same side into one aggregated trade.

### 4.2 The seven fields

| Field | Unit | Meaning | What it tells a trader |
|---|---|---|---|
| `agg_trade_id` | Integer | Sequence number of the aggregated trade, increasing by one | Completeness: a gap in the sequence is a missing trade (§5) |
| `price` | USDT per bitcoin | The price at which the fills happened | Every traded price, on the $0.10 grid |
| `quantity` | Bitcoin | The total size of the fills | Size of the move a trader made; in dollars, price × quantity |
| `first_trade_id`, `last_trade_id` | Integer | The first and last single fill inside the aggregate | How many fills it combines: last − first + 1 |
| `transact_time` | Milliseconds since 1 January 1970, UTC | When the matching engine executed the fills | Timing to the millisecond; the gaps between trades (§6) |
| **`is_buyer_maker`** | True or false | **True: the buyer's order was resting, so the seller was the aggressor. False: the buyer was the aggressor** | **Who was in a hurry.** A sell market order hitting the bids is `true`. The name inverts the usual reading, so it is safest to define a sign once: +1 for aggressive buying (`false`), −1 for aggressive selling (`true`) |

The first six rows of September 2026:

| `agg_trade_id` | `price` | `quantity` | `first_trade_id` | `last_trade_id` | `transact_time` | `is_buyer_maker` | Reading |
|---|---|---|---|---|---|---|---|
| 3435054521 | 78549.6 | 0.025 | 8038326171 | 8038326172 | 1788220800003 | false | 3 ms after midnight UTC, a buyer takes 0.025 BTC ($1,964) at the ask, in 2 fills |
| 3435054522 | 78549.5 | 0.016 | 8038326173 | 8038326177 | 1788220800016 | true | 13 ms later, a seller hits the bid 10 cents lower: 5 fills |
| 3435054523 | 78549.5 | 0.003 | 8038326178 | 8038326178 | 1788220800182 | true | Another sell at the bid, one fill |
| 3435054524 | 78549.5 | 0.139 | 8038326179 | 8038326184 | 1788220800566 | true | A larger sell, $10,918, 6 fills |
| 3435054525 | 78549.6 | 0.038 | 8038326185 | 8038326185 | 1788220800595 | false | A buy at the ask again |
| 3435054526 | 78549.5 | 0.097 | 8038326186 | 8038326187 | 1788220800607 | true | A sell at the bid |

The price bounces between 78,549.5 and 78,549.6 as buyers take the ask and sellers hit the bid: the **bid-ask bounce**. Measured from trade to trade, the price seems to move although the market has not; Lecture 3, §4.4 met the same effect as a source of bias in range-based volatility, and §6 measures it.

### 4.3 One month at a glance

| September 2026 | |
|---|---|
| Aggregated trades | 36.0 million, about 14 a second |
| Single fills per aggregated trade | 2.7 on average, up to 2,081 |
| Value of a trade | Median $232, mean $9,532, largest $50 million |
| Value traded | $344 billion |
| Share of trades with an aggressive buyer | 50.0% |
| Price range | $74,909 to $87,385 |

- **Trade sizes are extremely skewed.** The mean is forty times the median: most trades are small, and a few very large ones carry much of the volume. §6 shows the whole distribution.
- **Buying and selling aggression balance over a month**, but not over minutes: Lecture 15 asks whether the imbalance predicts the next move.
- **The aggressor flag is the order flow that Lecture 3, §7, could only estimate.** On-balance volume assigned a whole day's volume to buyers or sellers by the sign of the close-to-close change; bulk volume classification split it by the size of the move. Here every trade is labelled, and §7 compares the estimates with the truth.

*Next: §5, a data quality scan over five years.*

## References

- Binance. USDⓈ-M futures API documentation: compressed aggregate trades list; exchange information; funding rate history. — definitions and contract terms (§2–§4).
