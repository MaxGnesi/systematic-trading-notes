# Lecture 27: putting the portfolio together (first planned as "when positions lose together") — plan fixed before any result

Fixed 2026-11-13, before any number of this lecture was computed. Every later change is dated below with its reason.

## The question

Lecture 25 removed the markets that duplicate each other; Lecture 26 chose the speeds. What is left is not "which markets are alike?" but **"when do our positions lose together?"** A trend portfolio's risk depends on today's positions: two markets that move together are a double bet when both are held long and a hedge when one is long and the other short. Does it pay to size the portfolio with that in mind, or is volatility alone enough?

This is step 2 of the workflow (Lecture 25, §1): weights from the risk of positioned returns only; profit and loss only to judge, out of sample.

## The rule (one sentence)

**Every market at equal risk within its asset class, every class at equal risk, and the whole scaled to 10% a year on its own past volatility: volatility only, no correlations** — exactly Lecture 26's out-of-sample portfolio, so it reproduces its Sharpe ratio of 0.49 first, as a check.

## Two rivals

| Rival | One sentence | What changes against the rule |
|---|---|---|
| **Position-aware risk** | Forecast the portfolio's risk each day from today's positions and the markets' correlations over the past three years, and scale the whole to 10% on that forecast | Only the total's scale: up when positions offset, down when they stack the same way |
| **Groups by trend phase** | Group the markets by how often their trend positions point the same way (concordance, Lecture 25 §4), into as many groups as there are classes (five), and give each group equal risk | Only the grouping: by behaviour instead of by label |

Fixed details, so that each rival is finite by construction rather than capped:

- **Correlations.** Weekly returns of the markets (not of the trend streams, which flip sign and give unstable estimates) over the past three years, shrunk towards the identity with the Ledoit-Wolf intensity. Shrinkage keeps the smallest eigenvalue away from zero, so a forecast never collapses to zero and the scale stays finite.
- **Positions.** Each market's signed risk position today: its trend position from Lecture 26's rule times its volatility over six months (Lecture 26 §3).
- **Trading.** The new scale is reached a tenth of the way each day (as positions in Lecture 26), and every change of position costs 5 bp.
- **Groups.** Average-linkage clustering on 1 − concordance of the markets' trend phases (Lecture 25 §4: sign of the 26-week return, weekly; sign ignored, since a market that always trends the opposite way is the same bet for a trader who can be long or short) over the past three years, cut into five groups; recomputed at each year end.
- **Out of sample.** Reviews at each year end 2012-2025, traded the following year, 2013-2026, on Lecture 25's markets and Lecture 26's speeds chosen at the same review.

## Measures (the same for all three)

1. Sharpe ratio after costs, total and per year.
2. Worst drawdown, and the loss in the 12 worst months of the rule.
3. **Risk forecast**: the realised volatility of each next month divided by the 10% target. Good: close to 1 on average and with a small spread.

Differences against the rule: block bootstrap over calendar months (2,000 resamples), 90% bands; Benjamini-Hochberg at 5% over the two rivals and three measures.

## Three expectations

1. **Position-aware risk keeps the realised risk closer to target** (smaller spread of realised over target) and **cuts the worst drawdowns**, because it scales down when positions stack in the same direction before a reversal hits them all.
2. **On Sharpe ratio, volatility only is hard to beat**: neither rival differs from the rule by more than about 0.05 (DeMiguel, Garlappi and Uppal 2009: estimation error eats most of what correlations promise).
3. **Groups by trend phase add little**, because Lecture 25 already removed the duplicates; the groups will look much like the asset classes.

## Kept short (a section and exercises, not tested here)

- **Losing together in stress**: how often two streams are in drawdown at the same time; each stream's share of the portfolio's worst days (expected shortfall).
- **Stress scenarios**: today's positions priced through 2008, March 2020 and the 2022 rate shock, as a bound rather than a weight.

## Sources to check before use

- DeMiguel, V., Garlappi, L. and Uppal, R. (2009). Optimal versus naive diversification. *Review of Financial Studies*.
- Ledoit, O. and Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. *Journal of Multivariate Analysis*.
- López de Prado, M. (2016). Building diversified portfolios that outperform out of sample. *Journal of Portfolio Management* (hierarchical risk parity, the idea behind grouping).

## Clarifications before results

- 2026-11-13: the groups use Lecture 25's trend-phase concordance with the sign ignored (wording above made precise). The user agreed that a standalone covariance lecture is too much: covariance is one way of measuring dependence, and maybe not the smartest for trend positions; this lecture asks the narrower question of when positions lose together.

## Changes before the full run

- 2026-11-13, after a design check on two reviews (2024-2025), before any full result: average linkage left one group of 14 markets and three single markets (XLV, TLT, EWZ in 2025), so equal risk per group would give one fund a fifth of the risk. **Ward linkage**, which forms groups of similar size, is now rival 2 (agreed with the user); average linkage stays reported as first fixed. The same check found a bug in the risk forecast (exposures and correlations in different column orders), fixed before any result.

## Changes after results

- **2026-11-13, exploratory ideas after seeing the results (the user), labelled as such.** Position-aware risk levered up in 2023-2025 because offsetting positions read as a hedge, while they were a sign of choppy markets. Three ideas follow; each is first checked descriptively (no portfolio profit and loss), and only an idea whose mechanism shows up earns a grid test, ideally confirmed on the capstone futures 2000-2022:
  1. **Trend strength**: scale up when the speeds agree within markets (sign-free). Check: its correlation with the position-aware scale; strongly negative would mean it is mostly that rival turned upside down.
  2. **Two kinds of low volatility** (the user): low volatility with chop (compression) is not low volatility with a smooth trend (drift, carry: crowded and vulnerable). Check: per market and month, low or high volatility (against its three-year median) by low or high efficiency ratio (six months); what follows over three months (volatility jump, trend return per unit of risk).
  3. **Calm and stacked in risk assets** (the user): when the risk assets (equity, credit, commodities) are mostly held long and their volatility is low, cut the risk of those positions only; bonds and currencies untouched; never lever up. Check: list the episodes 2013-2026 and what followed each.
- **2026-11-13, constant leverage (the user), added after results as a second legitimate way to run the same portfolio, not a rival to beat.** Same proportions (equal risk per market and class); the total scaled each day so that gross exposure stays at the rule's median of the past three years, reached a tenth of the way each day, 5 bp on every change. Presented neutrally (the user): performance, risk over time, drawdowns, storm-after-calm windows, each class's share of capital and of risk; one is called better only if the data show it clearly.
- **2026-11-14, the overlay isolated (the user: with a correlation overlay, which base is best?).** A 2x2: volatility target set daily on a forecast without correlations, and constant leverage, each with and without the overlay (multiplier: forecast risk ignoring correlations over forecast with them). **Correction of an earlier reading:** the multiplier was above 1 on only 4.4% of days (median 0.7), so the overlay almost never levered up; the 2023 leverage of position-aware risk came from targeting volatility daily on today's positions, which scales small net positions (speeds disagreeing in choppy markets) back up to full risk. The version without correlations did the same (2023: -15.6% against -6.3% for the yearly-scaled rule). The overlay's Sharpe effect is +0.01 and +0.02 (bands about +-0.09); its smaller drawdowns match its lower risk (drawdown over volatility 2.4 in all four).
- **2026-11-14, equal capital inside the classes (the user), added after results, presented neutrally.** Inside each class every market gets the same average gross exposure (instead of the same risk); classes still at equal risk, the total scaled yearly as in the rule.

## Restructure, 2026-11-14 (the user)

**The lecture becomes "Putting the Portfolio Together": blending speeds inside each market, then markets and classes, then scaling the total.** The correlation overlay and the ideas that grew from it (trend strength, two kinds of low volatility, calm and stacked risk assets) move to the allocation lecture, which deals with correlations across markets; their results stay above. Allocation across markets stays equal risk here (the user: that method was right; the methods are compared in the next lecture). Equal capital inside a class is kept only as a remark on leverage, because it breaks the rule of one method at every level.

**New step, fixed before its results: blending the speeds.** Equal weight per held stream piles risk into the medium band, where neighbouring speeds are nearly the same bet.

- **Rule (one sentence):** inside each market, give the held streams equal risk contributions on their correlation, pooled over all markets, with each stream's risk budget cut by its cost.
- **Correlation:** gross daily returns of the 36 streams, standardised per market, all in-sample data up to the review; the average of the markets' correlation matrices, each asset class the same total weight (as the vote of Lecture 26). It is mechanical (overlapping look-back windows on the same price), so it should be stable.
- **Cost:** each stream's marginal cost in the combined position (5 bp times its contribution to the blend's turnover, which nets fast against slow trades) per unit of its risk, in Sharpe-ratio units; the budget is 0.3 minus that cost, where 0.3 is an assumed Sharpe ratio before costs common to all speeds (a prior, not fitted; 0.2 and 0.5 reported as a grid).
- **Rivals:** equal per stream (the current rule), and correlation only (equal budgets), to separate the two effects.
- **Measures:** Sharpe ratio after costs out of sample 2013-2026, cost a year, the effective number of independent streams (squared diversification ratio), skew and the 12 worst months of the rule; shown descriptively: skew and behaviour in the worst months by speed.
- **Expectations:** (1) the effective number of independent streams rises and weight moves from the medium band to the distinct speeds; (2) the Sharpe ratio differs by less than about 0.05; (3) cost falls a little.

**Speed blend, results (2026-11-14).** Equal per stream reproduces the rule (0.486). Correlation between streams depends almost only on the ratio of speeds (EWMA: 0.93 at 1.4x, 0.81 at 2x, 0.53 at 4x, 0.33 at 8x, 0.09 at 46x); rules at the same speed are 0.90 correlated. The held band (43-359 days) has average correlation 0.70: about 1.4 effective independent streams of 20. Equal risk contributions move weights only between 0.045 and 0.058 (bets 1.38 to 1.40); costs at these speeds are 0.003-0.03 in Sharpe units, so the cost budget changes nothing at any prior; out of sample 0.482 against 0.486. Expectation 1 not met, 2 met, 3 not meaningful. Reading: the speed blend is robustness (not knowing which speed), not diversification.

**Speed blend, added 2026-11-14 (the user): maximum Sharpe ratio as a demonstration with a warning.** Long only, in-sample Sharpe ratios after costs pooled like the correlation. In-sample Sharpe ratios of the held streams differ only between 0.14 and 0.23, yet the weights concentrate in two to five streams (EWMA 89 days 58-82% in most years) and swing between reviews; out of sample 0.455 against 0.486 for equal weights, effective streams 1.29. The error maximiser of Michaud (1989).

**Two steps, not one (the user: keep two steps, say why).** Speeds inside each market, then markets. One step (every market x speed as its own stream, about 400) is possible; two steps are chosen because the speed overlap is the same in every market (estimated once, pooled), netting gives one position per market, streams inside a market are far more alike than markets (nested allocation is then close to one step: the logic of HRP and NCO), and limits are set per market. One step is an exercise.

**General, not only our speeds (the user):** the cost term matters little at 43-359 days but decides the blend for fast systems; the method is described generally.

**Literature checked (2026-11-14):** Levine and Pedersen (2016), FAJ 72(3) 51-66 (crossovers and time-series momentum are equivalent filters); Goulding, Harvey and Mazzoleni (2023), JFE 149(3) 378-406 (slow-fast disagreement marks turning points; dynamic blend modest gains); Michaud (1989), FAJ 45(1) 31-42 (estimation-error maximisers). Carver's handcrafting and forecast diversification multiplier seen only in secondary sources: check the book before quoting.

**Timing the speeds (the user, 2026-11-14: choose the worst speeds, if performance mean-reverts).** Descriptive check, nothing fitted: per market, the Spearman correlation of the 21 band streams' (43-359 days) Sharpe ratios relative to their window average, in one window against the next. 1-year windows: -0.03 (1,946 pairs, 47% positive); 3-year: -0.02 (485 pairs, 49% positive); commodities -0.09 at 1 year. Markets in a class move together, so the effective sample is near 90 (standard error about 0.02): neither persistence (chase the best) nor reversal (buy the worst) is measurable. Supports holding the band evenly. Goulding, Harvey and Mazzoleni (2023) condition on the state (slow and fast agree or not), not on past performance. Ehsani and Linnainmaa (2022, Journal of Finance) find factor returns persist: to be checked at source before quoting.
