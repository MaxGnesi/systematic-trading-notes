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

Dollar bars are sparse at night, one an hour or fewer, and bunch when the market is busy: on this day 86 of them, against 48 on an average day, most in the afternoon sell-off. The hourly closes do not move.

A value computed on dollar bars, such as a moving average or a volatility, is therefore a staircase in clock time: it steps when a bar finishes and stays flat until the next one. An hourly rule reads that staircase at each of its closes:

![How an hourly rule reads a dollar-bar value: the trend measure on dollar bars as a staircase, read at each hourly close](figures/16_02_reading_another_clock.png)

At 17:00 the rule reads the value of the bar that ended at 16:48:42, eleven minutes earlier; at 03:00 it reads a bar that is an hour old, because nothing worth a bar happened during the night. Three rules make this exact:

| Step | What to do | Why |
|---|---|---|
| 1. Measure on the other clock | Compute the value on dollar bars, bar by bar | The measurement uses the clock it was designed for |
| 2. Read it as of the decision | At each hourly close, take the value of the last bar that has **finished**; in code, an "as-of join" on timestamps | A bar still forming contains trades after the decision: reading it would use the future |
| 3. Convert the units if needed | A trend measure has no units; a risk per dollar bar becomes a risk per hour by multiplying by the number of bars expected in the hour | The decision is about the next hour, not the next bar |

There is a second way to bring dollar bars into an hourly rule: to summarise the bars that finished during the hour instead of reading the last one. Their number measures the hour's activity, the sum of their squared returns its risk; §4 uses both.

**Data.** The tape of Lecture 12, the BTCUSDT perpetual on Binance from October 2021 to September 2026, as hourly closes and as the dollar bars of Lecture 13 (about 48 a day, thresholds from the past 28 days). Costs come from Lecture 15: 5 bp for a market order and 2 bp for a resting one, a regular account's fees, plus the measured spread; funding is charged at every eight-hour settlement. Every choice of speed or setting is made on 2021–2024; 2025–2026 is shown as well, and played no part in any choice.
