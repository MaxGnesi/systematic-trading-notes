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

## Changes after the plan was fixed

**2026-11-15, before any strategy return (user agreed): currencies from spot and rate gaps.** Carry and value on currencies use the nine G10 currencies against the dollar (euro, yen, pound, Swiss franc, Canadian, Australian and New Zealand dollars, Norwegian and Swedish krone), built from FRED's daily spot rates and the OECD 3-month interbank rates (FRED, monthly, the previous month's value applied through the current month): return over cash = spot return + (foreign rate − US rate) × days / 365, and carry = the rate gap itself. Reason: three currency futures cannot be ranked meaningfully (a ranking of three is long one, short one), and the rate gap measures carry directly, without the traps of a futures curve (stale later contracts, roll days). Check done before any strategy was built (`scripts/l29_fx.py`): the built euro and yen returns correlate with the capstone futures at 0.995 monthly (0.87 daily, because the spot rate is fixed at noon in New York and the futures settle later) and earn 0.3-0.5% a year more (interbank rates sit a little above the rates in futures prices, a known gap in covered interest parity). The currency group of the futures dataset is these nine currencies; trend keeps its own markets. FRED's euro and pound rates end in January 2026, so those two series end in April 2026; the futures sample ends in 2022 and is unaffected. **Emerging-market currencies** become an exercise (the peso and the rand have both legs free on FRED; the zloty, forint and koruna need Yahoo spot): does carry earn more with them, and what did 2008 cost?

**2026-11-15, before any strategy return (user's suggestion): currency value from real exchange rates.** Currency value uses the BIS real broad effective exchange rates (FRED, `RB..BIS`, monthly from 1994, each month used from the start of the month two months later, since the BIS publishes in the middle of the following month): value = minus the log of today's real rate over its average 4.5 to 5.5 years earlier. Reason: a real rate removes inflation; on nominal prices a currency with high inflation looks ever cheaper as it depreciates, which is not value (Asness, Moskowitz and Pedersen 2013 use real exchange rates for the same reason). For the ranking (the rule) each currency's own real rate is used: the dollar's part is common to all nine and drops out of a ranking. For the own-sign rival the signal is measured against the dollar (the currency's value minus the dollar's). The first signal is September 1999; the sample from 2006 is unaffected. Value on the other groups is unchanged (5-year reversal of the series we trade).

**2026-11-15, before any strategy return (user): carry signal = level and change.** Within each group the carry signal is the average of two ranks: the rank of today's carry (the level, AQR's signal) and the rank of its change over three months (today's carry minus carry three months earlier). Carry is averaged over 21 days first, because it is noisy day to day (the check in `scripts/l29_carry_check.py`: front-next and spot-front carry of the index futures agree at 0.95-0.96 in monthly averages but only 0.61-0.70 daily). Reason: the check found a permanent gap in the equity group (the S&P 500's carry above the Nasdaq-100's on 100% of days 2006-2022, by 0.9 points: the dividend gap), which a ranking of levels alone turns into a fixed long-short bet for 17 years. A permanent gap does not change, so the change rank is free of it; the level rank keeps half the weight and with it part of any fixed tilt. The change is our design choice; its literature is to be checked before the text.

**2026-11-15, before any strategy return (user): equity carry = earnings yield minus the bill rate.** The user's argument: holding a share at an unchanged price, the holder owns the year's earnings; the dividend is only the share paid out, a choice of the company, and the rest is retained for the holder. So equity carry = E/P − bill rate (trailing 12-month earnings of the S&P 500 over price, Shiller's free data, each month used with a three-month lag for publication), not the dividend yield minus the rate that the futures curve gives (AQR's definition, reported in the text for comparison). Free earnings exist only for the S&P 500, so equity carry is one market: its own sign (long when E/P is above the bill rate, short below), not ranked, and the Nasdaq-100 is not in equity carry. A futures holder receives only the dividends; the retained part reaches the holder only if the price comes to reflect it; this is stated in the text. Equity carry is a separate line in the results with its own luck baseline, and the carry test of the futures (currencies, commodities, bond funds, plus this line at the group's share of risk) stays one test.

**2026-11-15, before any strategy return (user agreed): commodity carry in 2022.** The capstone data hold no contract expiring after December 2022, so from early 2022 no contract twelve months ahead exists. Where none exists, the later contract is the furthest one at least six months ahead (flagged in the data; 41-82 days per market, all in 2022); past about mid-2022 not even that exists and commodity carry stops, the other groups sharing the risk (classes at equal risk among those with a signal). Check (`scripts/l29_commodity_check.py`, 2006 to 2022-11-18, pairing only contracts with a price that day, since gold's serial months rarely trade): a pair on 94% of days (the rest mostly holidays and late 2022); the later contract stale or untraded on 1-7% of its days; carry jumps two to four times as much on the days the pair changes as on other days, which the 21-day average absorbs; gold's carry is never positive.

**2026-11-15, before any strategy return (user): a second rival, the ranking with the main common risk removed.** Within currencies (9) and commodities (7), the ranking scores s are projected off the first principal component v of the group's volatility-scaled returns over the past three years, w = (I − v vᵀ) s, then scaled to the same risk as the rule. The long and short baskets then move alike on the group's main common risk (the dollar; the commodity market as a whole) while staying tilted to carry or value: in the user's example, long crude oil and short natural gas, when gas costs far more to hold, hedged by how the two actually moved together, rather than short both as own sign would be. Only the first component is removed: in currencies the second is usually risk-on against safe havens (the Australian dollar against the yen), which is largely the carry trade itself, a priced risk (Lustig, Roussanov and Verdelhan 2011, to be verified); removing it would remove the premium. Groups of one or two markets (bonds, equity) are left as in the rule. Robustness grid: 0, 1 and 2 components removed. The luck baseline's random scores go through the same projection. Added expectation: **removing the first component lowers volatility and drawdown more than it lowers the return.**

**2026-11-15, correction before any result: earnings delay six months, not three.** Shiller's monthly earnings are quarterly four-quarter totals spread linearly over the months (shillerdata.com; the old Yale copy stopped in October 2023), so a month's value depends on the next quarter's figure, published one to two months after that quarter ends; in the October 2026 file prices run to October 2026 and earnings to June 2026. Three months would use earnings not yet known; each month's earnings are used from six months later.

**Literature found 2026-11-15 (for the text).** The change in carry: Davis, Dorsten, Gillmann and Tsai (2022), "Carry Momentum", *Financial Analysts Journal* 78(1) (assets with rising carry beat those with falling carry, not explained by trend or carry); Boons and Porras Prado (2019), "Basis-Momentum", *Journal of Finance* 74(1); Ang and Chen (2010), working paper (changes in rates predict currency returns). Earnings yield minus a rate is called the yield gap or Fed model, not carry, in academic work: Maio (2013), *Review of Finance* 17(4) (it predicts); Asness (2003), "Fight the Fed Model", *Journal of Portfolio Management* 30(1) (real E/P against a nominal rate); called equity carry by Macrosynergy (practitioner, wording to be checked). Buybacks: Boudoukh, Michaely, Richardson and Roberts (2007), *Journal of Finance* (to be verified).

**2026-11-15, before any strategy return (user): net carry of each hedged version.** For 0, 1 and 2 components removed, the basket's own carry (Σ weight × carry, at the same risk) is reported over time, next to its return and drawdown. With two removed the basket is hedged against risk-off too and may hold a safe-haven currency long (the yen, the Swiss franc) while its carry stays positive overall; whether it does is the question. If net carry stays clearly positive, the hedge keeps the premium with less crash risk; if it falls towards zero, the risk-off exposure was the carry itself, and one component is the place to stop.

**2026-11-15, before any strategy return (user): the second rival hedges risk-off by half.** Replaces the two entries above on components removed. Within currencies and commodities, w = (I − v₁v₁ᵀ − α v₂v₂ᵀ) s, with v₁ and v₂ the first two principal components of the group's volatility-scaled returns over the past three years, then scaled to the same risk as the rule. The second rival is **α = ½**: the main common risk (the dollar; the commodity market) removed in full, the second (risk-on against safe havens in currencies) by half, so the long book holds some of a defensive currency (the yen, the Swiss franc) and the basket falls less in a panic while its carry stays positive overall; the projection, not a choice of ours, sets how much. Robustness grid: α = 0, ¼, ½, ¾, 1 (α = 0: only the first component removed; α = 1: both), each with Sharpe ratio, worst drawdown and **net carry** (Σ weight × carry) over time. The user's claim: a range of α keeps net carry clearly positive with smaller drawdowns; a plateau around ½ supports it, a single working α is noise. Expectation (replacing the one above): **α = ½ lowers volatility and drawdown more than it lowers the return, and its net carry stays positive.**

**2026-11-15, before any strategy return (user): equity carry against the real bill rate.** Equity carry = E/P − (bill rate − inflation), because E/P is a real yield (earnings grow with prices) and the bill rate is nominal (Asness 2003's objection to the Fed model). Inflation = the past 12 months' change in the CPI (FRED CPIAUCSL, each month used from the start of the month two months later, as it is published in the middle of the next month). Equity carry is long the S&P 500 when E/P is above the real bill rate, short below; as before, it is one market, a separate line with its own luck baseline.
