# Lecture 15: Who Trades and What It Costs: Order Flow, Costs and Capacity

*Systematic Trading: Lecture Notes (MSc) · Oct 24, 2026 · Max Gnesi*

Every trade on the tape has a buyer and a seller, but only one of them was in a hurry: the aggressor, who took the price offered rather than waiting for a better one. This lecture asks what that hurry tells us and what it costs. The first part is about order flow: does one-sided buying or selling predict where the price goes next, what happens when a single order sweeps through the book, and can the explosive days of Lecture 14 be seen coming? The second part is about costs: what a trade really pays, when a resting order is filled, and how large a strategy can grow before its costs eat its edge. It covers the fifth and sixth of Part III's six uses of the tape (the course guide, §1.1b): order flow, and costs and capacity.

## 1. Who was in a hurry

| § | Step | Question |
|---|---|---|
| 2 | Does one-sided flow predict the price? | After strong net buying, does the price carry on or come back? |
| 3 | Sweeps and absorption | When one order sweeps through the book, does the price come back? |
| 4 | Cascades | Can the explosive regime of Lecture 14 be recognised within the day? |
| 5 | What a trade costs | What does a market order really pay, and how much is lost to the price moving on? |
| 6 | Resting orders and stops | When is a resting order filled, and what does a stop really get? |
| 7 | Capacity | How large can a strategy trade before its costs eat its edge? |
| 8 | For the two examples | What the trend rule (Lecture 16) and the grid (Lecture 17) take from this lecture |

**Three words.** The **aggressor** of a trade is the side that sent the order which executed at once, against an order already resting in the book (Lecture 12, §3.2). **Net aggressive buying**, or flow, is the dollars bought by aggressors minus the dollars sold by aggressors, here divided by all dollars traded, so that it runs from −1 (only sellers in a hurry) to +1 (only buyers). The **spread** is the gap between the best price at which someone is willing to buy and the best price at which someone is willing to sell; a market order pays at least half of it.

**Data.** The tape of Lecture 12: the BTCUSDT perpetual on Binance, October 2021 to September 2026. Where the best bid and ask are needed (§5 and §6), Binance published them only from May 2023 to March 2024; those results are labelled with that period. Depth near the price comes from Binance's snapshots every 30 seconds, from 2023 on. The full order book, every level and every change, is the subject of Part IV.

## 2. Does one-sided flow predict the price?

When buyers hurry, the price rises: they take the offers in the book, one level after another. The question here is what comes next. If the buyers knew something, the price should stay up or rise further; if they only needed to trade, the market makers who sold to them should push it partly back (Bouchaud, Gefen, Potters and Wyart, 2004).

**How it is measured.** Cut five years into windows of equal length: 1, 5 and 30 minutes. In each window measure the flow and sort the windows into fifths, from most selling to most buying. For each fifth, record the return during the window, the impact, and over the next window of the same length, what follows. Repeat for three volatility regimes, defined by the last hour's realised variance against its median over the past 28 days, so that the regime is known before the window starts.

![The return during 30-minute windows and over the next 30 minutes, by fifth of net aggressive buying, for calm, normal and volatile hours](figures/15_01_impact_and_after.png)

| | 1 minute | 5 minutes | 30 minutes |
|---|---|---|---|
| Return during the window, most selling to most buying | −5 to +5 bp | −11 to +12 bp | −27 to +28 bp |
| Next window, most buying minus most selling | −0.08 bp | −0.51 bp | −0.99 bp |
| Same, in volatile hours | −0.21 bp | −0.91 bp | −3.02 bp |

*Our measurement for these notes; the differences in the second row are 4.5 to 7.7 standard errors from zero, with days as clusters.*

Flow moves the price strongly while it happens. Afterwards a small part comes back: about 1 bp after a move of 28 bp in 30 minutes, a few percent of the impact, and almost all of it in volatile hours. The reversal is reliable, but far smaller than what a market order costs (§5): it is not a strategy on its own. It is the trace of impact that is partly temporary, as the literature describes for stocks and for bitcoin.

**With or against the trend?** The reversal could depend on what the flow pushes against. The same test, now only on the strongest flow (the top and bottom fifths), split by the slower trend known at the time (the past three days' return, divided by its typical size: up, down, or no clear trend beyond half a standard deviation) and by the volatility regime:

![The next window's return in the direction of strong flow, by trend relation and volatility regime, 5- and 30-minute windows](figures/15_02_flow_matrix.png)

The price comes back reliably in one corner only: after strong flow **with** the slower trend, in normal and volatile hours, by 0.2 to 0.5 bp after five-minute windows and 1.7 bp after thirty-minute windows in volatile hours. After flow against the trend, or with no clear trend, nothing is distinguishable from zero. When the market piles in on the side the trend already favours, at a moment of stress, the price overshoots and gives some back. In some cells the average and the day-based test point different ways, because a few extreme windows pull the average; the figure shows the day-based statistics, which are not dominated by them.

**At scheduled releases.** At a CPI release or a Fed decision, flow and price both explode. Three examples, minute by minute:

![Price and net aggressive buying from 10 minutes before to an hour after three releases](figures/15_03_releases.png)

In November 2022 buyers sent $118 million of net buying in the first minute and the price kept rising; in September 2022 sellers sent $165 million and the price kept falling; at the Fed decision of September 2022 heavy selling and heavy buying followed within two minutes and the price reversed over the hour. Across all releases, the first five minutes' **move** predicts the next thirty minutes (a correlation of +0.45 for CPI releases, −0.32 for Fed decisions, Lecture 13, §7.4), but the first five minutes' **flow** does not (+0.15 and −0.10, neither distinguishable from zero). At a release the book reprices itself: the move carries the news, and the aggressive trades are only part of it.

**Our results and the literature.**

| The literature | Our result on BTCUSDT | |
|---|---|---|
| Order flow moves the price strongly and linearly within the same interval (Cont, Kukanov and Stoikov, 2014; for bitcoin, Silantyev, 2019) | ±28 bp during 30-minute windows, more in volatile hours | in line |
| The impact of trades is partly transient: it decays and partly reverses (Bouchaud, Gefen, Potters and Wyart, 2004; Bouchaud, Farmer and Lillo, 2009; for bitcoin, Donier and Bonart) | A small part comes back in the next window | in line |
| Daily price pressure in bitcoin is mostly permanent (Makarov and Schoar, 2020) | Only a few percent of the impact comes back | in line |
| Forecasting from order flow fades within seconds to a few price changes (Kolm, Turiel and Westray, 2023, on stocks; a 2026 thesis finds nothing beyond 30 seconds on Binance's bitcoin perpetual) | Reliable but a fraction of a basis point at minutes, below the cost of trading | in line |
| Trade imbalance explains price changes about half as well as the imbalance of the whole book (Cont, Kukanov and Stoikov, 2014) | At releases, the move predicts what follows and the flow does not | consistent: the book carries information the trades do not |
| — | The reversal is reliable only after flow with the slower trend, in normal and volatile hours | not found in the literature; a result on this sample |

**Key message.** On BTCUSDT, one-sided flow moves the price while it lasts and leaves almost all of its impact in place; the small part that comes back appears after flow with the slower trend in stressed hours. At releases the price move, not the flow, carries the information. None of it pays a market order's cost by itself; whether it helps a strategy that rests its orders, a grid, is a question for §5 and Lecture 17.

## 3. Sweeps and absorption

Section 2 looked at flow added up over minutes. A single order can do the same in a millisecond: a market order larger than the depth at the best price takes the next level, and the next, until it is filled. This is a **sweep**. Behind the price it leaves a gap, and the question is who fills it and how fast. If the book refills quickly, most of the move comes back; if the sweep carried news, it stays.

**Hypotheses.** Fixed before the measurement:

| | Hypothesis | Why one might expect it |
|---|---|---|
| H1 | A large part of a sweep's move comes back within seconds | The gap behind the sweep is refilled by new resting orders: the book's resilience |
| H2 | A sweep against the slower trend comes back more than one with it | It fights the market's direction; a sweep with the trend joins it |

**How it is measured.** A sweep is one aggressive order, all fills in the same millisecond on the same side, that moves the price by at least 5, 10 or 20 bp from its first to its last fill. Over five years there are 622,818 of at least 5 bp and 179,082 of at least 10 bp. Sweeps come in bursts, so only the first in each 10-minute block is kept; with a clear slower trend, this leaves about 19,000, 5,800 and 1,600 independent sweeps for the three sizes. For each, the price is read just before it, at its last fill, and 10 seconds, 1 minute, 10 minutes and 1 hour later. The slower trend is the one of §2, the past three days' return divided by its typical size, read in the minute before the sweep.

![The median price path after independent sweeps of at least 5, 10 and 20 bp, with and against the slower trend](figures/15_04_sweep_absorption.png)

*The time axis is in steps, not to scale.*

**H1 holds.** Within ten seconds, about half of the move is gone: a sweep of 13 bp is at 5 to 7 bp after ten seconds, one of 26 bp at 10 to 14. This is the same for both directions and all sizes. The gap fills almost at once.

**H2 fails, the other way round.** After the first ten seconds, the two kinds part:

- A sweep **with** the slower trend keeps losing ground and is back near where it started within the hour. The buyer who chases a rising market overshoots, and the market takes it back.
- A sweep **against** the slower trend keeps the half that survived the first ten seconds. Over the next ten minutes the price drifts a few basis points back towards the trend, and after an hour nothing is distinguishable from zero.

The control is the same return at moments without a sweep, every tenth minute with a clear trend, in the same volatility regime. There the trend's direction says nothing about the next ten minutes or the next hour (between −3 and +2 bp on average). The table gives the return in the trend's direction after the sweep's last fill, minus that control:

| Sweep | Size | Next 10 minutes | Next hour |
|---|---|---|---|
| with the trend | ≥ 5 bp | −4.8 bp (−8.8)\*\*\* | −7.4 bp (−4.3)\*\*\* |
| | ≥ 10 bp | −11.4 bp (−9.9)\*\*\* | −14.8 bp (−5.6)\*\*\* |
| | ≥ 20 bp | −20.6 bp (−6.6)\*\*\* | −26.1 bp (−5.0)\*\*\* |
| against the trend | ≥ 5 bp | +2.8 bp (4.9)\*\*\* | +1.2 bp (0.7) |
| | ≥ 10 bp | +4.1 bp (3.4)\*\* | −1.6 bp (−0.6) |
| | ≥ 20 bp | +7.5 bp (2.4)\* | −12.7 bp (−2.1)\* |

*Our measurement for these notes. Negative: the price moves back against the trend, that is against the sweep. In brackets the t-statistic, with days as clusters; stars after the Benjamini–Hochberg correction over the 16 tests (including the hourly-block variant below): \* q < 0.05, \*\* q < 0.01, \*\*\* q < 0.001.*

**Robustness.** The reversal after sweeps with the trend appears in every year from 2021 to 2026 (between −5 and −16 bp after ten minutes for sweeps of at least 10 bp), in calm, normal and volatile hours, and when only the first sweep per hour is kept (−8.6 bp after ten minutes, t −6.6). After sweeps against the trend the picture is less stable: the ten-minute drift towards the trend survives the hourly blocks (t 4.0); the hour after does not, and its sign changes from year to year.

**An open question.** In volatile hours, sweeps against the trend are followed by large moves further against it in some years (a median of −18 bp over the hour for sweeps of at least 10 bp), but the effect is not significant after correction, vanishes with hourly blocks and flips sign between years. Whether such a sweep marks the first crack of a trend, the forced selling of a liquidation cascade, is a question for §4, not a result here.

**Our results and the literature.**

| The literature | Our result on BTCUSDT | |
|---|---|---|
| After large trades the book is replenished quickly; new orders flow into a thin book (Biais, Hillion and Spatt, 1995) | About half of a sweep's move is gone within ten seconds | in line |
| The impact of aggressive orders is partly reversed in later trades, but a longer-term effect remains (Degryse, de Jong, van Ravenswaaij and Wuyts, 2005; for single trades, Bouchaud, Gefen, Potters and Wyart, 2004) | Part comes back, part stays | in line; the ten-second scale of a single sweep is our measurement |
| Trades in the direction of the prevailing flow meet more liquidity and move the price less permanently (Farmer, Gerig, Lillo and Mike, 2006); after a long price run-up, block purchases carry less permanent impact (Saar, 2001) | Sweeps with the slower trend are taken back almost completely | consistent in spirit; neither conditions on the trend as we do |
| Moves that trigger clustered stop-loss orders run on (Osler, 2005, for currencies) | Sweeps against the trend keep their remaining half | a possible mechanism, not tested here |
| — | The reversal depends on the sweep's relation to the slower trend | not found in the literature; a result on this sample, open to independent tests |

**Key message.** About half of a sweep comes back within seconds, whatever its direction: the book refills. What remains depends on the slower trend. A sweep that chases the trend overshoots and is taken back within the hour; one against the trend keeps its remaining half. For a strategy that rests orders in the book, a grid, this is the difference between a fill that is soon in profit and one that stays at a loss. Whether that pays after costs is a question for §5 and Lecture 17.

