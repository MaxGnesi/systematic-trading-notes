# Lecture 7: Comparing Trend Systems

*Systematic Trading: Lecture Notes (MSc) · Oct 18, 2026 · Max Gnesi*

Two trend systems with different Sharpe ratios may not differ at all: one may simply trade at a different speed, the gap may be noise, or the better one may have been picked from many tries. This lecture builds a fair way to compare trend systems, in five questions: compared at what speed, does a system add anything, what do its trades show, is the difference real, and will it last?

*Draft. The structure and methods are fixed; the measurements on the 16 ETFs of Lectures 5 and 6, the notebook and the charts follow. The lecture's position in Part II may change.*

## 1. The question of this lecture

Lecture 6 compared five trend families across their parameters and found that speed dominates: within each family the Sharpe ratio ranged from about −0.2 to 0.55 as the rule slowed down, while at equal speed the families lay within 0.1–0.3 of each other. Comparing one setting of one rule with one setting of another is therefore close to meaningless. This lecture asks how to compare trend systems properly.

| Question | Why it matters | Sections |
|---|---|---|
| Compared at what speed? | A slow rule and a fast rule differ by speed before they differ by idea | §2 |
| Does a system add anything? | The useful question is not which system is better but whether a second one improves the first | §3 |
| What do the trades show? | Two systems with the same return series can earn it from different trades, on different sides, with different time in the market | §4 |
| Is the difference real? | Strategy returns are noisy; a gap of 0.2 in Sharpe ratio over 25 years may be chance | §5 |
| Will it last? | The best point on a curve is the one most likely to disappoint | §6 |

## 2. A fair axis for speed

To compare families at equal speed, speed must be measured the same way for all of them. Three measures are in use, and each sees something different.

| Measure | What it counts | Sees | Misses |
|---|---|---|---|
| Changes of direction per year | How often the position switches between long, flat and short | Simple; matches how practitioners count trades | Unfair to continuous rules, which trade between changes of sign, and to rules that pass through flat |
| Turnover or holding period | Notional traded per year, or the average time a position is held | The actual trading, and so the cost | Includes the trading created by volatility targeting, which is the same for every family |
| Trend signature (Levine and Pedersen, 2016) | The weights a rule puts on past returns at each horizon | What the rule looks at, independently of how its trades are counted | Defined exactly only for linear rules; breakouts and stops need an approximation |

*To measure:* the curves of Lecture 6, chart E.2, redrawn against each of the three axes; how much the gaps between families change with the axis.

## 3. Does a system add anything?

A second system is worth adding if it improves the first, not if it beats it. Two systems with similar Sharpe ratios and low correlation are both worth keeping; a system with a higher Sharpe ratio that is almost a copy of the first adds little.

| Method | Idea | What it answers |
|---|---|---|
| Correlation at equal speed | Correlate the returns of two families matched on speed | How different they really are, once speed is removed |
| Spanning or alpha regression (Huberman and Kandel, 1987) | Regress system B's returns on system A's; the intercept is what B earns beyond A | Whether B adds to A, in return per unit of risk |
| Breakeven cost | The cost per unit traded at which a system's Sharpe ratio falls to zero | Edge and turnover combined in one number |

*To measure:* correlations and alphas between the five families at matched speeds; breakeven costs across each family's parameters.

## 4. Beyond the return series: trades, sides and time in the market

A daily return series hides how a system earns. Three views open it up.

### 4.1 Trades

| Measure | What it shows |
|---|---|
| Number of trades and average holding period | Speed in the units traders use |
| Win rate and average win against average loss | Whether the edge comes from winning often or from winning big |
| Distribution of trade returns: skewness, largest trades | The shape of the payoff, trade by trade |
| Share of profit from the largest tenth of trades | Concentration: Lecture 5 found the timing profit in a tenth of the months; a system that depends on a few trades is fragile to missing them |

### 4.2 The long side and the short side

Compare each system's long and short trades separately. Lecture 5 found that the long side collects drift and the short side earns only in persistent declines; Lecture 6 that the short side carries the crisis protection. Two systems with the same Sharpe ratio can earn it on different sides, and so behave differently in a crash.

### 4.3 Systems that are not always in the market

Systems that can be flat, such as long-or-flat designs or breakouts waiting for a break, are invested only part of the time. The temptation is to drop the idle periods and compute the Sharpe ratio on the active ones only. That number is real but answers a narrow question, and it can point the wrong way when capital has to be allocated.

If a system is in the market a fraction $`p`$ of the time, earns excess return $`\mu`$ with volatility $`\sigma`$ while invested, and its idle capital earns the cash rate, then over the whole period:

```math
\text{Sharpe ratio} \;=\; \frac{p\,\mu}{\sqrt{p}\,\sigma} \;=\; \text{Sharpe ratio while invested} \times \sqrt{p}, \qquad \text{excess return} \;=\; p\,\mu
```

| | System A: in the market 30% of the time | System B: always in the market |
|---|---|---|
| Sharpe ratio while invested | 1.00 | 0.60 |
| Sharpe ratio over the whole period | 1.00 × √0.3 = 0.55 | 0.60 |
| Excess return per unit of capital, if both run at 10% volatility while invested | 0.3 × 10% = 3.0% | 6.0% |

A looks better while it trades; over the whole period it has the lower Sharpe ratio and half the return per unit of capital. Which system deserves the capital depends on what the idle capital can do:

| Situation | What matters | Which system |
|---|---|---|
| Idle capital can be redeployed, to other strategies or by scaling A up when it trades | Sharpe ratio while invested, and how well A's active periods fit with the rest | A can be the better component |
| Capital is committed and leverage is limited | Return per unit of capital and Sharpe ratio over the whole period | B, despite its lower Sharpe ratio while invested |
| Leverage is available without limit | Sharpe ratio over the whole period, since any Sharpe ratio can be scaled to any return | B here, unless A's idle capital is reused |

There is no single right number. Report time in the market, the Sharpe ratio both while invested and over the whole period, and the return per unit of capital, and decide with the capital and leverage constraints in view. Capital that one system leaves idle can be used by another, which turns the comparison into a portfolio question (Lecture 10); how much leverage to run is a sizing question (Lecture 9).

*To measure:* trade statistics and the long and short split for each family; time in the market and return while invested for the long-or-flat and breakout designs.

## 5. Is the difference real?

Strategy returns are noisy, fat-tailed and serially dependent. Before reading a gap between two curves as a difference between two ideas, test it.

| Method | Idea | What it answers |
|---|---|---|
| Block-bootstrap bands | Resample blocks of strategy returns, as in Lecture 3, §10, and redraw each curve many times | Whether the gaps between curves exceed what noise alone produces |
| Test of a Sharpe-ratio difference | Jobson and Korkie (1981), corrected by Memmel (2003), assumes normal returns; Ledoit and Wolf (2008) use a bootstrap that allows fat tails and dependence | Whether two specific systems differ |
| Tests across the whole grid | White's (2000) reality check; Hansen's (2005) test for superior predictive ability; the stepwise procedure of Romano and Wolf (2005) | Whether any system in the grid truly beats a benchmark, given everything that was tried |
| Probability of backtest overfitting (Bailey, Borwein, López de Prado and Zhu, 2017) | Split the history into many combinations of sub-periods; record how often the best system in one combination ranks poorly in its complement | How much choosing the best point overfits |

**Splitting history is not neutral.** Different periods are different macro regimes: a system chosen in a decade of falling rates and tested in a decade of zero rates is compared across regimes, not on skill. Three things reduce the problem. Using many combinations of sub-periods, as the probability of backtest overfitting does, mixes regimes on both sides of each split. Splitting the **assets** instead of the history, choosing on half the markets and testing on the other half over the same period, holds the regime fixed. And splitting by regime explicitly, for example zero-rate months against the rest (Lecture 5, §3.5), turns the problem into a question.

*To measure:* bootstrap bands on the curves of Lecture 6; the Ledoit–Wolf test for the closest pairs of families at equal speed; the probability of backtest overfitting for choosing the best parameter in each family.

## 6. Will it last? Robustness instead of the best point

The best point on a curve combines skill with luck, and the luck does not repeat. Three habits reduce the dependence on it.

| Method | Idea | What it protects against |
|---|---|---|
| Judge the whole curve | Compare families by their median or average across parameters, not by their peak; prefer a flat plateau to a sharp peak | Selecting the lucky parameter; needs no selection, so it cannot be overfitted |
| Walk-forward and cross-market selection | Choose parameters on past data, or on half of the assets, and test on the rest | In-sample selection; results are out of sample by construction |
| Several measures at once | Sharpe ratio, skewness, drawdown, behaviour in crises, cost; keep the systems that no other beats on every measure | A single number hiding the payoff profile, which Lecture 6 showed depends on design |

*To measure:* median and peak Sharpe ratio per family; walk-forward parameter choice against the fixed best; the systems that survive on several measures at once.

## 7. A procedure, simplest first

1. **Sweep the parameters** of every family and plot performance against a common measure of speed (§2).
2. **Judge each family by its whole curve**, its median across parameters, not its peak (§6).
3. **Look at the trades and the sides**: concentration of profits, long against short, time in the market (§4).
4. **Put bootstrap bands on the curves** before reading any gap as real (§5).
4. **Compute the breakeven cost** of each family across its parameters (§3).
5. **Ask what each family adds** to the others at equal speed, with correlations and spanning regressions (§3).
6. **Only then test formally**, pairwise with Ledoit and Wolf, and across the grid with Romano and Wolf or the probability of backtest overfitting (§5).

**Watch out for** declaring a winner from a single backtest. Speed, noise and selection each produce differences between systems that are not differences between ideas; the procedure above removes them one at a time.

## 8. The charts this lecture needs

Comparisons are understood visually before they are tested. Each question gets a chart designed to answer it at a glance.

| Question | Chart | What the reader should see |
|---|---|---|
| At what speed? (§2) | Performance against speed: one curve per family across its parameters, on each of the three speed axes | Whether the families separate or collapse onto one curve, and how much that depends on the axis |
| At what speed? (§2) | Trend signatures: the weight each rule puts on past returns at each horizon | Which horizons each rule actually uses |
| Does it add anything? (§3) | Heat map of correlations between families at matched speeds | Which families are near copies and which are different |
| Does it add anything? (§3) | Breakeven cost against speed, one curve per family | Where each family's edge is eaten by costs |
| What do the trades show? (§4) | Histogram of trade returns per family, with the largest tenth of trades marked | Whether profits rest on a few trades |
| What do the trades show? (§4) | Long-side and short-side contributions per system, side by side | Where each system earns |
| What do the trades show? (§4) | Sharpe ratio against time in the market | How much of a gap is exposure rather than skill |
| Is it real? (§5) | The performance curves with block-bootstrap bands | Whether the gaps between curves lie outside the noise |
| Is it real? (§5) | Rank of each parameter on half of the assets against its rank on the other half, over the same period | Whether the best choice stays good in markets it was not chosen on, with the regime held fixed |
| Will it last? (§6) | Median against peak performance per family, side by side | How much of each family's best result is selection |
| Will it last? (§6) | Scatter of Sharpe ratio against skewness or drawdown, one point per system, with the systems no other beats marked | The trade-offs a single number hides |

## References

- Bailey, D., Borwein, J., López de Prado, M. and Zhu, Q. (2017). The probability of backtest overfitting. *Journal of Computational Finance* 20(4). — how much selecting the best backtest overfits (§5).
- Hansen, P.R. (2005). A test for superior predictive ability. *Journal of Business and Economic Statistics* 23, 365–380. — testing the best of many models (§5).
- Huberman, G. and Kandel, S. (1987). Mean-variance spanning. *Journal of Finance* 42(4), 873–888. — whether one set of assets adds to another (§3).
- Jobson, J.D. and Korkie, B. (1981). Performance hypothesis testing with the Sharpe and Treynor measures. *Journal of Finance* 36(4), 889–908. — the classical test of a Sharpe-ratio difference (§5).
- Ledoit, O. and Wolf, M. (2008). Robust performance hypothesis testing with the Sharpe ratio. *Journal of Empirical Finance* 15(5), 850–859. — a bootstrap test robust to fat tails and dependence (§5).
- Levine, A. and Pedersen, L.H. (2016). Which trend is your friend? *Financial Analysts Journal* 72(3), 51–66. — trend signatures (§2).
- Memmel, C. (2003). Performance hypothesis testing with the Sharpe ratio. *Finance Letters* 1(1), 21–23. — correction of the Jobson–Korkie test (§5).
- Romano, J. and Wolf, M. (2005). Stepwise multiple testing as formalized data snooping. *Econometrica* 73(4), 1237–1282. — controlling false discoveries across many strategies (§5).
- White, H. (2000). A reality check for data snooping. *Econometrica* 68(5), 1097–1126. — testing the best of many rules (§5).
