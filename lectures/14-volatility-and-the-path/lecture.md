# Lecture 14: How the Price Moves: Volatility and the Path

*Systematic Trading: Lecture Notes (MSc) · Oct 22, 2026 · Max Gnesi*

A bar keeps four prices of everything that happened inside it. This lecture looks at what it throws away, the path between those prices, and at the number that summarises how much a price moves, its volatility. The path decides whether a stop or a target is hit first, how often a grid's orders fill, and how far a position runs against its owner before it is closed; volatility decides how large a position may be, how wide a grid should be spaced and where a stop belongs. Both are measured on the same five years of BTCUSDT trades as Lectures 12 and 13. The lecture covers the second and third of Part III's six uses of the tape (the course guide, §1.1b): the path between bars, and volatility measured precisely.

## 1. What a bar does not tell

| § | Step | Question |
|---|---|---|
| 2 | What a candle loses | What does a bar not record, and when does that matter? |
| 3 | The path against a random walk | Does the price behave like a path without memory, and does that hold on every day? |
| 4 | Levels on the path | How often is a level crossed, how far does a position run against its owner, and what happens when the price jumps a level? |

**A unit before we start.** Every statement about the path needs a scale: is a move of 50 basis points large or small? The scale is volatility, the typical size of the price's moves over a given time. Here it is measured in the simplest way the tape allows: square each one-minute return of a day and add them up. The sum is the day's **realised variance**, its square root the day's volatility. A random walk spreads its moves evenly, so its variance grows in proportion to time and its volatility with the square root of time, √t: four times the time, twice the move. §3 tests whether the price follows that rule; the second half of the lecture asks how volatility should be measured and used.

**Data.** As in Lectures 12 and 13: the BTCUSDT perpetual on Binance, October 2021 to September 2026, from the tape of Lecture 12. The path is followed minute by minute, from one-minute closes; where single trades matter, from the trades themselves.

## 2. What a candle loses

A candle records the first and last price of a bar and its extremes. It records neither **what happened first** nor **how far the price travelled** in between.

**What came first.** A backtest on candles must guess whether the high or the low came first; on the tape, the order is known. Two common guesses, checked against the tape:

| Bar | "The bar's direction": a rising bar went to its low first | "The open nearer the high": then the high came first |
|---|---|---|
| 5 minutes | right on 90% of bars | 81% |
| 1 hour | 88% | 80% |
| 1 day | 88% | 81% |
| A random walk, any length | 89% | 81% |

*Our measurement for these notes; the random walk by simulation.*

The better guess is wrong on about one bar in eight, at every bar length, and a random walk gets it wrong just as often. The error is not a feature of bitcoin; it is built into candles.

It matters only when two levels lie inside the same bar. A rule that enters at the open with a stop and a target the same distance away must know which was hit first, and on hourly bars of BTCUSDT:

| Stop and target, × the typical range of an hour | Bars that touch both | The best guess right, on those |
|---|---|---|
| 0.25 | 40% | 68% |
| 0.5 | 13% | 76% |
| 1 | 2% | 80% |

*Our measurement for these notes; the truth from the first minute in which each level was touched; the typical range is the median of the past 28 days.*

**The distance travelled.** Measured minute by minute, the typical hour travels about four times its own range: up, down and up again before it closes. Among hours with almost the same candle, the distance runs from 3 to 5.3 times the range (10th to 90th percentile).

![Two hours with almost the same open, high, low and close, minute by minute](figures/14_01_same_candle_different_paths.png)

The two hours in the figure have the same candle to within a few basis points. The first rose almost steadily from its low; the second swung back and forth and travelled more than twice as far. A trend rule sees no difference; a grid, which earns each time the price swings through one of its levels, would have earned more than twice as much in the second hour.

**What it means.** The stop distance relative to a bar's range decides whether a candle backtest can be trusted: wide stops are hardly affected, tight ones are guessed wrong on a large share of bars. And everything that depends on the distance travelled, a grid's earnings or a measure of volatility, needs the path, not the candle. §3 and §4 measure the path; the second half of the lecture measures volatility from it.

## 3. The path against a random walk

A random walk has no memory: after a move up, the next move is up or down with equal chance. A grid needs the price to turn back; a trend rule needs it to carry on. The question for both: after the price has moved one step, does it move another step the same way, or turn back?

**How it is measured.** Lay a ladder of levels a fixed step apart over five years of one-minute prices. Each time the price reaches a new rung, record whether it came from below or above; then count how often the next rung reached lies in the same direction. For a random walk the answer is one half.

**The benchmark matters.** Counted this way, the price of bitcoin seems to carry on far more often than a random walk: two steps in three at 10 basis points. But the same count on the same one-minute returns **shuffled into a random order**, which keeps every move's size and removes all memory, gives almost the same result: a minute that jumps over several rungs makes all of them look like continuation. The fair comparison is the tape against its own shuffled returns, not against one half.

| Step | Tape: continues | Shuffled: continues | Difference, points | In every year? |
|---|---|---|---|---|
| 10 bp | 66.8% | 68.8% | −2.0 | yes |
| 20 bp | 61.3% | 62.7% | −1.4 | yes |
| 50 bp | 56.4% | 57.2% | −0.8 | yes, more weakly |
| 100 bp | 54.6% | 54.8% | −0.2 | no difference |

*Our measurement for these notes; one-minute closes, October 2021 to September 2026.*

At small steps bitcoin turns back slightly more often than a path without memory; at a percent and more there is no difference. That is the five-year average. It hides two different markets.

**Two regimes.** The same test, with the days grouped by their realised variance:

![Continuation against the shuffled path, by step size, for days grouped by their volatility](figures/14_02_two_regimes.png)

| Days | 20 bp | 50 bp | 100 bp |
|---|---|---|---|
| The calmest half (913 days) | −3.1 | −4.7 | −2.2 |
| The most volatile 10% (183 days) | −0.9 | +1.0 | +2.7 |
| The most volatile 2% (37 days) | −0.1 | +2.1 | +4.0 |

*Points of continuation, tape minus its own returns shuffled within the same days; the figure shows all groups with their 95% intervals.*

On calm and ordinary days the price turns back clearly more often than chance, at every step size. On the most volatile days the picture reverses at larger steps: moves of half a percent and more tend to carry on. The average of five years describes neither: a grid that relies on it is right on ordinary days and wrong on exactly the days that can ruin it.

**Can the regime be seen in advance?** Grouped by the *previous* day's volatility, which is known in the morning, the runs disappear: yesterday's volatility does not say whether today will be an explosive day. The regime has to be recognised within the day, from what the market is doing now. Lecture 15 looks for such signals in the order flow, and Lecture 17 uses them to decide when a grid steps aside.

**And √t?** If the price turns back, its moves over longer horizons are smaller than √t predicts from one-minute moves. The variance ratio measures by how much: the variance of returns over a horizon, divided by what the one-minute returns of the same weeks imply.

![The variance ratio from five minutes to a week, five years and year by year](figures/14_03_variance_ratio.png)

At four hours the variance is 13% below what one-minute returns imply (90% interval: 9% to 16%), and the shortfall appears in every year.

Scaling one-minute volatility with √t overstates the variance of a position held for hours by 5% to 13%, every year; at a day by about 9%; beyond a day the data cannot tell. The volatility half of the lecture returns to this: risk should be measured at a fine interval and scaled to the horizon a strategy holds with the measured ratio, not with √t.

**Key message.** Bitcoin's path is close to a random walk, but not quite, and not in the same way every day: it turns back on ordinary days and runs on explosive ones. A rule built on the average is built for a market that does not exist.

## 4. Levels on the path

A grid lives on the number of times the price crosses its levels; a stop on what happens when the price reaches it. Both are questions about the path at a level.

### 4.1 Crossings: what a grid can earn

For a random walk the number of steps of a given size per day is simple: the day's variance divided by the step squared. A grid that expects that many round trips is disappointed:

![Steps per day of 20, 50 and 100 bp against the random-walk count, calm and volatile days](figures/14_04_crossings.png)

The price completes only 40% to 72% of the steps the day's variance promises. The main reason is the size of the moves, not their order: a jump of 3% crosses six levels 50 bp apart, but it counts in the variance like 36 small moves. Large moves inflate variance much more than they cross levels, which is why the shortfall is largest for tight grids on volatile days. On calm days the turning back of §3 costs crossings as well: a price that keeps returning does not travel far. **A grid's spacing should be planned on counted crossings, not on variance.**

### 4.2 Excursions: what a position must survive

Open a position at every full hour, hold it four hours, and record the worst move against it, in units of the volatility expected for four hours (σ√T, with σ from the past 28 days):

![The share of positions whose worst move exceeds k times the expected volatility, against a random walk](figures/14_05_excursions.png)

The typical bad move is smaller than a random walk's: 0.64 σ√T on average, against 0.80. The rare one is far larger: a move beyond 3 σ√T, which a random walk makes 0.27% of the time, comes in 1.7% of positions, six times as often, and in 8.8% on the most volatile days, thirty times. A stop set on √t is too wide most of the time and too close in the tail. What a stop should be depends on its purpose: an active stop, which ends a trade that is not working, belongs where the typical excursion would rarely reach; a ring-fence, which only guards against disaster, is reached in the tail, and there the question is what it gets.

### 4.3 Gaps: what a stop gets

Measured with the right side of the trades (a sell stop is filled by sellers, at the bids), the path hardly ever skips a level on BTCUSDT: at the trigger, the first trade on the stop's side lies within 0.2 bp of the level in 99% of cases, on calm and on volatile days. And a resting order at a level was traded through, filled for certain, on more than 99.7% of visits: with a tick of ten cents the price almost never turns at exactly that price, so the place in the queue rarely decides whether it is filled. On a market with a coarser tick it would.

**What a stop gets, approximately.** The tape does not show the order book, so it cannot say what a stop-market order would have received. It shows what the sellers who followed the trigger actually got. Read within a second, it approximates what an instant order meets; within ten seconds, what a larger order spread over time would face, including the market's move meanwhile. The worst price any of them got is a conservative estimate, valid for orders no larger than what traded in that time.

![The worst price of the sellers who followed a stop's trigger, by time window, calm and volatile days](figures/14_06_stop_fills.png)

| Worst seller's price beyond the level | Median | Worst 5% | Worst 1% |
|---|---|---|---|
| Within 1 second, calm days | 2 bp | 14 bp | 23 bp |
| Within 1 second, volatile days | 4 bp | 33 bp | 76 bp |
| Within 10 seconds, volatile days | 11 bp | 122 bp | 209 bp |

*Our measurement for these notes; every first crossing of levels 20, 50 and 100 bp apart, 120 calm and 183 volatile days. Even in a slow second, at least $0.3 million (calm) to $0.7 million (volatile) was sold in nine cases out of ten.*

A typical stop costs a few basis points; the tail is fat and depends on the regime. The worst cases are short runs: the price breaks a level and runs 50 to 100 bp in a few seconds, often ending at a round price (19,200; 30,250; 105,000), where resting orders seem to stand. That is a hypothesis; the order book would show it.

**A building block for backtests.** *A stop fills at the worst price of the next second, at a chosen percentile of this distribution*: an explicit, conservative fill rule that a backtest on bars can use without the tape. It is valid up to the size that traded in that second, and in a backtest the regime must be judged from what is known at the trigger, such as the volatility of the last hour, not from the whole day. Lecture 15 measures the order book, how much size a level absorbs and how fast it recovers, and turns this rule into a fair cost of stops; Lectures 16 and 17 use it.

