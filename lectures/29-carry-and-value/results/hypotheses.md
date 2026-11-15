# Lecture 29: carry and value next to trend — plan fixed before any result

Fixed 2026-11-15, before any return of the strategies below was computed. Agreed with the user on 2026-11-15. Every later change is dated below with its reason.

**Change of scope, 2026-11-15, before any result (user).** An earlier plan for this lecture (commit 2987465: economic trend, the Fed-announcement day and carry, built from Lecture 28's regime series) is replaced by this one. The user's reason: adding other strategies to trend, after AQR's cross-asset styles, is worth more to the course than further strategies made from the regimes. Economic trend and the Fed-announcement day become exercises. No return of either was computed.

## Why this lecture follows Lecture 28 (the opening of the lecture)

Lecture 28 tried to avoid trend's bad regimes by switching trend off, and on our data the switch could not do better than chance. Even a good switch could only take away: switched off, trend's capital is idle. The other answer to the same problem is to hold, next to trend, strategies that earn for different reasons and so tend to earn when trend does not. This needs no forecast of the regime. The two best-documented cross-asset candidates are **carry** and **value** (Asness, Moskowitz and Pedersen 2013; Koijen, Moskowitz, Pedersen and Vrugt 2018). Lecture 28's regimes stay, but as a lens: each strategy is shown in the quadrants where trend is weak.

## The rule (one sentence, our proposal)

**Hold trend, carry and value at equal risk, and judge carry and value by what each adds to trend.**

## Samples and machinery (as Lectures 27-28)

- **Trend:** Lecture 27's baseline, always in. ETFs out of sample 2013-2026; capstone futures 2006 to 2022-11-18 (Lecture 28's end date).
- **Every strategy** uses the same machinery as trend: each market's position scaled to 10% volatility (six-month), reached a tenth of the way each day, 5 bp per trade; classes at equal risk; the strategy's total scaled each year to 10% on its past three years. Every signal known the day before.

## Two strategies, in their simplest versions

| Strategy | Signal | Markets | Literature |
|---|---|---|---|
| **Carry** | What holding the position earns if prices do not move: the annualised log gap between the front contract and a later one, $`\ln(F_{\text{front}}/F_{\text{later}}) \times 365 / \text{days between them}`$. Financial futures: the next contract (currencies: foreign rate minus US rate; equity indices: dividend yield minus rate); commodities: the contract about twelve months after the front, which removes the seasons (Lecture 28, exercise 3). Bond funds (VFITX, VUSTX): the Treasury yield of the matching maturity minus the bill rate (FRED: 5-year and 30-year) | Capstone futures, all classes | Koijen, Moskowitz, Pedersen and Vrugt (2018), "Carry" |
| **Value** | Cheap against its own past: minus the log of today's price over its average 4.5 to 5.5 years ago, on the series we trade (the rolled futures; the ETFs' adjusted prices) | Capstone futures and ETFs | Asness, Moskowitz and Pedersen (2013), "Value and Momentum Everywhere" |

**Carry on the ETFs** is not tested: there are no free curve data for ETFs; a version from free yields and dividends is an exercise.

**Value on the series we trade.** AQR measures value on spot prices, book-to-market for equity indices and real exchange rates for currencies. These are not free for our markets. The rolled futures and the ETFs' adjusted prices include income, so our value signal mixes a little carry into the price; the simplest version is kept and the difference is checked against AQR's published factors (below).

## From signal to positions: the rule and its one rival

- **Rule (AQR's way): rank within each group.** Within each of AQR's four groups (equity indices, bonds, currencies, commodities; on the ETFs Lecture 25's classes), each market's weight is its rank minus the average rank, scaled so the longs and the shorts each carry half the group's risk: long the high carry or cheap markets, short the low carry or dear ones. Every group is market neutral by construction.
- **Rival (trend's way): each market's own sign.** Long where the signal is positive, short where it is negative, each market on its own.

**A weakness fixed now.** The futures groups are small: 2 equity indices, 3 currencies, 7 commodities, 2 bond funds. Ranking two markets means long one and short the other (the Nasdaq against the S&P 500; long against intermediate Treasuries). The rival shows whether this loses what the own-sign version earns. Own sign has the opposite weakness: a signal that never changes sign holds one side for ever (gold's carry is always negative), which is a static position, not a strategy.

## Measures (the same for every strategy)

1. Sharpe ratio after costs on its own; correlation with trend.
2. The combination: Sharpe ratio, return a year at 10% volatility, worst drawdown, return in trend's 12 worst months.
3. **By quadrant** (Lecture 28's definitions, known the day before): volatility and correlation (level above or below its average to date × rising or falling over three months) and growth × inflation (first published): each strategy's Sharpe ratio against trend's.
4. **Luck baseline:** 1,000 random strategies on the same markets, each market's signal replaced by a random one switching with the same average holding period as the real strategy (a two-state Markov chain), positions built by the same rule; each added to trend in the same way. The share of them whose combination with trend the real strategy's combination beats on Sharpe ratio.
5. **Check against AQR** (a check, not an input): the correlation of our value, per group, with AQR's published "Value and Momentum Everywhere" factor of the same group (monthly, free from the AQR Data Library; cited as AQR Capital Management, LLC; kept local, never committed). AQR's factors are paper portfolios before costs, on many more markets.

## Trend's weak quadrants (fixed now, from Lecture 28's results, before any strategy return is seen)

The two quadrants with trend's lowest Sharpe ratio, per variable and dataset:

| Variable | ETFs 2013-2026 | Futures 2006-2022 |
|---|---|---|
| Volatility | above, rising (−0.20); below, falling (0.24) | below, rising (0.28); below, falling (0.32) |
| Correlation | above, rising (−0.77); below, falling (0.27) | above, falling (0.22); below, falling (0.36) |
| Growth × inflation | growth down, inflation up (0.12); growth up, inflation down (0.26) | growth down, inflation down (0.06); growth up, inflation down (0.44) |

They differ between datasets (Lecture 28 §6: such patterns are period-specific); each dataset is judged on its own.

## Verdict

- **A strategy adds to trend** if its combination with trend beats at least 90% of the combinations with random strategies on each dataset where it is tested, and the p-values pass Benjamini-Hochberg at 10% across the three tests (futures: carry, value; ETFs: value). The rule's positions are judged; the rival is reported with the same measures.
- **A strategy earns where trend does not** (descriptive, with 90% bands from a block bootstrap over months): its Sharpe ratio in a weak quadrant of trend is above trend's there.

## Three expectations

1. **Value is negatively correlated with trend** on both datasets (the 5-year reversal is close to the opposite of a long trend; AQR report about −0.5 between value and momentum).
2. **Carry earns a positive Sharpe ratio after costs on its own** on the futures; value, on its own, earns little after 2007.
3. **Trend, carry and value together beat trend alone** on Sharpe ratio on both datasets (ETFs: trend and value), because the three are weakly or negatively correlated.

## Kept for later

- Lecture 30, the final portfolio: trend, carry and value assembled once on fixed rules; allocation from risk only, constraints and trading in brief; course close.
- Exercises: economic trend from Lecture 28's real-time growth and inflation directions (Brooks 2017); the Fed-announcement day (Lucca and Moench 2015); carry on the ETFs from free yields, dividends and foreign rates; value on spot prices; AQR's equity factors (low beta, quality minus junk) as a sleeve before costs.
