# Lecture 13: When the Market Trades: Clocks and Seasonality

*Systematic Trading: Lecture Notes (MSc) · Oct 21, 2026 · Max Gnesi*

Every bar so far closed on the clock: at the end of a day in Parts I and II, at the end of a minute in Lecture 12. This lecture asks when the market trades. It builds bars that close after a fixed amount of trading, of one-sided pressure, or of price movement, from the same five years of BTCUSDT trades as Lecture 12, and asks whether they describe the market better; then it maps the market's rhythms: the time of day, the week, the round clock times and the scheduled events. It covers the first and fourth of Part III's six uses of the tape (the course guide, §1.1b): a clock, and seasonality.

## 1. Which clock should a bar follow?

Every bar closes when a counter reaches a threshold. For a one-hour bar the counter is seconds, and the threshold is 3,600. The counter can be anything that rises as the market trades: the number of trades, the dollars traded, the distance the price has moved. This counter is the bar's **clock**, and the literature uses the word in exactly this sense: business or intrinsic time (Mandelbrot and Taylor, 1967; Dacorogna et al., 2001), the transaction clock (Ané and Geman, 2000), the volume clock (Easley, López de Prado and O'Hara, 2012). A dollar bar follows a clock, one that counts dollars instead of seconds.

**Why change the clock.** Lecture 12 found the market's activity very uneven: the busiest hour of the day trades three times as much as the quietest, a weekend day half as much as a weekday, and 1% of the minutes hold a third of five years' variance (Lecture 12, §6.2 and §7.3). A one-minute bar at 4 a.m. and a one-minute bar after a Federal Reserve decision measure very different amounts of market. Volatility follows the number of trades, not the passing of time: the number of trades explains 85% of the variation in hourly variance (Lecture 12, §7.3). A bar that closes after a fixed amount of trading should therefore hold a more constant amount of information.

**The hypothesis, and its limits.** If prices move in trading time rather than in calendar time, returns measured on a trading clock should be closer to the normal distribution, with thinner tails and steadier volatility from bar to bar (Clark, 1973; Ané and Geman, 2000). The claim is contested: on stock data, the normality of returns on a transaction clock does not hold as cleanly as first reported (Murphy and Izzeldin, 2005). This lecture tests it on our data.

| § | Step | Question |
|---|---|---|
| 2 | The four families | Which clocks are there, and what is each one for? |
| 3 | Building bars from the tape | How is each bar type cut, and how is its threshold set? |
| 4 | Do they differ? | How often do different clocks close at the same moments? |
| 5 | Are returns closer to normal? | Tails, volatility clustering and autocorrelation, bar type by bar type |
| 6 | Imbalance bars, two versions | Does the published construction behave well on our data? *(deep dive)* |
| 7 | Seasonality | When does the market trade: the time of day, the week, the round clock times, scheduled events, and how they have changed? |
| 8 | For the two examples | What the trend rule (Lecture 16) and the grid (Lecture 17) take from this lecture |

**Data.** The derived layer of Lecture 12: BTCUSDT perpetual on Binance, October 2021 to September 2026, 2.6 billion trades, checked and patched (Lecture 12, §5). The bars are built with the same day-by-day machinery (Lecture 12, Appendix A).

## 2. The four families

The clocks fall into four families, by what their counter measures.

| Family | The counter, the bar's clock | A bar closes when… | Examples |
|---|---|---|---|
| **Time** | Seconds | a fixed time has passed | One-minute, one-hour, daily bars |
| **Activity** | Trades, coins or dollars | a fixed amount of trading has happened | Tick, volume and dollar bars |
| **Information** | One-sided trading | buying or selling has become more one-sided than usual | Imbalance and run bars |
| **Price** | Price movement | the price has moved a fixed distance | Range bars, Renko bricks, the CUSUM filter |

Every family still produces bars with an open, high, low, close and volume: what changes is only when a bar ends (Lecture 12, §8).

### 2.1 Time

Time bars are the benchmark. They are simple, every data vendor supplies them, and returns over equal times are directly comparable: a daily volatility can be annualised, and two markets' bars close at the same moments. Their weakness is the one of §1: a fixed time holds a variable amount of trading, little at night and very much after a central-bank decision.

### 2.2 Activity: tick, volume and dollar bars

| Bar | Closes after | Strength | Weakness |
|---|---|---|---|
| **Tick** | a fixed number of trades | Follows activity automatically; the number of trades is what volatility follows (Lecture 12, §7.3) | What counts as one trade depends on the data: Binance's aggregated tape has 2.5 times fewer rows than its file of single fills (Lecture 12, §8.1), and an order split into pieces counts many times |
| **Volume** | a fixed number of coins | Not changed by splitting an order | The same number of coins is worth very different amounts over time: one bitcoin cost about $20,000 in 2022 and over $100,000 in 2025 |
| **Dollar** | a fixed amount of money | Each bar is the same amount of economic activity, whatever the price | The amount of trading itself drifts: on average, $11.5 billion a day in 2023 and $17.8 billion in 2024 (Lecture 12, §6.1). A fixed threshold gives far fewer bars in a quiet year; §3 sets it from the recent past instead |

Dollar bars are the natural representative of the family, and the one López de Prado (2018, ch. 2) recommends: they measure activity in the unit a trader cares about.

### 2.3 Information: imbalance and run bars

Information bars close when the order flow becomes more one-sided than usual, using the aggressor flag of each trade (Lecture 12, §3.2), which candles do not have (Lecture 12, §8.3).

| Bar | Closes when | What it aims to catch |
|---|---|---|
| **Imbalance** | the running sum of buys minus sells, in trades, coins or dollars, exceeds what is normally seen | The moments when one side takes over: informed trading, forced liquidations |
| **Run** | the longest sequence of trades on one side exceeds what is normally seen | A large order executed in many small pieces, all on the same side (Lecture 12, §7.1) |

Both are defined by López de Prado (2018, ch. 2), with thresholds estimated from past bars. The idea is attractive, since one-sided flow is exactly what moves prices (Lecture 12, §6.5), but the construction has two known weaknesses: the threshold depends on the bars it produces, which can make bar sizes run away, and it falls to almost nothing when buying and selling are balanced. §6 builds the published version and a stabilised one side by side, on our data.

### 2.4 Price: range bars, Renko and the CUSUM filter

| Bar | Closes when | What it aims to catch | Weakness |
|---|---|---|---|
| **Range** | the high and low of the bar are a fixed distance apart | Every bar holds the same price movement, so a trend rule sees moves, not minutes | The number of bars explodes in volatile markets; the high and low carry no information, being fixed; a gap, like the 2.3% jump of the flash crash in Lecture 12, §5.4, overshoots the bar |
| **Renko** | the price has moved a fixed distance beyond the last brick; a reversal needs twice that | A trend-following picture: small back-and-forth moves draw nothing | Discards time and volume; reversals are recognised late; a brick's price is not a traded price, an easy source of optimistic backtests |
| **CUSUM filter** | the cumulative movement of the price since the last event exceeds a threshold, in either direction (Page, 1954) | Not a bar but a trigger for *when to look*: a strategy evaluates its signal only after a real move | The threshold decides everything; events cluster in stress |

The CUSUM filter is a sampling rule rather than a bar, and López de Prado (2018, ch. 2) uses it to decide when a strategy should take a decision at all: fewer decisions, made after real moves, mean less turnover and lower costs. It belongs here because it is a clock that ticks only when the price moves.

### 2.5 What every clock shares

Three rules apply to every family, and to every later lecture that uses these bars:

| Rule | Why |
|---|---|
| A bar is known only when it closes, at the trade that crosses the threshold | Its close is a trade that has already happened; an order sent on it fills at a later trade, on its own side (Lecture 12, §9.2) |
| Thresholds use past data only | A threshold set from the whole sample tells each bar how much trading lies ahead |
| Bar types are compared at the same number of bars per day | A clock that closes more often looks smoother only because it is finer; equal frequency is the bar equivalent of equal speed in Lecture 7 |

From each family the lecture builds one representative, plus time bars as the benchmark: **dollar bars** for activity, **dollar-imbalance bars** for information (in both versions of §6), **range bars** for price, and the **CUSUM filter** as a sampling rule. Tick and volume bars are built too, briefly, to show why dollar bars are preferred.

## References

- Ané, T. and Geman, H. (2000). Order flow, transaction clock, and normality of asset returns. *Journal of Finance* 55(5), 2259–2284. — the transaction clock; normality in trading time (§1).
- Clark, P. K. (1973). A subordinated stochastic process model with finite variance for speculative prices. *Econometrica* 41(1), 135–155. — volume as the clock of prices (§1).
- Dacorogna, M. M., Gençay, R., Müller, U. A., Olsen, R. B. and Pictet, O. V. (2001). *An Introduction to High-Frequency Finance*. Academic Press. — intrinsic time (§1).
- Easley, D., López de Prado, M. and O'Hara, M. (2012). The volume clock: insights into the high-frequency paradigm. *Journal of Portfolio Management*, Fall 2012. — the volume clock (§1).
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley, ch. 2. — tick, volume, dollar, imbalance and run bars; the CUSUM filter (§2).
- Mandelbrot, B. and Taylor, H. M. (1967). On the distribution of stock price differences. *Operations Research* 15(6), 1057–1062. — prices in transaction time (§1).
- Murphy, A. and Izzeldin, M. (2005). Order flow, transaction clock and normality of asset returns: a comment on Ané and Geman (2000). Working paper. — the limits of normality in trading time (§1).
- Page, E. S. (1954). Continuous inspection schemes. *Biometrika* 41(1/2), 100–115. — the CUSUM test (§2.4).
