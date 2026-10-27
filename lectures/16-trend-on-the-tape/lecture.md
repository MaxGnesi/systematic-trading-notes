# Lecture 16: A Trend Rule on the Tape: Deciding, Measuring and Trading on Three Clocks

*Systematic Trading: Lecture Notes (MSc) · Oct 27, 2026 · Max Gnesi*

Lectures 12 to 15 measured what the tape adds to bars: when the market trades, how the price moves inside a bar, who is in a hurry and what a trade costs. This lecture applies those measurements to the first of Part III's two examples, the trend rule of Part II, on five years of BTCUSDT. The question is practical: what does the tape change for a trend rule, and what does it leave as it was? The answer is organised around one idea, that a strategy runs on three clocks, not one, and that each of them can be chosen separately.

## 1. Three clocks

| § | Step | Question |
|---|---|---|
| 2 | The rule on BTCUSDT | Which speeds work on this market, and how often should the rule look? |
| 3 | The information clock | How does information from another clock reach an hourly rule, and does it help? |
| 4 | Risk | Does sizing by a sharper forecast of risk improve the rule? |
| 5 | The execution clock | What does a patient entry save? |
| 6 | Holding | Perpetual or spot: what does it cost to hold a position? |
| 7 | The rule built up | What each step adds, after all costs |
| 8 | For the grid | What the grid of Lecture 17 takes from this lecture |
| 9 | Summary, exercises and reading | |

**The promise of other clocks.** Lecture 13 cut the tape into bars by trades, by volume and by dollars instead of by time, and found returns that behave better: fewer extreme bars, a steadier variance. The classic results say the same: returns measured in trading time come closer to the normal distribution than returns measured in clock time (Clark, 1973; Ané and Geman, 2000), and López de Prado (2018) recommends bars cut by activity for financial machine learning for this reason. It is tempting to conclude that a strategy run on such bars will do better.

**What the evidence says.** Better-behaved returns are a statement about measurement, not about profit. We found no published study showing that a trend rule earns more on bars cut by activity than on bars cut by time. The closest test, on the same market as this lecture, the Binance bitcoin perpetual, finds that dollar bars have the best statistical properties of all the bars it compares, yet predict no better and lose money in every backtest; in its authors' words, statistical quality and predictability appear to be largely orthogonal (Fayyaz et al., 2026, preprint). Whether a clock helps a trend rule is therefore an open question, and this lecture treats it as one.

**Three clocks, not one.** The usual way of putting the question, time bars against dollar bars, mixes three choices that a strategy makes separately:

| Clock | The question it answers | In this lecture's rule |
|---|---|---|
| **Decision clock** | When does the rule decide? | At every hourly close |
| **Information clock** | On which samples are its measurements built? | Hourly closes, or dollar bars |
| **Execution clock** | How is an order worked once it is decided? | A patient entry, worked over seconds (§5) |

The decision clock stays on the calendar throughout. Funding is paid every eight hours, risk limits and reports run by the day, and results must be comparable across strategies; an hourly decision keeps all of this simple. It also makes every test in this lecture fair: when the decision times are fixed, a change in the result can only come from the information the rule uses or from the way it trades, not from the moments it happens to decide.

**How the clocks communicate.** The clocks share one thing: time. Every trade on the tape carries an exchange timestamp to the millisecond, so every dollar bar carries one too, the moment its last trade happened. On one ordinary day, the two clocks look like this:

![Three clocks on one day: hourly closes and dollar-bar ends on 12 March 2024, and the age of the latest finished dollar bar at each hourly close](figures/16_01_three_clocks.png)
<sub><b>How to read the figure.</b> <b>Black line:</b> the price, from one-minute closes. <b>Blue dashes along the top of each panel:</b> each marks the moment a dollar bar finished, when another fixed amount of dollars, about a 48th of a typical day's trading, had changed hands (the information clock). <b>Columns:</b> how many dollar bars finished in each hour; the dotted line is an average day's two an hour. <b>Orange lines (lower panels):</b> the hourly closes, at which the rule decides (the decision clock). <b>Shaded bands (lower panels):</b> from the last dollar bar finished before an hourly close to that close; the width written above each is how old the newest dollar-bar information is when the rule decides.</sub>

Each dash marks the moment a dollar bar finished, and the columns count them hour by hour. Dollar bars are sparse at night, one an hour or fewer, and bunch when the market is busy: on this day 86 of them, against 48 on an average day, 15 in the single hour of the afternoon sell-off. The hourly closes do not move. In the lower panels, the shaded band runs from the last finished dollar bar to each hourly close: it is how old the information is that the rule can read, an hour at night, a few minutes in the sell-off.

A value computed on dollar bars, such as a moving average or a volatility, is therefore a staircase in clock time: it steps when a bar finishes and stays flat until the next one. An hourly rule reads that staircase at each of its closes:

![How an hourly rule reads a dollar-bar value: the trend measure on dollar bars as a staircase, read at each hourly close](figures/16_02_reading_another_clock.png)
<sub><b>How to read the figure.</b> <b>Blue staircase:</b> the trend measure computed on dollar bars (fast span 48 bars, about a day); above 0 the price has been rising. <b>Blue dashes:</b> a dollar bar finishes and the value steps; between dashes it stays flat. <b>Orange lines:</b> the hourly closes. <b>Orange diamonds:</b> the value the rule reads at each close, the height of the step at that moment. <b>Grey text at the top:</b> how many dollar bars finished during each hour.</sub>

At 17:00 the rule reads the value of the bar that ended at 16:48:42, eleven minutes earlier; at 03:00 it reads a bar that is an hour old, because nothing worth a bar happened during the night. Three rules make this exact:

| Step | What to do | Why |
|---|---|---|
| 1. Measure on the other clock | Compute the value on dollar bars, bar by bar | The measurement uses the clock it was designed for |
| 2. Read it as of the decision | At each hourly close, take the value of the last bar that has **finished**; in code, an "as-of join" on timestamps | A bar still forming contains trades after the decision: reading it would use the future |
| 3. Convert the units if needed | A trend measure has no units; a risk per dollar bar becomes a risk per hour by multiplying by the number of bars expected in the hour | The decision is about the next hour, not the next bar |

There is a second way to bring dollar bars into an hourly rule: to summarise the bars that finished during the hour instead of reading the last one. Their number measures the hour's activity, the sum of their squared returns its risk; §4 uses both.

**Data.** The tape of Lecture 12, the BTCUSDT perpetual on Binance from October 2021 to September 2026, as hourly closes and as the dollar bars of Lecture 13 (about 48 a day, thresholds from the past 28 days). Costs come from Lecture 15: 5 bp for a market order and 2 bp for a resting one, a regular account's fees, plus the measured spread; funding is charged at every eight-hour settlement. Every choice of speed or setting is made on 2021–2024; 2025–2026 is shown as well, and played no part in any choice.

## 2. The rule on BTCUSDT

The rule is the one Part II built and the capstone of Lecture 11 carried into its final portfolio: EWMAC, the gap between a fast and a slow exponentially weighted moving average of the price, divided by the volatility of price changes, so that a trend is measured in units of its own noise. Its parts, and what changes on bitcoin:

| Part | As in Part II | On BTCUSDT |
|---|---|---|
| Signal | Fast average minus slow average, the slow span four times the fast, divided by the volatility of price changes | The same, on hourly closes |
| Scale | The signal divided by its own average absolute size so far, so that 1 is a typical signal | The same; no cap on large signals, so that the rule's output is not trimmed by hand |
| Position | Signal × target volatility ÷ the market's volatility, here a 10% annual target and the past 36 days' volatility of hourly returns | The same |
| Trading | Change the position when the target has moved | Only when the target is more than 10% of its average size away from the position held: a buffer that keeps the rule from paying fees for small adjustments |
| Costs | A cost per unit traded | The 5 bp fee of a market order and the measured half-spread (Lecture 15, §5), and funding at every eight-hour settlement on the position held |

Without a cap, large signals give large positions, and the rule's realised volatility comes out near 19% a year rather than the 10% it targets. The comparisons below are in Sharpe ratios, which the scale of the positions does not change.

**Which speeds?** Part II found a plateau of fast spans from about 16 to 128 days on futures, and found that faster rules failed. Bitcoin is a different market, so the speed is chosen again, on 2021–2024 only: the same rule, fast spans from 3 hours to 3 weeks, each about 1.6 times the last, so that the curve is spaced evenly in what matters: 1 to 2 hours doubles the speed, 13 to 14 days hardly changes it.

![The Sharpe ratio after all costs by speed, 2021-2024 and 2025-2026, and what trading costs a year](figures/16_03_speed_curve.png)

The curve has a plateau, and it lies far faster than on futures: fast spans of **one to three days**, with a Sharpe ratio after all costs of 1.0 to 1.2 in 2021–2024 and about 0.5 in 2025–2026, which played no part in the choice. Faster than half a day, costs eat the rule: at a fast span of three hours it trades its capital about 580 times a year and pays 29% of it in fees. Slower than a week, it fades, and at three weeks it loses money in 2025–2026. The gap between the curve before and after costs shows where costs matter: at the fast end. On this market and sample, bitcoin's tradable trends last days, not months; whether that holds on other cryptocurrencies, or in other years, is an open question.

**How often to look?** The speed is how much history the rule weighs; the candle is how often it looks. A fast span of one day is about 24 hourly candles, or 288 five-minute candles, or a single daily one. The same speeds, measured in hours of history, on candles from five minutes to a day:

![The Sharpe ratio after all costs on candles of five minutes to one day, for speeds of one, two and four days](figures/16_04_candle_size.png)

From five minutes to four hours, the candle hardly matters: in 2021–2024 the Sharpe ratios lie within about 0.15 of each other at every speed. In 2025–2026 finer candles do a little better, by amounts that two years of data cannot tell from chance. Once a day is too seldom: a rule that sees only the daily close reacts a day late to trends that last a few days, and loses a third of its Sharpe ratio or more. Looking once an hour is therefore enough, and simpler to run than looking every five minutes.

**The rule for the rest of the lecture.** Hourly candles; the three speeds of the plateau, fast spans of 1, 2 and 3 days, blended with equal weights, following the rule of Part II: drop the speeds that do not work and keep all those that do, rather than the single best. The blend has a Sharpe ratio after all costs of 1.14 in 2021–2024 and 0.52 in 2025–2026; it pays 2.0% of its capital a year in fees and 1.4% in funding, and turns its capital over about 40 times a year. Every section that follows changes one thing in this rule, and measures what it adds.
