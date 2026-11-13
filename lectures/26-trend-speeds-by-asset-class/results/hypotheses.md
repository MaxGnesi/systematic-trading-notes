# Lecture 26: hypotheses, fixed before the results

Fixed on 2026-11-13 with the user's approval, before any result was computed. Every later change is dated here before it is judged on later data.

**The question.** For a trend follower trading the markets chosen in Lecture 25, which trend speeds should each broad asset class use? The aim is a small set of speeds that works across all markets of a class, chosen so that the speeds diversify each other, and judged out of sample against simpler choices. Choosing parameters is the one step of the workflow (Lecture 25, §1) that may look at strategy performance; it does so in sample only, chooses a region rather than a best point, and is judged out of sample against a luck baseline.

**What is already known.** Lecture 7 found that at equal speed the trend families give nearly the same results, and that differences between speeds of 0.1 to 0.3 in Sharpe ratio lie inside the noise (a standard error of about 0.2 over 26 years). Lecture 9 found that fast rules need partial trading to survive costs (EWMAC 8/32: from −0.43 to 0.01 at 20 bp). No result on the ETFs of Lecture 25 has been computed.

## Shared definitions

- **Markets.** Every ETF of Lecture 25 above the USD 10 m floor at each review, grouped into the five broad classes (equity, government bonds, credit, commodities, currencies); no sub-classes, to limit the room for fitting. Speeds are chosen on all liquid ETFs of a class (more evidence), and traded on the markets Lecture 25 chose.
- **Data.** Daily adjusted closes, free from Yahoo, as in Lecture 25.
- **Speeds.** Twelve horizons from two weeks to two years, each about 1.4 times (the square root of 2) the one before, and each a prime number of trading days (the user's proposals): 11, 17, 23, 31, 43, 61, 89, 127, 179, 251, 359 and 503. Primes share no common divisor, so box windows (past return, breakout) share none of their blind spots, and they stay off the round lookbacks many trend followers use (20, 50, 100, 200) and off the calendar's cycles (21, 63, 252 days). The round grid 10, 15, 20, 30, 40, 60, 90, 120, 180, 250, 360, 500 is run alongside (C5).
- **Rules, at equal speed (Lecture 7).** EWMAC with spans (h/4, h) rounded to whole days, a breakout over h days and a past return (time-series momentum) over h days, from `trading_models`. 36 streams per market.
- **Positions.** Forecast scaled to a 10% yearly volatility target with the market's volatility from recent returns (Lecture 9); partial trading, closing a tenth of the gap to the target each day (Lecture 9). The forecast is never capped: the EWMAC forecast is divided by its own rolling standard deviation, so it is finite by construction.
- **Costs.** 10 bp of the value traded for every market (main), 5 bp and 20 bp reported.
- **Measure.** Sharpe ratio after costs, per market and stream.

## The selection rule, per class

1. **Region (in sample).** For each market, the best stream's Sharpe ratio after costs and its standard error, the square root of (1 + SR²/2) divided by the number of years. A stream **qualifies** for the class if it lies within one standard error of the market's best in at least 75% of the class's markets.
2. **Core: well inside the region.** A speed (with its rule) belongs to the core if it qualifies, if the speeds one step faster and one step slower in the same rule also qualify, if it was in the region at at least two thirds of the past yearly reviews (once there are three), and if it still qualifies at costs of 20 bp. If a class's core is empty, the class uses the speeds shared by all classes (C1) and the empty core is reported as a result.
3. **Even spread (the rule).** Within each rule's core, the speeds at about one quarter and three quarters of the core's width on the log scale (the nearest speeds of the grid; one speed if the core holds fewer than three). No profit enters this step.
4. **Walk-forward.** The region, the core and the speeds are chosen at each year end from 2012 on, on all data up to then (at least five years), and traded the following year. The out-of-sample record runs from 2013 to 2026.

## Comparisons, out of sample 2013-2026, per class and in total

- **C1, buckets against one shared set:** the same rule applied to all markets of all classes together, giving one pair for every class.
- **C2, inside the core:** the even spread against (a) the least-correlated pair in the core (the core's ends, compared only; not the user's preference), (b) all core speeds with equal risk (the average of all random picks, no choice), and (c) 500 random pairs from the core, the luck baseline.
- **C3, against one default speed for all:** EWMAC 30/120.
- **C4, against all 36 streams with equal risk:** no choice at all.
- **C5, prime grid against round grid:** correlation between adjacent speeds and Sharpe ratio after costs, same rules otherwise.
- Measures: Sharpe ratio after costs, the worst drawdown, and the correlation of the class's stream with the other classes'. Differences by block bootstrap over months (2,000), one-sided; Benjamini-Hochberg at 5% over the five classes for C1.

## Expectations, written before the run

1. The regions are wide: most classes qualify at least five of the twelve horizons, and the regions of different classes overlap.
2. The fastest horizons (10 and 20 days) qualify in few classes after costs of 10 bp.
3. Mechanism hypothesis: government bonds favour slower speeds than commodities (bond trends follow slow policy cycles; commodity trends follow faster supply shocks). Stated before the run; it may well fail.
4. C1: per-class speeds beat one shared set by less than the noise: no class passes the Benjamini-Hochberg correction.
5. C2: the even spread, the least-correlated pair, all core speeds and the random pairs land close together out of sample, because the core does the work; all core speeds with equal risk has the smallest drawdowns. Finding the core matters; the point inside it hardly does.
6. C4: all 36 streams with equal risk do about as well as any choice, which would say that the region matters more than the point.
7. C5: the prime grid and the round grid differ little in correlation between adjacent speeds or in Sharpe ratio, because the ratio between speeds, not their divisibility, sets how different two speeds are. A benefit from trading on different days than the crowd cannot be measured with our data.

## Addendum 1, 2026-11-13, before any result: three lenses and a mix (the user's request for smarter approaches)

- **Lens A, backtest core:** the core of the selection rule above.
- **Lens B, stability selection:** 500 block-bootstrap resamples of the in-sample history (blocks of 3 months, the same blocks for all markets so that co-movement is kept); in each, the class's core is found as above (without the time check); a speed is supported if it is in the core in at least half of the resamples. Its frequency is kept as a weight.
- **Lens C, market persistence (returns only, no strategy profit):** for each class, the variance ratio of the class's markets at each of the twelve horizons (the variance of h-day returns over h times the variance of daily returns), averaged over the class's markets, in sample; a speed is supported if its variance ratio is in the upper half of the class's twelve.
- **The mix:** a speed (with its rule; lens C applies to all three rules at that horizon) is kept if at least two lenses support it; kept speeds are held with risk in proportion to their lens B frequency. If none is kept, the class uses the shared set (C1).

**Comparisons added:** C6, lens B alone (speeds in the core in at least half of the resamples, weighted by frequency); C7, lens C alone (the speeds in the upper half of the variance ratios, equal risk); C8, the mix, against the even spread, the shared set, all core speeds and random pairs from the core. Same measures and walk-forward as above.

**Expectations, written before the run:**
8. The mix does at least as well as the best single lens out of sample, and its chosen speeds change less from one year to the next (measured as the share of speeds kept from the previous review).
9. Lens C alone, which uses no strategy profit, does about as well as lens A; if so, choosing speeds needs no backtest.
10. Lenses A and C agree most for government bonds and commodities and least for equity.

## Addendum 2, 2026-11-13, before any result: random segments of history and splits by condition (the user's question)

- **C9, probability of backtest overfitting (Bailey, Borwein, López de Prado and Zhu, 2017; Lecture 7, §5).** For each class, 2007-2026 is cut into 12 consecutive segments of equal length; for each of the 924 ways to take 6 of them as the choosing half, each selection method chooses its speeds on that half and the result of its choice is ranked, out of sample on the other half, among all 36 streams (Sharpe ratio after costs). The probability of overfitting is the share of splits in which the choice ranks below the median. Methods compared: the single best stream in sample (the foil), the even spread, lens B, lens C, the mix, and all core speeds. A method that takes several speeds is ranked by the result of holding them with its weights.
- **C10, splits that hold the regime fixed or name it.** (a) Markets: each class's markets split at random into two halves (200 splits), speeds chosen on one half and judged on the other over the same years (Lecture 7, §5). (b) Conditions: speeds chosen on 2007-2021 and judged on 2022-2026 (before and after rates rose), and the reverse; and chosen on calm months and judged on turbulent ones and the reverse, turbulent meaning the third of months with SPY's highest realised volatility.
- **Expectations, written before the run:**
  11. The single best stream has a probability of overfitting close to 50% in most classes; the core-based methods and the mix stay clearly below it.
  12. Speeds chosen on half the markets hold on the other half better than speeds chosen on half the years hold on the other years.
  13. The speeds chosen before and after 2022 differ most for government bonds.

## Addendum 3, 2026-11-13, before any result: lens B built on random halves of everything (the user's proposal)

Lens B of addendum 1 is replaced, before any result. **Lens B, random halves:** at each review, within the in-sample period, 500 splits each take a random half of the 3-month segments of history **and** a random half of the class's markets. On the half taken, the class's core is found (without the time check); on the half left out (the other segments and the other markets), every stream is ranked by its Sharpe ratio after costs. A speed is supported if it is in the core in at least half of the splits and ranks in the upper half out of sample in at least half of the splits; its weight in the mix is the share of splits in which it was both. This is stability selection on halves (Meinshausen and Bühlmann, 2010; to be checked at source), with a test set nested in every split. C6 becomes this lens alone.
**Expectation, written before the run:** 14. Lens B on halves supports fewer speeds than the backtest core alone, and its speeds change less from one review to the next.
**Variant reported alongside (2026-11-13, before any result; the user's question):** lens B-all, random halves of the segments with all of the class's markets in every split, otherwise as lens B. It shows whether halving the markets changes the speeds supported; the main rule keeps lens B.

## Addendum 4, 2026-11-13, before any result: the plan simplified (the user: "too much")

Everything above that is not listed here is dropped before any result (even spread, least-correlated pair, the three-lens mix, the bootstrap, lens B-all, the default speed C3, the prime-against-round comparison C5, the market and condition splits of C10). The prime grid of twelve speeds, the rules, positions, costs and the walk-forward stay as defined.

**The rule.** Per class, at each review, 500 splits take a random half of the in-sample 3-month segments and a random half of the class's markets. On the half taken, the class's core is found: streams within one standard error of the market's best in at least 75% of the markets, whose neighbouring speeds in the same rule also qualify. On the half left out, every stream is ranked by its Sharpe ratio after costs. A stream is **kept** if it is in the core in at least half of the splits and ranks in the upper half out of sample in at least half of the splits; kept streams are held with risk in proportion to the share of splits in which they were both. If none is kept, the class uses the shared set (below).
**The alternative using no profit.** Per class, the horizons where returns persist most: the variance ratio of h-day returns, averaged over the class's markets, in the upper half of the twelve horizons; all three rules at those horizons, equal risk.
**Rivals, out of sample 2013-2026 (walk-forward).** (1) One shared set: the rule applied to all markets of all classes together. (2) All 36 streams with equal risk. (3) 500 random sets from the core, of the same size as the rule's.
**Honesty check.** The probability of backtest overfitting (12 segments, 924 splits; Bailey, Borwein, López de Prado and Zhu, 2017) for the rule and for the single best stream in sample.
**Measures and tests.** Sharpe ratio after costs, worst drawdown; differences by block bootstrap over months, Benjamini-Hochberg at 5% over the five classes for rival (1).

**Expectations (replacing 1-14 above):**
1. The regions are wide, and the 11- and 17-day speeds fail after costs of 10 bp in most classes.
2. Government bonds keep slower speeds than commodities (mechanism: policy cycles against supply shocks).
3. Per-class speeds beat the shared set by less than the noise: no class passes the correction.
4. The persistence speeds, chosen without any strategy profit, do about as well as the rule.
5. The rule's probability of overfitting is clearly below 50% in every class; the single best stream's is close to 50%.

## Addendum 5, 2026-11-13, before any result: the final plan, in one sentence (the user: "conceptually too much to digest")

This replaces the rule, rivals, checks and expectations of addendum 4; the speeds (the twelve primes), rules, positions, costs and walk-forward stay.

**The rule.** For each asset class, 500 times, split the in-sample years (3-month segments) and the class's markets at random into two halves; a stream **works** on a half if its Sharpe ratio after costs, averaged over that half's markets, is in the top half of the 36 streams; it **passes** if it works on the half where it was found and on the other half too. Keep the streams that pass in at least half of the 500 splits, with equal risk. If none passes, the class holds all 36 streams with equal risk.
**Compared out of sample, 2013-2026 (walk-forward):** (1) one set for all classes: the same rule on all markets together; (2) all 36 streams with equal risk. Sharpe ratio after costs and worst drawdown, per class and for the five classes together; differences by block bootstrap over months.
**Exercise, not part of the results:** choosing speeds without any backtest, from the horizons where a class's returns persist (variance ratio).

**Expectations (replacing all above):**
1. The 11- and 17-day speeds do not pass after costs of 10 bp.
2. Per-class speeds beat one set for all classes by less than the noise.
3. The kept speeds beat all 36 streams only slightly: the gain is in avoiding the speeds that fail, not in finding the best.

## Addendum 6, 2026-11-13, before any result: one set for all markets is the rule, per class is the challenger (the user)

The rule of addendum 5 is applied first to **all markets together**: 500 times, split the in-sample years and all liquid markets at random into two halves; keep the streams that work on one half and pass on the other in at least half of the splits; equal risk. This one set is the main rule, since it rests on the most evidence and makes the fewest choices. **Challenger:** the same rule within each asset class; it must beat the shared set out of sample to earn its extra choices. **Baseline:** all 36 streams with equal risk.
**Framing:** the lecture separates dependence on the sample we happened to see (measured in advance by the random halves) from a future unlike the past (not measurable in advance; addressed by mechanism, yearly review and the walk-forward, and named as an open risk).
**Expectations (replacing 2 of addendum 5; 1 and 3 stay):** 2. The per-class challenger beats the shared set by less than the noise in every class.

## Implementation, 2026-11-13, before any result

The three rules at horizon h, all as the sign of the trend (+1 long, -1 short), so no forecast scaling or capping arises:
- **EWMA crossover:** sign of the exponential average of log price with span h/4 minus that with span h.
- **Breakout:** the Turtle-style channel of `trading_models.momentum.donchian_state`, entering on a new h-day high or low and leaving on a new h/2-day low or high (flat in between).
- **Past return:** sign of the h-day return (`trading_models.momentum.past_return`).
**Position:** sign times 10% divided by the market's yearly volatility, from an exponential average of squared daily returns with a span of 36 days (Lecture 11), using data up to the previous close; partial trading, each day closing a tenth of the gap to the target (Lecture 9). **Return** of a stream: the position held over the day times the market's daily return, less 10 bp of the value traded. Daily adjusted prices from Yahoo (Lecture 25's download, which includes highs and lows).

## Addendum 7, 2026-11-13, before any result: blending by pass share (the user's question on markets that disagree)

**The rule (replacing the hard cut):** hold each stream in proportion to how often it passes on the other half of the 500 random splits (a weighted union): streams that pass in most splits carry most of the risk, streams that never pass carry none. Where markets and periods agree, this concentrates on the shared speeds (like an intersection); where they disagree, it holds both regions, each in proportion to how broadly it works (like a union).
**Reported alongside, in one table:** the intersection (streams passing in at least 90% of the splits, equal risk; may be empty) and the plain union (every stream passing at least once, equal risk).
**In the lecture:** one or two worked examples showing that the blend diversifies, e.g. two markets of a class that trend at different speeds.
**Expectation:** 4. The weighted union does at least as well as the intersection and the plain union out of sample, with a smaller worst drawdown than the plain union's best and worst cases; where a class's markets disagree, its weights spread over more speeds.
