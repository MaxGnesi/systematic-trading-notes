# Lecture 9: Comparing Trend Systems

*Systematic Trading: Lecture Notes (MSc) · Oct 18, 2026 · Max Gnesi*

Two trend systems with different Sharpe ratios may not differ at all: one may simply trade at a different speed, the gap may be noise, or the better one may have been picked from many tries. This lecture builds a fair way to compare trend systems, in four questions: compared at what speed, does a system add anything, is the difference real, and will it last?

*Draft. The structure and methods are fixed; the measurements on the 16 ETFs of Lectures 5 and 6, the notebook and the charts follow. The lecture's position in Part II may change.*

## 1. The question of this lecture

Lecture 6 compared five trend families across their parameters and found that speed dominates: within each family the Sharpe ratio ranged from about −0.2 to 0.55 as the rule slowed down, while at equal speed the families lay within 0.1–0.3 of each other. Comparing one setting of one rule with one setting of another is therefore close to meaningless. This lecture asks how to compare trend systems properly.

| Question | Why it matters | Sections |
|---|---|---|
| Compared at what speed? | A slow rule and a fast rule differ by speed before they differ by idea | §2 |
| Does a system add anything? | The useful question is not which system is better but whether a second one improves the first | §3 |
| Is the difference real? | Strategy returns are noisy; a gap of 0.2 in Sharpe ratio over 25 years may be chance | §4 |
| Will it last? | The best point on a curve is the one most likely to disappoint | §5 |

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

## 4. Is the difference real?

Strategy returns are noisy, fat-tailed and serially dependent. Before reading a gap between two curves as a difference between two ideas, test it.

| Method | Idea | What it answers |
|---|---|---|
| Block-bootstrap bands | Resample blocks of strategy returns, as in Lecture 3, §10, and redraw each curve many times | Whether the gaps between curves exceed what noise alone produces |
| Test of a Sharpe-ratio difference | Jobson and Korkie (1981), corrected by Memmel (2003), assumes normal returns; Ledoit and Wolf (2008) use a bootstrap that allows fat tails and dependence | Whether two specific systems differ |
| Tests across the whole grid | White's (2000) reality check; Hansen's (2005) test for superior predictive ability; the stepwise procedure of Romano and Wolf (2005) | Whether any system in the grid truly beats a benchmark, given everything that was tried |
| Probability of backtest overfitting (Bailey, Borwein, López de Prado and Zhu, 2017) | Split the history many ways; record how often the best system in one half ranks poorly in the other | How much choosing the best point overfits |

*To measure:* bootstrap bands on the curves of Lecture 6; the Ledoit–Wolf test for the closest pairs of families at equal speed; the probability of backtest overfitting for choosing the best parameter in each family.

## 5. Will it last? Robustness instead of the best point

The best point on a curve combines skill with luck, and the luck does not repeat. Three habits reduce the dependence on it.

| Method | Idea | What it protects against |
|---|---|---|
| Judge the whole curve | Compare families by their median or average across parameters, not by their peak; prefer a flat plateau to a sharp peak | Selecting the lucky parameter; needs no selection, so it cannot be overfitted |
| Walk-forward and cross-market selection | Choose parameters on past data, or on half of the assets, and test on the rest | In-sample selection; results are out of sample by construction |
| Several measures at once | Sharpe ratio, skewness, drawdown, behaviour in crises, cost; keep the systems that no other beats on every measure | A single number hiding the payoff profile, which Lecture 6 showed depends on design |

*To measure:* median and peak Sharpe ratio per family; walk-forward parameter choice against the fixed best; the systems that survive on several measures at once.

## 6. A procedure, simplest first

1. **Sweep the parameters** of every family and plot performance against a common measure of speed (§2).
2. **Judge each family by its whole curve**, its median across parameters, not its peak (§5).
3. **Put bootstrap bands on the curves** before reading any gap as real (§4).
4. **Compute the breakeven cost** of each family across its parameters (§3).
5. **Ask what each family adds** to the others at equal speed, with correlations and spanning regressions (§3).
6. **Only then test formally**, pairwise with Ledoit and Wolf, and across the grid with Romano and Wolf or the probability of backtest overfitting (§4).

**Watch out for** declaring a winner from a single backtest. Speed, noise and selection each produce differences between systems that are not differences between ideas; the procedure above removes them one at a time.

## References

- Bailey, D., Borwein, J., López de Prado, M. and Zhu, Q. (2017). The probability of backtest overfitting. *Journal of Computational Finance* 20(4). — how much selecting the best backtest overfits (§4).
- Hansen, P.R. (2005). A test for superior predictive ability. *Journal of Business and Economic Statistics* 23, 365–380. — testing the best of many models (§4).
- Huberman, G. and Kandel, S. (1987). Mean-variance spanning. *Journal of Finance* 42(4), 873–888. — whether one set of assets adds to another (§3).
- Jobson, J.D. and Korkie, B. (1981). Performance hypothesis testing with the Sharpe and Treynor measures. *Journal of Finance* 36(4), 889–908. — the classical test of a Sharpe-ratio difference (§4).
- Ledoit, O. and Wolf, M. (2008). Robust performance hypothesis testing with the Sharpe ratio. *Journal of Empirical Finance* 15(5), 850–859. — a bootstrap test robust to fat tails and dependence (§4).
- Levine, A. and Pedersen, L.H. (2016). Which trend is your friend? *Financial Analysts Journal* 72(3), 51–66. — trend signatures (§2).
- Memmel, C. (2003). Performance hypothesis testing with the Sharpe ratio. *Finance Letters* 1(1), 21–23. — correction of the Jobson–Korkie test (§4).
- Romano, J. and Wolf, M. (2005). Stepwise multiple testing as formalized data snooping. *Econometrica* 73(4), 1237–1282. — controlling false discoveries across many strategies (§4).
- White, H. (2000). A reality check for data snooping. *Econometrica* 68(5), 1097–1126. — testing the best of many rules (§4).
