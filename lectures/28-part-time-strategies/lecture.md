# Lecture 28: Part-Time Strategies

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 15, 2026 · Max Gnesi*

Lecture 27's baseline trend portfolio is always in the market. A **regime filter** turns it into a **part-time strategy**: it steps aside when the economy or the markets are in a state where trend is expected to fail. This lecture asks whether that works with information known on the day, and, before that, how a strategy that is out of the market part of the time should be compared with one that never is. Two families of regime variables are tested side by side: **macro** (growth, inflation, the Fed; monthly, published late, revised) and **market state** (volatility, correlation, turning points, the yield curve, the dollar; daily, never revised). The scale is the opposite of Part IV's: there a strategy saw millions of events a day and a test had thousands of independent trials; here a regime lasts months, and twenty years hold a handful of episodes. The plan was fixed before any result was computed, and every change made after seeing results is dated and labelled ([results/hypotheses.md](results/hypotheses.md)).

## 1. Regime information as a switch

The same regime information can be used in two ways.

| | As a switch (this lecture) | As a strategy (Lecture 29) |
|---|---|---|
| Question | When should trend be held? | Does the regime itself earn a return? |
| What the regime does | Turns an existing strategy on and off | Sets the positions of a new strategy next to trend |
| Result | A part-time version of trend | A second return stream, judged by what it adds to trend |
| Idle capital | Stays idle | Used by the second strategy |

The switch comes first because it is the natural first idea and continues Lecture 8, which tested filters on single markets; here the filter switches the whole portfolio. This lecture also builds the regime series (known the day before, macro data as first published) that Lecture 29 reuses without testing them again.

**The rule in one sentence** (our proposal). *Trade trend while the regime is moving; step aside while it stands still*, where for each variable the unfavourable state was fixed before any result (§3). Off means the whole portfolio's target position is zero; it is reached a tenth of the way each day, like every position since Lecture 26, and every change costs 5 bp.

The lecture's result fits in one chart.

![A part-time strategy against always-in](figures/28_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> x: the share of days a filter keeps the baseline trend portfolio on; y: the portfolio's Sharpe ratio after costs over all days, idle days included (they earn the cash rate, zero excess return). Left: ETFs, out of sample 2013-2026; right: capstone futures 2006-2022. Dots: one per filter at its fixed threshold (blue: macro; orange: market state; green: both families combined). Dotted line: always in. Dashed curve: what time in the market alone gives, the always-in Sharpe ratio times the square root of the share of days on (Lecture 7 §4.3). Grey bars: 1,000 random switches per filter with the same time in the market and the same spell lengths, from their median to their 95th percentile. Our calculation.</sub>

The dots lie around the dashed curve: most of what a filter does to the Sharpe ratio over all days is explained by the time it spends out of the market, not by when it is out. On the ETFs every filter is below always-in (0.49). On the futures (always-in 0.55), four come near it or above it (growth still 0.63, both composites agreeing 0.56, the yield curve still 0.56, volatility low 0.54), and growth beats 95% of its random switches there; the same filter beats 50% of them on the ETFs. Under the verdict fixed in advance (beat 90% of random switches on both datasets, Benjamini-Hochberg at 10% within each family), **no filter works** on our data. The lecture shows how this was measured and what the data say about why, so that readers can judge the evidence themselves.

| § | Topic | Question |
|---|---|---|
| 2 | Comparing part-time with always-in | Which numbers answer which question, and what does each hide? |
| 3 | The regime variables | What do macro and market-state variables measure, and what does data revised later do to them? |
| 4 | The scan | Does trend earn less on the days a regime stands still? |
| 5 | The filters against luck | Does switching on these regimes beat always-in and random switching? |
| 6 | Why | What drives the patterns that appear, and do they repeat on years not used to find them? |
| 7 | One class at a time | A worked example: commodity trend by the shape of the futures curve |

## 2. Comparing a part-time strategy with always-in

A part-time strategy and an always-in strategy do not use their capital the same way, so no single number compares them. Lecture 7 (§4.3) showed the basic arithmetic for a system in the market a share $`p`$ of the time:

```math
\text{Sharpe ratio, all days} \;\approx\; \text{Sharpe ratio while on} \times \sqrt{p}, \qquad \text{return per unit of capital} \;\approx\; p \times \text{return while on}.
```

This section builds on it for a portfolio switched by a regime: which questions to ask, in which order, and what each answer leaves out.

### 2.1 The bar a switch must clear

A filter that knew nothing would leave the Sharpe ratio while on unchanged and lower the Sharpe ratio over all days by the factor $`\sqrt{p}`$. To match always-in over all days, the strategy must earn a Sharpe ratio while on of at least the always-in Sharpe ratio divided by $`\sqrt{p}`$:

| Share of days on, $`p`$ | 90% | 75% | 60% | 50% |
|---|---|---|---|---|
| Sharpe ratio needed while on, as a multiple of always-in | 1.05 | 1.15 | 1.29 | 1.41 |
| For the ETF baseline (0.49) | 0.51 | 0.56 | 0.63 | 0.69 |

<sub><b>How to read the table.</b> Each column is a filter that keeps trend on for the given share of days. The middle row is $`1/\sqrt{p}`$: how much better than always-in the days kept must be for the part-time strategy to match always-in over all days. The bottom row applies it to the ETF baseline. A definition, from the formula above.</sub>

The bar rises quickly: a filter that is off half the time must pick days on which trend earns a Sharpe ratio 41% higher than its average. The random filters of the key chart show the bar in practice: their medians sit close to the dashed curve. For the growth filter of §2.3 (on 59% of days on the futures) the formula gives 0.55 × √0.59 = 0.42 and its random filters' median is 0.43; on the ETFs (on 54% of days) 0.36 against 0.33.

The formula is a guide, not an identity. Positions move a tenth of the way each day, so the portfolio is still partly invested in the first days of an off spell and not yet fully invested in the first days of an on spell; switching also costs. The **random filter** with the same time in the market, the same spell lengths and the same attachment (Lecture 8 §4.5) includes all of this, which is why it, not the formula, is the yardstick of the verdict.

### 2.2 Six questions, six numbers

| Question | Number | Label | What it can hide |
|---|---|---|---|
| Does the account do better? | Sharpe ratio over all days | Definition (Lecture 7) | Where the change comes from: being out alone lowers it by $`\sqrt{p}`$ |
| Is trend better on the days it is held? | Sharpe ratio while on | Definition (Lecture 7) | The idle capital: a high number can come with a low return |
| What does the account earn as it is run? | Excess return a year per unit of capital | Definition | Risk: a lower return at much lower risk can be the better strategy |
| What would it earn at the same risk? | Return and worst drawdown, scaled after the fact to the always-in volatility | Convention (comparison only) | That running it needs leverage on the days on, and that the scale uses the whole sample |
| Is the timing information or chance? | Share of random filters with the same time in the market that it beats | Lecture 8 §4.5 | Nothing on its own about size: a filter can beat luck and still lose to always-in |
| Does it add what always-in cannot give? | Alpha: the intercept of its returns regressed on always-in's, with its t-statistic | Definition (Lecture 8, step 4) | Few independent episodes: macro regimes give wide bands |

<sub><b>How to read the table.</b> One row per question a reader may ask of a part-time strategy, the number that answers it, whether that number is a definition or a convention, and what it leaves out. No row settles the comparison alone.</sub>

The order matters. The first two numbers describe the strategy; the next two say what it does to an account; the last two say whether the timing carries information. A filter can pass the first and fail the fifth: it then earns its higher Sharpe ratio from being out of the market at random times, which any coin would do.

### 2.3 One running example: the growth filter on the futures

The growth filter switches trend off while US industrial production growth is still: the size of the 12-month change in its year-on-year growth rate is in the bottom third of its history to date, on data as first published (§3). It is the filter that came closest to working, so it shows every number of §2.2 at once.

| | Always in | Growth filter (part-time) |
|---|---|---|
| Share of days on | 100% | 59% |
| Sharpe ratio while on | 0.55 | 0.72 |
| Sharpe ratio over all days | 0.55 | **0.63** |
| Volatility | 11.1% | 8.3% |
| Excess return a year, as run | **6.1%** | 5.3% |
| Excess return a year, scaled to 11.1% volatility (× 1.34) | 6.1% | 7.0% |
| Worst drawdown, as run / scaled to 11.1% | −21.8% | −12.5% / −16.5% |
| Random filters with the same time in the market: median, 95th percentile | | 0.43, 0.64 |
| Share of random filters beaten | | 95% |
| Alpha over always-in, a year (t-statistic) | | 1.7% (1.4) |
| The same filter on the ETFs: Sharpe ratio over all days, random filters beaten | 0.49 | 0.33, 50% |

<sub><b>How to read the table.</b> Capstone futures 2006-2022, after costs; excess returns over cash; idle days earn zero excess return. "Scaled" multiplies the part-time strategy's daily returns by the ratio of the two volatilities over the whole sample (1.34), a comparison, not a strategy that could have been run. The last row is the same filter on the ETFs, 2013-2026. Our calculation.</sub>

The example shows the trade-off a part-time strategy brings. Over all days its Sharpe ratio is higher than always-in's (0.63 against 0.55), its drawdowns smaller and it beats 95% of random filters; **yet it earns less**: 5.3% a year against 6.1%, because 41% of the time its capital is idle. It earns more only when scaled up to the same risk, which means running it with a third more leverage on the days it is on, or giving its idle budget to something else. On the ETFs the same rule beats half its random filters, no better than a coin.

### 2.4 What the comparison cannot settle

Which of the two deserves the capital depends on what the idle capital can do. Lecture 7 (§4.3) laid out the cases: with committed capital and limited leverage, return per unit of capital decides; with capital that can be moved, the Sharpe ratio while on and the fit with the rest of the portfolio decide. A portfolio switched by a regime makes the second case concrete: the idle budget can be given to another strategy that does well in the regimes where trend is off. That is the question of Lecture 29, which uses the same regimes as strategies.

This lecture reports all six numbers for every filter and keeps its own reading short and labelled.
