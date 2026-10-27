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

## 3. The information clock

Section 1 showed how an hourly rule can read a value computed on dollar bars. This section asks whether it should, for the trend measure itself. The test keeps everything else fixed: the rule decides at every hourly close, with the same sizing, the same market orders, the same buffer and the same funding; only the information it reads changes.

| Version | What the rule reads at each hourly close | What it isolates |
|---|---|---|
| **A: hourly closes** | The trend measure of §2, on hourly closes | The baseline |
| **B: dollar bars, average per bar** | The same measure computed on dollar bars, with spans counted in bars (48 a day on average), read from the last finished bar | The market's clock in full: averages that move fast when trading is busy and stand still when it is quiet |
| **C: dollar bars, average fading by time** | Dollar-bar prices, averaged with weights that fade with the time elapsed, not with the number of bars | Only the sampling: when the prices are taken, not how fast they are forgotten |

The distinction between B and C has a name in the literature on unevenly spaced data: an average whose weights depend on the number of samples changes when the sampling changes, one whose weights depend on elapsed time does not (Zumbach and Müller, 2001). C is the second kind.

![Sharpe ratio after all costs by speed, for the hourly rule reading its trend from hourly closes, from dollar bars with an average per bar, and from dollar bars with an average fading by time](figures/16_05_information_clock.png)
<sub><b>How to read the figure.</b> Each line is one version of the rule, by speed; the large markers on the right are the rule of §2, the three plateau speeds blended. <b>Blue (A):</b> the trend read from hourly closes. <b>Pink (B):</b> read from dollar bars, the average counted in bars. <b>Green (C):</b> read from dollar bars, the average fading with time. The shaded band is the plateau of §2. Left, 2021–2024; right, 2025–2026.</sub>

**C is A.** Dollar-bar prices averaged by elapsed time give almost the same signal as hourly closes (correlation 0.99) and the same Sharpe ratio: 1.13 against 1.14 in 2021–2024, 0.51 against 0.52 in 2025–2026, for the blend. Sampling the price when dollar bars finish adds no information that hourly closes lack. It does change one thing: the signal is updated less often in quiet hours, so the rule trades a little less, and its costs fall from 2.0% to 1.4% of capital a year.

**B is worse where the rule earns.** An average counted in dollar bars gives a different signal (correlation 0.84 to 0.98 with A), and on the plateau a worse one: for the blend, a Sharpe ratio of 0.99 against 1.14 in 2021–2024 and 0.41 against 0.52 in 2025–2026; at a speed of half a day, 0.37 against 0.96. For slow rules, off the plateau, B does slightly better in both periods (at three weeks, 0.78 against 0.65 and −0.01 against −0.14), but there the rule earns little anyway.

**Why.** An average counted in bars runs with the market's activity. In a burst, such as the afternoon of figure 16_01 with fifteen bars in an hour, it moves fifteen steps in an hour and follows the burst; at night it moves one step an hour, or none. Bursts of activity on BTCUSDT often reverse: flow in the direction of the trend partly comes back, and a sweep with the trend is taken back within the hour (Lecture 15, §2 and §3). A fast rule that follows bursts therefore buys late and sells late. A slow rule weighs so many bars that a burst moves it little, and freezing at night costs it nothing; that is why B stops hurting as the rule slows down.

**The same holds for a breakout.** A breakout rule, which trades on price levels rather than averages, was checked the same way, with its channel taken from hourly closes or from dollar bars: where it works, at channels of eight to thirteen days, dollar bars make it worse.

> **Box: López de Prado's bars, and what the tests found.** López de Prado (2018) recommends sampling the market by volume or dollars rather than by time, for the statistical properties of the resulting returns, and builds on such bars a pipeline that goes beyond a trend rule: a filter that picks out moments when the price has drifted far enough (the CUSUM filter), labels set by profit-taking, stop-loss and time limits, and a machine-learning model that decides which moments to act on. Two tests on bitcoin bear on it. On bitcoin and ether from 2018 to 2023, the pipeline earned after costs, but the part that helped was the CUSUM filter, not the volume or dollar bars (Grądzki, Wójcik and Lessmann, 2025). On the Binance bitcoin perpetual, dollar bars had the best statistics and no better predictions (Fayyaz et al., 2026, preprint). This section's result points the same way for a trend rule: what dollar bars measure well is not what makes a trend rule earn. Exercise 3 (§9.2) lets the rule decide only at CUSUM events.

**Our results and the literature.**

| The literature | Our result on BTCUSDT | |
|---|---|---|
| Returns are closer to normal when measured in trading time rather than clock time (Clark, 1973; Ané and Geman, 2000) | Lecture 13 found the same on dollar bars | in line |
| An average weighted by the number of samples depends on the sampling; one weighted by elapsed time does not (Zumbach and Müller, 2001) | The time-weighted version on dollar bars matches hourly closes; the per-bar version does not | in line |
| On the Binance bitcoin perpetual, the statistical quality of bars and their predictive power are largely unrelated (Fayyaz et al., 2026, preprint) | The trend measure gains nothing from dollar bars | in line |
| In a bitcoin trading pipeline, the CUSUM event filter helped, not the bar type (Grądzki, Wójcik and Lessmann, 2025) | — | not tested here; exercise 3 |
| — | A trend measure counted in dollar bars hurts fast trend rules, because it follows bursts that reverse | a result on this sample |

**Key message.** Information from another clock is easy to plug into an hourly rule: measure on the other clock, read the last finished bar at each decision. For a trend rule on BTCUSDT it adds nothing: sampled on dollar bars but averaged by time, it is the same as hourly closes, only a little cheaper to trade; averaged by bars, it follows bursts that reverse and hurts the rule where it earns. If a trend measure is taken from another clock, its average should fade with time, not with bars. The rule keeps reading hourly closes.

## 4. Risk

The rule sizes each position by the market's volatility over the past 36 days of hourly returns: the plainest estimate there is. Lecture 14 showed that measures built from inside the bar forecast the next bars' risk better, and Lecture 15 that risk clusters hour by hour. This section asks what that sharper knowledge of risk is worth to the trend rule, in two steps: what an hour's risk is made of, and what sizing by a forecast of it does.

**Two parts of risk.** An hour's risk, its realised variance from one-minute returns, is the product of two quantities: how much is traded in the hour, its **activity** (dollars traded, over a typical hour), and how far each dollar traded moves the price, its **risk per dollar**. The first is the number of dollar bars the hour will contain; the second is the risk each of them carries.

![The two parts of an hour's risk: activity and risk per dollar over one week, and how the hour-to-hour variation of risk splits between them](figures/16_06_two_parts_of_risk.png)
<sub><b>How to read the figure.</b> <b>Left:</b> one week, 11 to 17 March 2024, hour by hour, on a log scale where 1 is the usual level. <b>Blue:</b> activity, the dollars traded in the hour over a typical hour. <b>Pink:</b> risk per dollar, the hour's realised variance over its activity, relative to its usual level (the 28-day median). <b>Right:</b> over five years, the share of the hour-to-hour variation of log realised variance that comes from each part, and from the two moving together.</sub>

The two parts move separately, and each carries a large share of the variation: activity 42%, risk per dollar 38%, and the two together another 20%. Both can be forecast from what is known at the start of the hour, with the same kind of model, a regression on the last hour, the last day and the last week (Corsi, 2009), plus the same hour of the week and the scheduled releases:

| Forecast of the next hour, out of sample (2025–2026) | R² |
|---|---|
| Activity, from the last hour alone | 0.45 |
| Activity, full model with the hour of the week and the release hours | 0.58 |
| Risk per dollar, full model | 0.72 |
| Risk itself, directly | 0.70 |
| Risk as forecast activity × forecast risk per dollar | 0.70 |

*R² of the logarithm. A release hour carries about four times a typical hour's activity.*

Forecasting the two parts separately gives the same accuracy as forecasting risk directly. The split does not make the forecast sharper; it tells what kind of risky hour is coming. A busy hour, high activity at a normal risk per dollar, is largely foreseeable from the clock and the release calendar: a rule can plan around it. A thin hour, a high risk per dollar, is the state of liquidity that Lecture 15 found before cascades: a rule should hold less in it.

**Sizing by forecast risk.** The test replaces the 36-day volatility in the position size with a forecast of the coming risk, built from one-minute data, and compares four ways of measuring the risk the rule sizes by:

| Sizing by | What it uses |
|---|---|
| **Plain** | The past 36 days' volatility of hourly returns |
| **Next-day forecast, raw** | A forecast of the next 24 hours' realised variance, from the last hour, day and week, updated every hour |
| **Next-day forecast, smoothed** | The same forecast, averaged over a day, so that the position is not resized every hour |
| **Forecast over the holding period** | The same model, forecasting as far ahead as the rule typically holds: one day for the one-day speed, eight days for the eight-day speed |

![Sharpe ratio in both periods and the worst day, by speed, for four ways of measuring the risk the rule sizes by](figures/16_07_sizing.png)
<sub><b>How to read the figure.</b> Each line is one way of sizing, by speed; the large markers on the right of each panel are the rule's blend of the three plateau speeds. <b>Left and middle:</b> the Sharpe ratio after all costs, 2021–2024 and 2025–2026. <b>Right:</b> the worst day of 2021–2024, the largest loss over 24 hours, in units of the rule's typical daily move: closer to zero is milder. The shaded band is the plateau of §2.</sub>

For the rule's blend:

| Sizing by | Sharpe ratio, 2021–2024 / 2025–2026 | Worst day | Month-to-month spread of risk | Costs a year |
|---|---|---|---|---|
| Plain | **1.14 / 0.52** | −9.5 | 0.58 | 2.0% |
| Next-day forecast, raw | 0.92 / 0.21 | −6.8 | 0.45 | 5.8% |
| Next-day forecast, smoothed | **1.18** / 0.37 | **−6.5** | **0.46** | 1.8% |
| Forecast over the holding period | 1.11 / 0.38 | −7.4 | 0.48 | 1.7% |

*Worst day: the largest 24-hour loss in units of the rule's typical daily move. Spread of risk: the standard deviation of monthly realised volatility over its average.*

First, how good is each measure as a forecast of risk? Against the next 24 hours' realised variance, with each measure scaled to the same average level on 2021–2024:

| Forecast of the next 24 hours' risk | QLIKE, 2021–2024 / 2025–2026 (lower is better) |
|---|---|
| Plain: past 36 days | 0.38 / 0.32 |
| Next-day forecast, raw | **0.26 / 0.23** |
| Next-day forecast, smoothed over a day | 0.29 / 0.25 |
| The larger of raw and smoothed | 0.27 / 0.24 |

*QLIKE: the loss function for variance forecasts that is robust to noise in the measured variance (Patton, 2011; Lecture 14, §5.3).*

The forecast from one-minute data is a much better measure of the coming risk than the 36-day volatility, and smoothing it over a day gives up only part of the gain: out of sample it keeps about three quarters of the raw forecast's advantage. Then, what does each do in the rule? Three results stand out.

- **The raw forecast is a trap.** It moves from hour to hour, the position follows it, and the rule pays 5.8% of its capital a year in fees instead of 2.0%. Smoothed over a day, the forecast keeps most of its information and loses the churn. A middle way, sizing by the larger of the raw and the smoothed forecast, so that the position is cut at once when risk jumps and grows back slowly when it falls, brings much of the churn back (3.4% a year in fees) and makes the worst day no milder (−6.8): smoothing is the cheaper way to use the forecast.
- **A sharper forecast of risk steadies the rule.** Sized by the smoothed forecast, the rule's worst day is −6.5 typical daily moves instead of −9.5, and its risk varies less from month to month. That is what a forecast of risk is for, and it delivers it.
- **It does not raise the return per unit of risk.** The Sharpe ratio is about the same in 2021–2024 (1.18 against 1.14) and lower in 2025–2026 (0.37 against 0.52); at every speed in 2025–2026 the plain sizing does best. Forecasting over the holding period instead of the next day helps the slow rules, for which tomorrow's risk is the wrong number, but does not close the gap. One explanation, to be tested rather than assumed: bitcoin's large trends tend to come with rising volatility, and a rule that cuts its position as soon as risk rises holds less during the moves it lives on; the slow 36-day estimate reacts later and keeps more of them.

**Our results and the literature.**

| The literature | Our result on BTCUSDT | |
|---|---|---|
| Realised volatility is well forecast by its own last day, week and month, a simple model that mimics long memory (Corsi, 2009) | The same model forecasts an hour's risk with an R² of 0.70 out of sample, and each of its two parts as well | in line |
| Volatility targeting raises the Sharpe ratio only for risk assets such as equities and credit, negligibly for bonds, currencies and commodities, but makes extreme returns and left-tail events smaller in every asset class (Harvey, Hoyle, Korgaonkar, Rattray, Sargaison and Van Hemert, 2018) | Sizing by a sharper forecast makes the worst day milder (−6.5 against −9.5) without raising the Sharpe ratio | in line: bitcoin behaves like the second group |
| Scaling factor portfolios by their recent variance raised their Sharpe ratios (Moreira and Muir, 2017; for momentum, Barroso and Santa-Clara, 2015); later work finds the gains weaker out of sample and after costs | The sharper forecast does not raise the Sharpe ratio after costs | consistent with the later work |
| Much of the reported performance of time-series momentum comes from scaling its positions by volatility (Kim, Tse and Wald, 2016) | All versions here are scaled by volatility; scaling by a sharper measure adds nothing to the return | a different question: how well, not whether, to scale |
| — | An hour's risk splits about equally between activity and risk per dollar, each forecastable | a result on this sample |

**Key message.** An hour's risk on BTCUSDT has two parts of about equal weight: how much is traded, largely foreseeable from the clock and the release calendar, and how far each dollar moves the price, the state of liquidity. Forecasting them separately is no more accurate than forecasting risk directly, but tells what kind of hour is coming. Sizing a trend rule by a sharper forecast of risk, smoothed so that it does not churn, makes its worst days milder and its risk steadier, but does not raise its return per unit of risk; on this sample the plain, slow estimate did as well or better. The choice is between steadier risk and the last part of the return, and it is the investor's, not the data's. The capstone of Lecture 11 met the same trap from the other side: its floor on measured volatility kept positions from jumping when volatility briefly collapsed. The rule of the following sections keeps the plain sizing; §7 shows the alternative beside it.
