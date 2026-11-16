# Lecture 30: the final portfolio — plan fixed before any result

Fixed 2026-11-16, before any result of this lecture was computed. Agreed with the user. Every later change is dated below with its reason.

## The frame: realistic expectations (the opening of the lecture)

The lecture closes the course with one portfolio built from simple, rule-based strategies, and with the expectation such a portfolio can honestly carry. Setting that expectation is part of the method (user): a researcher who expects a simple rule to deliver a very high Sharpe ratio keeps adjusting it until the backtest agrees, which is curve fitting by another name; one who aims for **performance comparable to, or slightly above, long-only indices with low correlation to them** stops at a robust rule. That target is realistic, and it is valuable: in practice a strategy that earns like the market but moves differently from it is what investors pay to add to their portfolios.

## The rule (one sentence, our proposal)

**Hold trend (Lecture 27's baseline) and carry (Lecture 29's rule, unchanged) at equal risk, the total scaled to 10% a year, and judge it as an addition to a long-only portfolio.**

## Rivals and benchmarks

- **Rival:** trend, carry and value from fundamentals (Lecture 29 §5.4) at equal thirds of the risk. Value enters the portfolio only through this rival; the decision is fixed now, before the test.
- **Yardsticks:** trend alone (Lecture 27); and the long-only benchmarks, US equities (S&P 500, total return over cash) and 60/40 (S&P 500 and intermediate Treasuries, VFITX).

## Samples

- **The test: 1990-2005**, years never used to build or tune carry or value. Trend: Lecture 28's 12-market trend portfolio for 1990-2005 (the baseline's rules on long free series). Carry with Lecture 29's rule, each group entering as its data begins: currencies from 1990 (the euro before 1999 via the German mark at the fixed rate; Japan's call-money rate before its 3-month rate begins in 2002); government bonds from the 1980s for seven countries with daily central-bank yields, Australia from 1995 and Germany from 1997; equities, the US throughout (Shiller), other countries from about 1997 (country funds from 1996); commodities from about 2000 (the capstone futures). A partial universe, stated: for most of the period carry rests on currencies and bonds.
- **For reference, not as a test:** 2006-2022 (futures) and 2013-2026 (ETFs), the years Lectures 27-29 used.

## Measures (the same for every portfolio)

1. Sharpe ratio (daily where the data allow, else monthly, stated), return, volatility, worst drawdown, Calmar, Omega, skew, worst month.
2. Correlation with US equities and with 60/40.
3. **The investor's frame:** a 60/40 portfolio with 0%, 20%, 30% and 50% of its risk budget moved to the rule, at 60/40's volatility: Sharpe ratio and worst drawdown.
4. Luck: 1,000 random strategies on the same markets, as Lecture 29; and the deflated Sharpe ratio counting the tries of Lectures 27-30.
5. **The realistic expectation:** the backtest's Sharpe ratio cut, one source at a time, to an expected live range: monthly against daily measurement, selection (the deflated Sharpe ratio), costs (5, 10 and 20 bp per trade), and the period (in-sample years against 1990-2005).
6. In brief, from the folded lectures: gross leverage and each group's share of risk over time; the cost of the monthly rebalancing with Part IV's cost estimates; capacity in a sentence.

## Three expectations

1. **On 1990-2005, carry earns a positive Sharpe ratio with low correlation to trend** (below 0.3), weaker than in 2006-2022 since it rests mostly on currencies and bonds.
2. **On 1990-2005, trend + carry earns at least as much per unit of risk as trend alone.**
3. **On 1990-2005, moving 20-30% of a 60/40 portfolio's risk budget to the rule raises its Sharpe ratio and reduces its worst drawdown.**

## Verdict (graded, not pass/fail)

The evidence is read together: the Sharpe ratios as probabilities (against random strategies; deflated for the tries), the breadth across groups and periods, whether the 1990-2005 results point the same way as the in-sample years, and what the rule adds to a long-only portfolio. The realistic expectation (measure 5) is the number the lecture ends on.

## Kept for later / exercises

- The hedge, value tilts and mixes of Lecture 29 are not revisited.
- Exercise: rebuild the 1990-2005 test with your own Lecture 29 variant, fixed before you look, and count it as a try.

## The course close: where higher Sharpe ratios come from (user, 2026-11-16)

Not to diminish the result but to set direction. Large multi-strategy funds often report higher Sharpe ratios than this portfolio's realistic range; the difference is mostly breadth and granularity, not a better signal (Grinold's law, Lecture 1 §5.4: IR ≈ IC × √breadth). The closing section compares, source by source, this portfolio (about 40 markets, two or three styles, monthly or daily, whole countries, free data, a flat cost) with a large fund (thousands of instruments, dozens of mostly market-neutral strategies, intraday and single names, capacity-limited niches, measured execution and technology, paid data and large teams), and points each source to where the course touched it (Lecture 25 markets and capacity; Lecture 1 many small edges; Part IV tick data, microstructure and execution). Message: this portfolio is the base layer; higher Sharpe ratios come from adding breadth and granularity, at a cost in data, infrastructure and capacity. Directions to explore next, not a verdict on what was built.

## Results (2026-11-16, `scripts/l30_test.py`, results/test.json; monthly)

**1990-2005, the test.** Trend 0.78 (worst drawdown −12.6%); carry 0.99 (currencies 0.74, bonds 0.74, commodities 0.05 from 2000, equities −0.20 from about 1997), correlation with trend 0.19; **the rule, trend + carry, 1.11** (−14.4%, Calmar 0.81, Omega 2.33); the rival with value 0.89 (−9.8%); US equities 0.57 (−46.3%); 60/40 0.71 (−24.6%); the rule's correlation with 60/40 −0.03. 60/40 with 20/30/50% of its risk in the rule: 0.97 / 1.10 / 1.31, worst drawdown −19.4% / −16.4% / −9.7%. Luck: carry and the rule beat all 1,000 random strategies (95th percentiles 0.36 and 0.83). **All three expectations hold.**
**2006-2022, reference.** Trend 0.67, carry 0.54, the rule 0.84, the rival 0.81; 60/40 0.66; 60/40 with 30% in the rule 0.93.
**Costs.** At 10 bp per trade on carry the rule earns 1.01 (1990-2005) and 0.68 (2006-2022); at 20 bp 0.82 and **0.36**, below trend alone: carry's edge is fragile to costs, since its scores move every month.
**Reading for the realistic expectation.** 1990-2005 was carry's best era (currency and bond carry before the 2008 unwind); monthly Sharpe ratios run about a fifth above daily ones (trend 1990-2005: 0.78 monthly, 0.64 daily); the 2013-2026 ETF years gave the rule 0.45. These go into the haircut table.
**When each carry group trades in the test** (first month with a position, after each group's three years of scaling history): currencies 1990, bonds 1995, equities 2001, commodities 2004; the rule's chart starts in 1993. So 1993-1995 is currency carry only, 1995-2001 currencies and bonds.
