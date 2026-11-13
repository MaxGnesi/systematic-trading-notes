# Lecture 27: when positions lose together — plan fixed before any result

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
