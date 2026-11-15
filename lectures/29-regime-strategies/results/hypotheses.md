# Lecture 29: regime information as a strategy — plan fixed before any result

Fixed 2026-11-15, before any return of the strategies below was computed. Every later change is dated below with its reason. Agreed with the user on 2026-11-15.

## Why this lecture follows Lecture 28 (the opening of the lecture)

Lecture 28 asked the regimes **when trend works** (a switch) and, on our data, they could not say better than chance. A switch could not have done more: switched off, trend's capital is idle. This lecture asks the same regime series a different question, **where prices go**, by turning them into strategies of their own next to trend, and judges each by what it adds, above all in the regimes where trend loses (the user's question: when trend is weak in a quadrant, is there a strategy that does better there?). The regime series are reused as built in Lecture 28; the switches are not tested again.

## The rule (one sentence, our proposal)

**Hold trend and the regime strategies side by side at equal risk, and judge each strategy by what it adds to trend, above all in the regimes where trend loses.**

## Samples and machinery (as Lectures 27-28)

- **Trend:** Lecture 27's baseline, always in. ETFs out of sample 2013-2026; capstone futures 2006 to 2022-11-18 (Lecture 28's end date).
- **Every strategy** uses the same machinery as trend: each market's position scaled to 10% volatility (six-month), reached a tenth of the way each day, 5 bp per trade; markets at equal risk within a class, classes at equal risk, the strategy's total scaled each year to 10% on its past three years. Every signal known the day before.

## Three strategies

| Strategy | Positions | Markets | Literature |
|---|---|---|---|
| **Carry** | Long where holding pays, short where it costs: the sign of the annualised gap between the front contract and a later one (financial futures: the next contract; commodities: the contract about twelve months after the front, which removes the seasons, as Lecture 28's exercise 3 suggested); bond funds: the yield of the matching maturity minus the bill rate (VFITX: 5-year, VUSTX: 20-year, FRED) | Capstone futures, all classes (the curve of currency and equity-index futures carries the rate gap and the dividend yield; checked 2026-11-15: euro futures gap −2.1% in 2006, +1.7% in 2008; S&P 500 −3.4% in 2006, +1.9% in 2012) | Koijen, Moskowitz, Pedersen and Vrugt (2018) |
| **Economic trend** | Lecture 28's real-time growth and inflation directions (sign of the 12-month change, data as first published): bonds long when growth and inflation fall, score −(g + i)/2; equities and credit (g − i)/2; commodities (g + i)/2, with g, i = +1 rising, −1 falling. Currencies: not traded (needs foreign macro data) | ETFs and capstone futures | Brooks (2017), "A half century of macro momentum" (AQR) |
| **Fed announcement** | Long US equities (SPY; S&P 500 futures) from the close before each scheduled FOMC announcement to the close of the announcement day, flat otherwise; size one unit of notional (no leverage). Scheduled meetings from the Federal Reserve's calendars (free); conference calls and unscheduled meetings excluded. A daily version of the announcement-day premium; the pre-announcement drift itself is intraday | ETFs and capstone futures | Lucca and Moench (2015); Savor and Wilson (2013); reported weaker after 2015 |

**Carry on the ETFs** is not tested: there are no free curve data for ETFs. Marked open, with that reason.

**The Fed strategy is not scaled to equal average risk.** It is invested about eight days a year; at equal average risk it would need several times leverage on those days. It is added at one unit of notional, and the lecture shows this as the example of **average against active risk budgets** (a strategy that is rarely on cannot carry the same average risk as one that is always on without large leverage when it is on).

## Combination and its one rival (the idle budget)

- **Rule:** trend, carry and economic trend at equal risk (futures: three strategies; ETFs: trend and economic trend), total scaled to 10%; the Fed strategy added at one unit of notional on its days.
- **Rival:** trend switched off by Lecture 28's growth filter (as fixed there); while trend is off, its risk budget passes to the other strategies, so the total risk target stays the same. Changes a tenth of the way each day.

## Measures (the same for every strategy)

1. Sharpe ratio after costs on its own; correlation with trend.
2. The combination: Sharpe ratio, return a year at 10% volatility, worst drawdown, return in trend's 12 worst months.
3. **By quadrant** (Lecture 28's definitions, known the day before): volatility and correlation (level above or below its average to date × rising or falling over three months) and growth × inflation (first published): each strategy's Sharpe ratio against trend's.
4. **Luck baseline:** 1,000 random strategies on the same markets, each market's sign switching at random with the same average holding period as the real strategy (a two-state Markov chain), the same machinery; each added to trend in the same way. The share of them whose combination with trend the real strategy's combination beats on Sharpe ratio.

## Trend's weak quadrants (fixed now, from Lecture 28's results, before any strategy return is seen)

The two quadrants with trend's lowest Sharpe ratio, per variable and dataset:

| Variable | ETFs 2013-2026 | Futures 2006-2022 |
|---|---|---|
| Volatility | above, rising (−0.20); below, falling (0.24) | below, rising (0.28); below, falling (0.32) |
| Correlation | above, rising (−0.77); below, falling (0.27) | above, falling (0.22); below, falling (0.36) |
| Growth × inflation | growth down, inflation up (0.12); growth up, inflation down (0.26) | growth down, inflation down (0.06); growth up, inflation down (0.44) |

They differ between datasets (Lecture 28 §6: such patterns are period-specific); each dataset is judged on its own.

## Verdict

- **A strategy adds to trend** if its combination with trend beats at least 90% of the combinations with random strategies on each dataset where it is tested, and the p-values pass Benjamini-Hochberg at 10% across the strategy tests (futures: carry, economic trend, Fed; ETFs: economic trend, Fed: five tests).
- **A strategy earns where trend does not** (descriptive, with 90% bands from a block bootstrap over months): its Sharpe ratio in a weak quadrant of trend is above trend's there.

## Three expectations

1. **Carry and economic trend earn on their own after costs; the Fed strategy weakly at best** (reported to have faded after 2015).
2. **In trend's weak quadrants, at least one strategy beats trend on both datasets**, for each of the three variables.
3. **Combining beats trend alone, and the idle-budget rival does no better than fixed budgets**, because Lecture 28 found the switch's timing no better than chance.

## Kept for later

- Lecture 30: allocation methods across trend and these strategies (risk parity, hierarchical, budgets from risk only).
- Exercises: cross-sectional carry (rank within class); economic trend with foreign macro data for currencies; the intraday pre-announcement drift; an equity dividend-yield carry for ETFs.
