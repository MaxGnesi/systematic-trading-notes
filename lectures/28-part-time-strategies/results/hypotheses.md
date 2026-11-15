# Lecture 28: part-time strategies — plan fixed before any result

Fixed 2026-11-14, before any number of this lecture was computed. Every later change is dated below with its reason. The literature behind the plan is summarised in the course's research report on regime detection for trend strategies (main finding: regime maps drawn on the same period make trend look robust everywhere; filters that could have been traded rarely beat always-in trend after costs).

## The question

A regime filter turns an always-in strategy into a part-time one. Can a filter that uses only information known on the day switch Lecture 27's baseline trend portfolio off in the regimes where trend fails, and does it beat both the always-in baseline and random switching with the same time in the market? Two families of filters are tested side by side, because they differ in kind:

| | Macro filters | Market-state filters |
|---|---|---|
| What they measure | The economy and policy | Prices themselves |
| Updated | Monthly, published weeks late | Daily, known at the close |
| Revised later | Yes: only data as published at the time are used | Never |
| Independent episodes 2000-2026 | A handful | Many |
| Strength / weakness | Mechanism / late, revised, few episodes | Timely / noisy, overlaps with trend's own signal |

This lecture builds on Lecture 7 (statistics of strategies not always in the market, §4.3), Lecture 8 (one test for every filter, the random filter, out-of-sample confirmation) and Lecture 11 (macro episodes described after the fact), and does not repeat them.

## The rule (one sentence)

**Trade trend while the regime is moving; step aside while it stands still** — for each variable, the unfavourable state is fixed below with its reason, before any result.

## Strategy, sample and attachment (the same for every filter)

- **Strategy:** Lecture 27's baseline (equal risk at every level, total scaled yearly to 10%), unchanged when the filter is on.
- **Off** means the whole portfolio's target position is zero (cash, zero excess return). Changes are reached a tenth of the way each day, like every position in Lectures 26-27, and every change costs 5 bp. While on, positions are exactly the baseline's: no re-levering to use the idle budget (that is Lecture 29).
- **Information:** every input lagged one trading day; macro data as published at the time (below).
- **Samples:** ETFs out of sample 2013-2026 (the baseline's own out-of-sample period); capstone futures 2003-2022 (Lecture 27's futures portfolio: Lecture 26's end-2025 held speeds, equal weights) as independent confirmation.
- **Per class** switching (e.g. inflation for bonds and commodities) is an exercise, not tested.

## Macro filters

| Filter | Measured as | Still (off) when | Why |
|---|---|---|---|
| Growth | US industrial production, year-on-year growth; "moving" = absolute 12-month change of that growth rate | In the bottom third of its own history to date | Trend earns on persistent macro news of either sign; a stable economy gives few persistent moves |
| Inflation | US CPI, year-on-year; absolute 12-month change of the inflation rate | In the bottom third of its own history to date | Trend earned in inflation shocks of either sign and least in stable inflation (Neville et al. 2021; AQR 2026) |
| Fed | Fed funds target (upper bound from December 2008) | No change in the past six months (on hold) | A moving policy rate drives persistent moves in rates, currencies and risk assets |
| Macro composite | The three above | At least two of the three are still | Waits until the evidence agrees |

**Data as published at the time.** Industrial production and CPI from the Philadelphia Fed's Real-Time Data Set (free, monthly vintages): on each day, the latest vintage available that day and its latest observation. The Fed's target rate is never revised; a change counts from the day after the announcement. Growth × inflation quadrants (the sign of each 12-month change) are used in the scan only, not as a filter, because the literature gives no clear direction for trend by quadrant. If a series is not available as described, the substitute is chosen and dated here before any result.

## Market-state filters

| Filter | Measured as | Off when | Why |
|---|---|---|---|
| Volatility | VIX, 21-day average | In the bottom third of its own history to date (still) | The "still" reading of the rule. Lecture 8 found trend slightly better in calm markets and Goulding, Harvey and Mazzoleni find volatility does not predict trend; expected to fail |
| Correlation across markets | Average pairwise correlation of the baseline markets' daily returns (sign ignored) over the past six months | In the top third of its own history to date | Many trends become one bet and reverse together; the one regime that predicted trend once lagged (Hurst, Ooi and Pedersen 2017); Lecture 8's version did not survive out of sample |
| Turning points | Share of the baseline markets whose 1-month and 12-month returns have opposite signs | In the top third of its own history to date | Disagreement between fast and slow trends marks turns, where trend loses (Goulding, Harvey and Mazzoleni 2023) |
| Yield curve | 10-year minus 2-year Treasury yield; absolute 12-month change | In the bottom third of its own history to date (still) | A curve that does not move gives rates and rate-sensitive markets little to trend on |
| Dollar | Broad trade-weighted dollar index; absolute 12-month percentage change | In the bottom third of its own history to date (still) | A dollar that does not move gives currencies and commodities little to trend on |
| Commodity curves (futures only) | Average across the commodity futures of the annualised gap between front and next contract; absolute 12-month change | In the bottom third of its own history to date (still) | Kept only if the capstone data hold the next contract; decided from the data's structure before any result |
| Market composite | The filters above | More than half of the available ones are off | Waits until the evidence agrees |

"Its own history to date": an expanding window starting with the first available data (at least five years before the first test day); the threshold uses only data up to the day before.

## Macro against market state

- **Both families:** off only when both composites are off (primary); off when either is off (reported).

## Measures (the same for every filter)

1. Sharpe ratio after costs on all days, and while on.
2. Worst drawdown; loss in the 12 worst months of the baseline.
3. Share of time on; switches a year.
4. Alpha over the baseline (intercept of the filtered returns regressed on the baseline's; Lecture 8, step 4).
5. **The luck baseline:** 1,000 random filters with the same share of time on and the same average length of spells, attached the same way (Lecture 8 §4.5); the share of them the real filter beats on Sharpe ratio.

## Verdict

A filter **works** if it beats at least 90% of its random filters on the ETFs and on the futures, with the p-values (one minus the share beaten) passing Benjamini-Hochberg at 10% within its family (macro: four tests; market state: six or seven). Thresholds are a curve, not a point: every filter is also run at bottom (top) quarter and half, and a filter that works only at one threshold is reported as fragile (Lecture 7 §5).

## Demonstration, not a hypothesis: the price of look-ahead

The scan's growth × inflation quadrants and the inflation filter are run twice: on today's revised data (FRED) and on data as first published (Philadelphia Fed vintages). Reported: the share of months in a different quadrant, and the difference in the filter's result.

## Three expectations

1. **Market-state filters react sooner but trade more:** costs and false alarms eat most of their gain.
2. **Macro filters switch rarely and late:** any gain comes from a few long episodes, with wide bands.
3. **Neither composite clearly beats the luck baseline alone; both families together do better than either**, because they fail at different times.

## Kept for later

- Lecture 29: regime-driven long-short strategies (economic trend, the FOMC strategies) and combining part-time with always-in strategies (risk budgets, the idle budget).
- Lecture 30: jump models and the similarity method as portfolio-level filters.
- Exercises: per-class switching; halving instead of switching off.

## Framing added 2026-11-14, before any result (the user: the approach must be clear to readers)

**The same regime information can be used in two ways: as a switch or as a strategy.** Lecture 28 tests it as a switch (does it tell us when to hold trend?); Lecture 29 tests it as a strategy of its own next to trend (does it add a second return stream that fails at different times?) and combines part-time with always-in strategies. The switch comes first because it is the natural first idea and continues Lecture 8; Lecture 28 also builds the regime series (real time, data as first published) that Lecture 29 reuses without re-testing. The lecture's lead and §1 state this framing.

## Data check, 2026-11-14, before any result

- **Philadelphia Fed Real-Time Data Set** (free, no account): CPI (PCPI, monthly vintages from November 1998) and industrial production (IPT, monthly vintages from November 1962); each vintage holds the full history as known then. Both available as planned.
- **Clarifications (no result seen):** a vintage dated month m reflects data available in the middle of that month, so it is used from the 16th of month m (one day's lag). "Its own history to date" for a macro measure is the measure over the full history of the vintage in use that day, so the threshold is as known that day and is available from the first test day.
- **Commodity curves: kept.** The capstone futures are stored one file per contract, and neighbouring contracts overlap (crude oil: 276 contracts). Commodities: crude oil, natural gas, gold, corn, soybeans, wheat, cocoa. On each day the front contract is the nearest one more than five trading days before its last day in the data, the next is the following contract; the gap is the log of front over next, annualised by the days between the two contracts' last trading days.
- **Revised data for the look-ahead demonstration:** FRED CPIAUCSL and INDPRO, downloaded once and saved locally.
- **Market-state series:** VIX (FRED VIXCLS), 10-year minus 2-year yield (FRED T10Y2Y), broad dollar index (FRED DTWEXBGS from 2006, spliced to DTWEXB before, on their overlap), Fed target (FRED DFEDTAR to 2008-12-15, DFEDTARU after).
- Reading the Philadelphia Fed's files needs the free package openpyxl, added to the requirements.

## Commodity curves moved out of the filter set, 2026-11-15, before any result (the user)

The user: a curve filter for commodities only is odd in a test that switches the whole portfolio; it can be an example. **Commodity curves are no longer one of the market-state filters**, so the market-state family is the same on both datasets: volatility, correlation across markets, turning points, yield curve, dollar, and the composite (six tests). The curve becomes a **worked example of a per-class switch**, labelled exploratory and outside the Benjamini-Hochberg families: the commodity trend sleeve of the capstone futures 2003-2022, scanned by backwardation and contango (front against next contract, as defined in the data check). Context: Levine, Ooi, Richardson and Sasseville (2018), Commodities for the Long Run, Financial Analysts Journal 74(2), 55-68, with futures prices from 1877 (seen in abstract and summaries only; check at source before quoting). The term structure of the other classes (bond yields, interest-rate differentials) is carry, a strategy of its own, and belongs to Lecture 29.

## Futures sample, 2026-11-15, before any filter result

The capstone futures start in 2000, so the market-state thresholds (five years of their own history, as fixed) exist only from 2005-2006. **The futures sample is 2006-2022 for both families** (instead of 2003-2022), so that macro and market-state filters are judged on the same days. The futures baseline reproduces Lecture 27 (Sharpe ratio 0.466 over 2003-2022).

**Scan, result (2026-11-15; descriptive, nothing switched).** Baseline Sharpe ratio on the days each filter would be off against on, fixed threshold (results/scan.json, figures/28_scan.png). No variable separates the days in the direction fixed in the plan on both datasets with a band excluding zero. Two separate in the opposite direction on both datasets: trend earned more when the dollar stood still (ETFs 1.06 against 0.11; futures 1.27 against 0.32; both bands exclude zero) and when the Fed was on hold (ETFs 1.13 against 0.01, band excludes zero; futures 0.69 against 0.41). The yield curve supports the plan on the futures (0.09 still, 0.73 moving) but not on the ETFs. Growth, inflation, turning points and correlation: no clear separation. Growth x inflation quadrants: 19% (ETFs) and 22% (futures) of days fall in a different quadrant on revised data than on data as first published, and the Sharpe ratio by quadrant changes with it (futures, growth down and inflation up: 1.12 first published, 0.39 revised). The filters are tested as fixed; the reversed patterns are exploration, to be read with Lecture 8's rule (a pattern found after looking needs confirmation on data it was not found in).

**Scan on the shared years (2026-11-15, descriptive; the user asked whether ETFs and futures disagree).** On 2013-2022, ETFs and futures give nearly the same picture for growth, the Fed, volatility and the dollar (the two baselines are 0.75 correlated, both Sharpe 0.61); they differ only for turning points, inflation and the yield curve, with small gaps. The apparent disagreements of the full samples come from the futures' years 2006-2012 (still volatility -0.59 against moving 0.97; Fed on hold 0.28 against moving 0.65), when the relations ran the other way. Reading: the effect of a regime on trend changes between periods, as expected with few macro episodes. The dollar is the one variable with the same sign in all three windows (trend earned more when the dollar stood still: 1.38/0.19, 1.52/0.30, 0.85/0.35); found after looking, so a candidate for independent confirmation, not a result.

## Filters, result (2026-11-15, as fixed)

**No filter works.** None beats 90% of its random filters on both datasets; none passes Benjamini-Hochberg within its family (results/filters.json, figures/28_filters.png). ETFs: every filter's Sharpe ratio is below always-in (0.49); the best against luck is correlation high (on 91% of days, 0.52, beats 85%). Futures (always-in 0.55): growth still beats 95% (0.63; on the ETFs 50%), the curve 87%, volatility 86%, both composites 89%. Being out of the market alone lowers the all-days Sharpe ratio by about the square root of the time in the market (Lecture 7 §4.3), which is why the random filters' median sits well below always-in (ETFs 0.33). Expectation 1 met (market-state filters trade more: turning points 40-47 switches a year, alpha t -2.6 on the ETFs); 2 met (macro filters switch 1-3 times a year, results driven by few episodes); 3 not met (the combination of the families does not help).

## Exploration after the results (the user, 2026-11-15; labelled as such, not confirmatory)

- **Why, Fed on hold (ETFs).** The pattern is one episode: the years with the Fed on hold all year were 2013-2015 and 2021 (zero rates), and 2014 alone gave +24.9%. Every class earned a little more on hold days. On the futures 2006-2012 it ran the other way (fast cutting in 2007-08 was good for trend). Reading: a regime label that stands for one or two episodes, not a mechanism.
- **Why, dollar still (ETFs).** Spread over many years (still days beat moving days in 2017-2021 and 2024-2026), from equity and currencies most. Consistent across three windows in the scan but negative as a switch (it leaves the market on the wrong days at the fixed threshold: the filter switches trend OFF when the dollar is still, which the scan shows were the good days). An open question: why sharp dollar moves coincide with weak trend returns.
- **Volatility, level and direction (the user: trend earns when volatility expands, but extreme volatility tends to mean-revert).** Baseline Sharpe ratio by VIX level (fifth of its history to date) and its 3-month change (figures/28_volatility.png). Rising volatility: ETFs -0.42, 2.52, 0.83, 0.79, -0.81 from lowest to highest fifth; futures 0.02, 0.56, 0.24, 1.02, 0.26: rising volatility helps at moderate levels and stops helping at the highest level, on both datasets (the user's inverted U). Highest fifth and falling (after a spike): the best cell on both (1.29, 1.67). Cells hold 4-16% of days; found after looking; a candidate for an independent test (for example the futures 2000-2005 and other markets), not a result.
- **Correlation, level and direction (the user: maybe correlation behaves like volatility; exploration).** Same split for average correlation across markets (figures/28_volatility.png, lower row). Rising correlation: ETFs 0.99, 0.95, 1.68, -0.90, 0.05 (lowest to highest fifth); futures -, 1.01, 1.56, 0.21, 0.51: rising correlation from a middle level is the best cell on both (1.68, 1.56), and it stops helping at high levels, like volatility. Unlike volatility, falling from the highest level is not good (futures -0.62; ETFs: no such days, since 2008 dominates the history). Cells uneven (0-32% of days). Weaker than the volatility pattern; found after looking.
