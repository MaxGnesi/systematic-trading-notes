# Lecture 29: Carry and Value

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 16, 2026 · Max Gnesi*

Lecture 28 tried to avoid trend's bad regimes by switching trend off, and no switch passed the test fixed in advance. This lecture takes the other answer to the same problem: hold, next to trend, strategies that earn for different reasons, so that they tend to earn when trend does not, without anyone forecasting the regime. The two best-documented candidates across asset classes are **carry**, what a position earns if prices stand still, and **value**, buying what is cheap against what it is worth. Both are built across four groups, currencies, commodities, government bonds and equity indices, and judged by what they add to trend. Where a published version exists, ours is checked against it, and every difference is shown with what it costs in agreement. The plan was fixed before any result was computed, and every change made after seeing results is dated and labelled ([results/hypotheses.md](results/hypotheses.md)).

## 1. A second business next to trend

| § | Topic | Question |
|---|---|---|
| 1 | A second business next to trend | What does carry add to trend, in one chart? |
| 2 | Why after Lecture 28 | Why hold another strategy rather than switch trend off? |
| 3 | The published versions and ours | How does AQR build carry and value, and where do we differ? |
| 4 | Carry | What does each group earn, and how is the signal built? |
| 5 | Value | How should value be measured, and does it earn? |
| 6 | Results | Does carry beat luck, and what does it cost in crashes? |
| 7 | What did not add | Which refinements failed, and what does that teach? |
| 8 | Summary | Takeaways, exercises, reading |

The lecture's central result fits in one chart.

![Carry next to trend](figures/29_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> x: time, January 2007 to October 2022, monthly (the capstone futures run out in December 2022); y: the value of 100 invested, excess return over cash, after costs. Black: trend, Lecture 27's baseline portfolio **across all its markets** (not trend on the carry markets). Dotted orange: carry alone, currencies, commodities, government bonds and equity indices together (§4). Blue: trend and carry at equal risk, the total scaled on its past to trend's risk. At the right: each line's Sharpe ratio and compound return a year, from January 2007, when the combination's scaling has a year of history (carry over 2006-2022, as in §4 and §6: 0.57). Our calculation ([results/key.json](results/key.json)).</sub>

Carry alone earned about what trend did (Sharpe ratio 0.59 against 0.67), but at different times: the two are almost uncorrelated (0.06). Held together at the same total risk, they earned more than either (0.86, 9.7% a year against 6.7%), with a worst loss about as deep as trend's alone (−20.6% against −19.3%). That is the whole case for a second strategy: not a better forecast, but returns that arrive at different times (§7.1 asks how independent the source really is). The rest of the lecture asks whether the result is real (it beats all of 1,000 random strategies, §6), what it costs (carry adds sudden losses, §6), where it fails (the ETF years 2013-2026, §6), and which refinements did not help (§7). Value, the second candidate, lost when measured by price against its past and earned a little when measured from fundamentals, without adding to trend (§5).

## 2. Why after Lecture 28: a switch against a second business

Lecture 28 and this lecture answer the same problem, that trend loses money in some regimes, in two ways.

| | Switching trend (Lecture 28) | A second strategy (this lecture) |
|---|---|---|
| What changes | Trend is turned on and off | Carry and value are held next to trend, always in |
| What it needs | A forecast, on the day, of when trend will do badly | A different reason to earn; no forecast |
| Idle capital | Stays idle: a switch can only take away | None: every strategy is always in |
| Judged against | Random switching with the same time in the market | Random strategies on the same markets, added to trend the same way |
| Result on our data | No switch passed; the strongest pattern ran against the plan | Carry adds to trend; value from fundamentals earns a little but does not add |

*Analogy (labelled):* a fisherman can stay in port when a storm is forecast, or also own an umbrella shop. The shop earns in storms without anyone forecasting them. A switch needs the forecast; a second business needs only that its customers come for a different reason.

Why carry and value, rather than strategies built from Lecture 28's regimes? They are the two cross-asset styles with the longest published record next to trend (momentum): Asness, Moskowitz and Pedersen (2013) for value and momentum, Koijen, Moskowitz, Pedersen and Vrugt (2018) for carry. Their returns come from different sources. Trend earns when prices keep moving; carry earns the income of a position while prices stand still; value earns when prices return towards a long-run level. A strategy that earns for a different reason is the "many small edges" of Lecture 1 §5.4 in practice.

Lecture 28's regimes are not thrown away: they are where carry and value are judged (§6), above all in the regimes where trend lost.

## 3. The published versions and ours

Carry and value have published constructions. Rebuilding them from free data forces choices, and each choice is a chance to differ from the literature, by necessity or by design. This section shows the published construction, ours, the reason for each difference, and the evidence of what it costs: the correlation of our series with AQR's published one, month by month, 2006 to October 2022. The pattern of the table, not its entries, is the point: a reader building a version of their own will face the same kinds of choices.

**The published series.** AQR publishes monthly returns of the value and momentum factors of Asness, Moskowitz and Pedersen (2013), by asset group, free in its data library ("Value and Momentum Everywhere: Factors, Monthly", AQR Capital Management, LLC). They are paper portfolios before costs, on more markets than ours. AQR publishes no carry factor in the free library; Koijen et al. (2018) describe the construction.

| Group | Published construction | Ours | Why we differ | Our value against AQR's (correlation) |
|---|---|---|---|---|
| **Currencies** | Value: 5-year change in the real exchange rate; 10 developed-market currencies, the US dollar among them. Carry: the interest-rate gap from forward rates | 9 currencies against the dollar, returns from spot rates plus the 3-month rate gap (FRED). Value: BIS real effective exchange rates. Carry: the rate gap | Free data; the same idea | **0.79** |
| **Commodities** | Value: price today against its average 4.5 to 5.5 years ago (5-year reversal); 27 commodities. Carry: slope of the futures curve | 7 commodities (capstone futures). Value: the same on the front contract's price. Carry: front against the contract 12 months later | No free clean futures for more commodities; 12 months removes the seasons | 0.56 |
| **Government bonds** | Value: 5-year change in 10-year yields; 10 countries, futures. Carry: term spread plus roll-down | 9 countries, returns built from each central bank's 10-year yield (no free bond futures). Carry: the term spread | No free bond futures; month-end yields from nine central banks | 0.69 |
| **Equity indices** | Value: book-to-market; 18 countries, futures. Carry: dividend yield minus the rate, from the futures | 15 country funds, hedged into dollars. Value: price against its past. Carry: the S&P 500's **earnings yield** minus the real bill rate; elsewhere the dividend yield minus the real cash rate | Book values are not free per country; earnings, not dividends, are what a holder accrues (buybacks), but free earnings exist only for the US | 0.46 |
| **Across groups** | Ranked within each group, equal risk across groups | The same, but weighted by a carry *score* rather than a rank (§4), and value against a 10-year trend line or from fundamentals (§5) | Our design choices, tested against the published versions (§5, §7) | – |

<sub><b>How to read the table.</b> One row per group. "Published": Asness, Moskowitz and Pedersen (2013) for value, Koijen et al. (2018) for carry. "Ours": what this lecture builds from free data. The last column is the correlation of the monthly returns of our value strategy, built with the published construction, with AQR's published value factor for the same group, 2006 to October 2022. Our calculation.</sub>

The agreement follows the universe. Where ours is nearly the same as AQR's, currencies, the two series move together (0.79); where we hold a fraction of the markets, commodities, or measure value differently, equity indices, agreement falls. Two of our first versions agreed far worse, and the comparison is what exposed them:

- **Bonds as two US maturities.** The first bond group held two US Treasury funds, a 5-year and a 20-year. Ranking them is a bet on the shape of the US curve, not on which country's bonds are cheap. Agreement with AQR was 0.19, and bond carry lost money. Rebuilt as nine countries, agreement rose to 0.69 and bond carry earned.
- **Equities as two US indices.** The S&P 500 against the Nasdaq-100 is not a value universe either: agreement 0.07. Rebuilt as fifteen countries: 0.46.

**What to take from this.** A published strategy is a family of choices, not a recipe (Lecture 1). Checking a rebuild against the published series early is cheap, and it catches errors that a backtest alone does not: both flaws above produced plausible-looking numbers.

## 4. Carry

**Key message.** Carry is what a position earns if prices stand still: the income of holding it, net of what holding it costs. Each group has its own measure of that income, but the strategy is the same everywhere: hold more of what pays more for its risk, and less of what pays less. Each group earns a little; the four together earn much more than any one, because their income comes from different places.

### 4.1 What carry measures in each group

| Group | Markets | Carry: what the position earns if prices stand still | Median carry, 2006-2022 |
|---|---|---|---|
| **Currencies** | 9 against the dollar: euro, yen, pound, Swiss franc, Canadian, Australian and New Zealand dollars, Norwegian krone, Swedish krona | The foreign 3-month rate minus the US rate: holding a currency earns its deposit rate and pays the dollar's | from −0.9% (Swiss franc) to +2.5% (New Zealand dollar) |
| **Commodities** | 7: crude oil, natural gas, gold, corn, soybeans, wheat, cocoa | The gap between the front futures contract and the one about 12 months later: a future rolls towards the price of the nearer contract | from −11.2% (natural gas) to +0.7% (soybeans) |
| **Government bonds** | 10-year bonds of 9 countries (US, Germany, Japan, UK, Canada, Australia, Norway, Sweden, Switzerland) | The 10-year yield minus the 3-month rate (the term spread): a bond earns its yield and is financed at cash | from +0.3% (Japan) to +1.4% (US) |
| **Equity indices** | 15: the US and 14 country funds | The US: the earnings yield of the S&P 500 minus the real bill rate. Elsewhere: the dividend yield minus the real cash rate | from 1.4% (Japan) to 5.1% (UK) |

<sub><b>How to read the table.</b> One row per group; the third column says in words what the carry number measures, the fourth gives the range of its median across the group's markets, a year. Our calculation from free data: FRED and OECD rates, the capstone futures, the central banks' 10-year yields, Shiller's S&P 500 earnings and the funds' distributions.</sub>

Three choices in the table need a word.

- **Commodities: 12 months, not the next contract.** Natural gas and grains have seasons: the gap between two nearby contracts often measures winter against summer, not the cost of holding. A contract twelve months away compares the same season. In 2022 the data hold no contract that far ahead, so the furthest contract at least six months ahead stands in until about mid-year (labelled in the data), and commodity carry stops after that.
- **Currencies: built from spot rates and rate gaps.** A currency's return over cash is its spot change plus the gap between the two interest rates. Built this way from free FRED data, the euro and the yen match the capstone futures with a monthly correlation of 0.995.
- **Equity carry: earnings, not dividends, in the US.** Holding a share at an unchanged price, the holder owns the year's earnings; the dividend is only the part the company chooses to pay out. In the US a large share of what companies return comes as buybacks, which the dividend yield misses. Earnings yield (E/P) is a real yield, since earnings grow with prices, so it is compared with the *real* bill rate (the bill rate minus past inflation), not the nominal one (Asness 2003 makes the same objection to comparing E/P with a nominal yield). Free earnings exist only for the S&P 500; elsewhere the dividend yield stands in, **a compromise**, labelled as such. Academic work calls E/P minus a rate the *yield gap* rather than carry; this is our definition, not the futures-implied one of Koijen et al. (2018), which uses the dividend yield.

### 4.2 From carry to positions

| Step | What happens | Why |
|---|---|---|
| 1. Measure | Carry in each market, averaged over the past month (daily data) or taken at the month end | Daily carry is noisy, about 2 to 3 points a year from day to day |
| 2. Two views | The carry **level** today, and its **change** over three months | A market whose carry is rising tends to outperform one whose carry is falling (Davis et al. 2022; Boons and Porras Prado 2019 for commodity curves); the change is free of permanent gaps between markets |
| 3. Score | For each view, half the carry in absolute terms and half per unit of the market's risk, each as a z-score within the group; then level and change averaged | A market paying much more should weigh more (absolute); a calm market paying a little can be worth as much as a wild one paying more (per unit of risk) |
| 4. Weights | Each market's weight in proportion to its score, long the positive, short the negative, weights summing to one in absolute value | The basket collects as much carry as it can; risk is set once, at the end |
| 5. Size | Each position: its weight × 10% ÷ the market's volatility over 36 months | Carry positions last many months; sizing on a short window would lever calm markets just before they move (Lecture 26) |
| 6. Groups | Each group scaled each year to 10% on its past three years; groups at equal risk; the total scaled to 10% | As trend (Lecture 27): no group dominates |

<sub><b>How to read the table.</b> One row per step from the carry numbers to the positions held each month; the right column gives the reason for each choice. Positions are set at the end of a month for the next, 5 bp per unit traded.</sub>

In symbols, for market $`i`$ in a group, with carry $`c_i`$, its 3-month change $`\Delta c_i`$ and volatility $`\sigma_i`$, and $`z(\cdot)`$ the z-score across the group's markets:

```math
s_i = \tfrac{1}{2}\Big[\tfrac{1}{2}\big(z(c_i) + z(c_i/\sigma_i)\big) + \tfrac{1}{2}\big(z(\Delta c_i) + z(\Delta c_i/\sigma_i)\big)\Big],
\qquad w_i = \frac{s_i}{\sum_j |s_j|}, \qquad \text{position}_i = w_i \,\frac{10\%}{\sigma_i}.
```

### 4.3 What each group earned

| Futures period, 2006 to October 2022, monthly | Currencies | Commodities | Government bonds | Equity indices | **All four** |
|---|---|---|---|---|---|
| Sharpe ratio | 0.24 | 0.18 | 0.28 | 0.46 | **0.57** |
| Worst drawdown | −35.5% | −39.5% | −19.2% | −27.3% | **−22.7%** |

<sub><b>How to read the table.</b> Each group's carry strategy on its own, scaled to 10% volatility, after costs, excess returns over cash; the last column holds the four at equal risk. Our calculation.</sub>

No group alone is worth much: their Sharpe ratios of 0.18 to 0.46 come with drawdowns of 20% to 40%. Together they earn 0.57 with a shallower worst loss than three of the four. The income of a high-rate currency, a backwardated commodity, a steep yield curve and a cheap stock market are paid for different risks and do not fail together. That, not a cleverer signal, is where carry's result comes from.

## 5. Value

**Key message.** Value buys what is cheap and sells what is dear, betting that prices return towards what the asset is worth. Measured by price against its own past, the simple proxy of the literature, it did not earn in this period, on our data or on AQR's. Measured from fundamentals (real yields, purchasing power, the yield gap of stocks over bonds, inventories) it earned a little and held trend's Sharpe ratio steady. Carry's income is visible; value has to estimate worth, and that needs a stronger arsenal (§5.4).

### 5.1 Measuring cheap and dear

| Step | What happens | Why |
|---|---|---|
| 1. A price without income | The real exchange rate (currencies), the front contract's own price (commodities), the 10-year yield (bonds), the index without dividends in local currency (equities) | A total-return series rises with its income; measured on it, a market that pays a lot always looks dear and one that costs a lot to hold always looks cheap |
| 2. A trend line, not a flat average | A straight line through the past ten years of monthly log prices, extended to today; value is today's distance below the line | Prices that grow over time sit above their own past average most of the time; against a flat average the S&P 500 looked cheap in only 12-14% of months in 2006-2022, gold in 5% |
| 3. A z-score | The distance divided by how far the market usually strays from its own line | A volatile market strays further; without this, natural gas was the most extreme commodity in 31% of months |
| 4. Positions | Ranked within each group, long the cheapest, short the dearest; sized and scaled as carry (§4.2) | The same machinery for every strategy |

<sub><b>How to read the table.</b> One row per step from prices to positions, with the reason for each. Steps 2 and 3 are our design; AQR's construction (the price against its average 4.5 to 5.5 years earlier) is reported alongside as the published variant (§3). For bonds a yield above its line means cheap.</sub>

Step 1 was learned the hard way. The first version measured value on the series we trade, which include income. The rolled natural-gas series, which loses money on every roll in contango, was "cheap" on 100% of days, and value would have held it long throughout; the bond funds, whose price rises with every coupon, were never cheap. A signal that never changes is a fixed position, not a strategy.

### 5.2 What value earned

| Futures period, 2006 to October 2022, monthly | Currencies | Commodities | Government bonds | Equity indices | **All four** |
|---|---|---|---|---|---|
| Value, our rule (10-year line, z-score) | −0.14 | −0.12 | +0.28 | +0.04 | **−0.09** |
| Value, AQR's construction | +0.10 | −0.04 | +0.19 | −0.28 | −0.01 |
| AQR's published value factor | +0.11 | +0.33 | +0.07 | −0.40 | +0.16 |

<sub><b>How to read the table.</b> Sharpe ratios, monthly, excess returns over cash. Our two rows: after costs, our markets (§3). AQR's row: its published factors, before costs, on more markets, the same months; its last column averages AQR's four asset-allocation groups. Our calculation; AQR Capital Management, LLC.</sub>

Value lost a little with our rule and broke even with AQR's construction. Its correlation with trend is −0.35: it tends to earn when trend loses, as hoped, but it earned too little to help. Added to trend at equal risk it lowered the Sharpe ratio from 0.67 to 0.47, and it beat 48% of 1,000 random strategies: indistinguishable from luck.

### 5.3 Why: three readings

1. **The period.** AQR's own value across asset classes earned 0.35 in 1972-2005 and 0.16 in 2006-2022; equity-index value lost (−0.40). Within the period it came in bursts: 0.70 in 2016-2020, −0.57 in 2023-2026. Part of our result is the years, not the build.
2. **Too few independent bets.** Value turns over in years. Sixteen years hold a handful of value cycles per market, and a Sharpe ratio over sixteen years has a standard error of about 0.25: −0.09 cannot be told apart from a modest real edge of +0.2, nor from zero.
3. **Breadth.** Value is a cross-sectional style, and ranking works better with more markets. Where our universe matches AQR's (currencies, 9 of their 10) our value tracks theirs closely (0.79); with 7 commodities against their 27, much of what earned for AQR is missing.

*Our reading (labelled), for the price version.* Value is not shown to work here, and not shown not to work. Its role in a portfolio is the one the correlation suggests, a diversifier of trend, but on this sample it did not earn enough to pay for its place. Whether it belongs in Lecture 30's final portfolio is a question for that lecture, to be decided before looking at data it was not tested on.

### 5.4 Value from fundamentals

Price against its own past is a proxy: it needs no data beyond prices, which is why the literature uses it where fundamentals are missing. Real value compares a price with what the asset is worth. Each group has a natural free measure; each was fixed in the plan before its data were loaded, as a change after the first results, and is counted in §6.2.

| Group | What makes it cheap | Measured as | Free source |
|---|---|---|---|
| Government bonds | It pays more after inflation | The 10-year yield minus the past year's inflation, compared across countries | Central banks, OECD |
| Currencies | It buys more than its price level justifies, and less than usual | Half the gap between the spot rate and purchasing-power parity, compared across currencies; half the real exchange rate against its trend (§5.1) | World Bank PPP, BIS |
| Equity indices | Stocks pay more over bonds than usual | The earnings yield (US: ten years of real earnings, the inverse of the CAPE) or the dividend yield (elsewhere), minus the real 10-year yield, against its own 10-year history | Shiller, OECD, the funds |
| Commodities | Stocks are scarce, or the price is low after inflation | Half inventories against the same month of the past five years, low = long (Gorton, Hayashi and Rouwenhorst 2013); half the real price against its 20-year history (gold and cocoa: the real price only) | EIA, USDA, World Bank |

<sub><b>How to read the table.</b> One row per group: in words, what makes a market cheap; the measure; the free source. Each measure is known at the end of the month before the position. PPP and USDA stocks are revised history with no point-in-time versions, so those parts carry some look-ahead; fundamental currency value starts in 2004.</sub>

| 2006 to October 2022, monthly | Price version (§5.2) | **Fundamental version** |
|---|---|---|
| Currencies | −0.14 | +0.08 |
| Commodities | −0.12 | +0.05 |
| Government bonds | +0.28 | +0.10 |
| Equity indices | +0.04 | +0.17 |
| **All four** | **−0.09** | **+0.14** |
| Correlation with trend | −0.35 | −0.32 |
| Trend + value (trend alone 0.67) | 0.47 | **0.65** |
| Random strategies beaten: alone / added to trend | 48% / – | 77% / 90% |
| 2013-2026: value; trend + value (trend alone 0.41) | −0.13; 0.37 | +0.12; 0.32 |

<sub><b>How to read the table.</b> Sharpe ratios after costs, excess returns over cash; the two value strategies use the same machinery and differ only in how cheap and dear are measured. "Random strategies": 1,000 per strategy with the same holding periods, as in §6.1. Our calculation ([results/value_fund.json](results/value_fund.json)).</sub>

Fundamentals turn value from a small loss into a small gain (0.14, close to AQR's own 0.16 in this period), better in three of the four groups, as expected in the plan; bonds, where the price version was already a yield, are the exception. Its correlation with trend stays negative, so next to trend it now roughly holds trend's Sharpe ratio instead of costing a fifth of it, and it beats 90% of random strategies added to trend, which dilute trend more. It still does not add to trend, and in 2013-2026 it costs. *Our reading (labelled):* value was mismeasured by the proxy, and measured properly it is a small diversifier of trend, the weakest of the three styles in these years.

One more observation links value to carry. In currencies and commodities the two point in opposite directions: the high-carry markets tend to be the dear ones (the signals' rank correlation is −0.12 and −0.24; the strategies' returns −0.31 and −0.43). A currency that pays a high rate attracts money and appreciates; a commodity in backwardation has usually just risen. §7 asks whether that can be used.

## 6. Results

**Key message.** Carry passes every test of luck we set, but less comfortably once the search that chose it is counted: about 90% likely to be more than luck, not the near-certainty that a single comparison suggests. It adds to trend on every measure in 2006-2022, at a price, sudden losses, and it did not help in 2013-2026.

### 6.1 Against luck

The rule was compared with 1,000 random strategies on the same markets, each market's position switching at random with the same average holding period, built by the same machinery and added to trend in the same way (futures period, monthly).

| | Carry | Random: median | Random: 95th percentile | Share of random beaten |
|---|---|---|---|---|
| Carry alone | 0.57 | −0.11 | 0.28 | 100% |
| Trend + carry | 0.86 | 0.36 | 0.65 | 100% |
| Value alone (price version) | −0.09 | −0.08 | 0.34 | 48% |

<sub><b>How to read the table.</b> Sharpe ratios after costs, 2006 to October 2022. The random strategies have no information by construction; added to trend at equal risk, they dilute it (median 0.36 against trend's 0.67 alone), which is the bar a real strategy must clear. Our calculation.</sub>

### 6.2 The number of tries

The comparison above judges one strategy. But the rule was chosen from many versions tried along the way, and the best of many tries is lifted by luck (Lecture 1 §5.3; Bailey, Borwein, López de Prado and Zhu 2014). Counting them honestly:

| | |
|---|---|
| Carry configurations tried | 21: the robustness grid (§7), three hedges, three value tilts, four combinations of the best rows, two mixes |
| Their average correlation | 0.71 |
| Effective number of independent tries | 6.8 |
| What the best of 6.8 tries of noise would show | Sharpe ratio 0.20 |
| The rule, on the same months | 0.53 |
| **Deflated Sharpe ratio** | **0.90** (0.83 if all 21 counted as independent) |

<sub><b>How to read the table.</b> The tries are listed in [results/tries.json](results/tries.json) with their Sharpe ratios, on the months all of them cover (2008-2022). Effective tries: $`\bar\rho + (1-\bar\rho)M`$ for $`M`$ tries with average correlation $`\bar\rho`$. The deflated Sharpe ratio (Bailey and López de Prado 2014) is the probability that the rule's true Sharpe ratio is above what the best of that many tries of noise would show, taking into account the spread of the tries, the sample length and the fat tails of the returns. Our calculation.</sub>

Two things lower the number. The tries: 6.8 independent attempts make a Sharpe ratio of 0.20 what luck alone would deliver. And the tails: carry's monthly returns have a kurtosis of 8.6, far above the normal's 3, so a Sharpe ratio overstates how reliable its returns are. The best of the 21 tries earned 0.61; reporting it as "the" result would have overstated carry by a tenth of a unit.

**How much evidence to expect.** About 90% is good evidence, and a stricter bar would mostly measure the length of the sample. To be 95% sure that a Sharpe ratio is above zero takes about $`(1.65/\text{SR})^2`$ years:

| Sharpe ratio | Years of data to clear 95% once |
|---|---|
| 1.0 | 3 |
| 0.5 | 11 |
| 0.3 | 30 |
| 0.2 | 68 |

<sub><b>How to read the table.</b> One row per true Sharpe ratio; the right column is the number of years after which a one-sided test at 95% would just reject zero, before counting any search. A definition, from the standard error of a Sharpe ratio, about $`1/\sqrt{T}`$ over $`T`$ years.</sub>

Strategies that survive in competitive markets have Sharpe ratios of 0.3 to 0.5 after costs; an edge strong enough to clear the bar easily would be visible to everyone and competed away. So the evidence for a lasting edge is always noisy, and it is judged on several things together, not on one threshold:

1. **The statistics, as a probability**, here 0.90 after counting the tries;
2. **breadth**: carry earns in all four groups (§4.3);
3. **a reason it persists although everyone knows it**: carry is paid for bearing crash risk, which is why it still earns though it has been published for decades; the losses of §6.3 are the price of the premium, not a flaw in it (Lecture 1 §5.4: lasting edges are uncomfortable rather than secret);
4. **what it adds**: its value is next to trend (§6.3), not on its own.

### 6.3 What carry costs: crash measures

A Sharpe ratio measures risk by volatility. Carry's risk comes in sudden losses, so it is also judged by its worst loss (Calmar: return a year over the worst drawdown), by the balance of gains and losses (Omega: the sum of gains over the sum of losses) and by the asymmetry of its returns (skew).

| Futures period, monthly | Sharpe | Return a year | Worst drawdown | Calmar | Omega | Skew | Worst month |
|---|---|---|---|---|---|---|---|
| Carry | 0.57 | 5.9% | −22.7% | 0.26 | 1.61 | +0.29 | −12.0% |
| Trend | 0.67 | 6.7% | −19.3% | 0.35 | 1.67 | +0.41 | −7.4% |
| **Trend + carry** | **0.86** | **9.7%** | −20.6% | **0.47** | **1.95** | −0.15 | −11.4% |

<sub><b>How to read the table.</b> One row per strategy, excess returns over cash, after costs, 2006 to October 2022 (trend and the combination from 2007, when the combination's scaling has a year of history). Calmar and Omega: higher is better; skew: negative means the large months are losses. Our calculation.</sub>

On these years carry improves trend on every measure, crash measures included: Calmar from 0.35 to 0.47, Omega from 1.67 to 1.95, with a worst drawdown barely deeper. The cost is in the tail. Trend's positive skew, its habit of earning in crises, turns negative, and the worst month deepens from −7.4% to −11.4%. Currency carry shows the classic pattern most clearly (skew −0.45): steady income, then a sharp loss when high-rate currencies fall together. Carry is often described as picking up coins in front of a steamroller; the table shows both the coins and the steamroller.

### 6.4 Where carry earned: trend's weak regimes

The plan fixed, from Lecture 28, the two quadrants of each regime variable in which trend had done worst on the futures. In each, carry's Sharpe ratio against trend's:

| Trend's weak quadrant (fixed in advance) | Carry | Trend | Months |
|---|---|---|---|
| Volatility below average, falling | **0.33** | 0.11 | 81 |
| Volatility below average, rising | 0.70 | 0.79 | 43 |
| Correlation below average, falling | **0.34** | 0.21 | 50 |
| Correlation above average, falling | **1.02** | 0.43 | 46 |
| Growth down, inflation down | 0.25 | 0.30 | 63 |
| Growth up, inflation down | **1.69** | 0.27 | 27 |

<sub><b>How to read the table.</b> Rows: the six quadrants named in the plan before any carry result (Lecture 28's definitions, each month classified by its quadrant at the end of the month before). Monthly Sharpe ratios on the months in each quadrant, futures 2006 to October 2022. With 27 to 81 months a cell has a standard error of about 0.4 to 0.7, so single cells are weak evidence; the count across cells is the reading. Our calculation ([results/quadrants.json](results/quadrants.json)).</sub>

Carry beat trend in four of the six regimes where trend was weak, and lost narrowly in the other two. It is what a second business should do: earn when the first one does not, without a forecast of when that will be. The cells are small; the pattern across them, not any one number, is the evidence.

### 6.5 The weak spot: 2013-2026

On the ETF years the picture changes. Over 2013-2026 carry earned a Sharpe ratio of 0.23, with no commodity group after 2022, and trend plus carry (0.45) did slightly worse than trend alone (0.48), with a deeper worst loss (−28.1% against −20.1%). Two possible readings, neither tested here: the commodity group drops out after 2022, so carry rests on three groups instead of four; and the rate shock of 2022 may have hit several groups at once. A strategy that helps in one period and not in the next is what Lecture 1 calls the normal case: an edge of this size can disappear for a decade by chance alone.

## 7. What did not add

**Key message.** Five refinements were tried after the first results. None improved carry reliably: the gains seen on 2006-2022 were small, within noise, or did not repeat on 2013-2026. One check changed how the result should be read: most of carry's return came from markets and months where it agreed with trend.

| Refinement (tried after the first results) | Idea | 2006-2022 | 2013-2026 | Reading |
|---|---|---|---|---|
| **Hedge the common risk** (currencies, commodities): remove the dollar or the commodity market from the baskets, risk-off by half | Long and short baskets that move alike on the main common risk, still tilted to carry | Trend + carry 0.86 → 0.92; difference +0.06, 90% band −0.03 to +0.13 | 0.45 → 0.44 | Noise: the hedged and unhedged versions are 97% correlated |
| **Tilt carry towards cheap markets** (value against its 5-year line, weight ¼ to 1) | Buy carry when it is cheap, not overextended; Jordà and Taylor (2012) find currency carry earns less when the high-rate currency is overvalued, and that conditioning on valuation removes carry's negative skew | Worse at every weight: carry 0.57 → 0.42 → 0.21 → −0.03; drawdowns deeper | Worse at every weight | On our data, carry markets that had fallen kept falling |
| **The best grid rows combined** (6-month change, hedge, 12-month sizing) | Keep the variants with the best drawdowns | Calmar 0.47 → 0.66, worst loss −20.6% → −14.5% | Worse on every measure (Sharpe 0.45 → 0.37) | Fitted to 2006-2022 |
| **Mix the variants** (one of each type, or all eleven) | Spread the risk of a wrong specification | Same Sharpe, drawdown −15% instead of −21% | Slightly worse | Variants are 0.71 to 0.97 correlated: little to diversify |
| **The variants of the signal** (level only, change only, 1- or 6-month change, rank) | Simpler or different signals | 0.28 to 0.45, all below the rule (0.57) | – | Level and change together beat either alone (0.37 and 0.42) |

<sub><b>How to read the table.</b> One row per refinement; Sharpe ratios of trend + carry unless stated, monthly, after costs. "90% band": block bootstrap over 12-month blocks. Every row was found or chosen after seeing the first results, so 2013-2026 is the check that matters. All of them are counted in §6.2. Our calculation.</sub>

Two lessons. **Gains come from different sources, not from different settings.** The four groups diversify each other, and level and change diversify each other (correlation −0.02); variants of one idea mostly do not. Mixing them still buys something small: less dependence on having picked exactly the right specification and parameters, a little protection against model and parameter risk rather than a higher return. And **an intuitive refinement can be tested and rejected**: buying carry on the dip sounds prudent and made carry worse at every step of the grid, the same way in both periods. That is a result, not a failure.

### 7.1 Carry and trend: a second business, or a filter in disguise?

Carry and trend trade some of the same markets: the euro and the yen, the seven commodities, the S&P 500, US Treasuries. Where both hold a position, their positions add up when they agree and cancel when they disagree. On those markets carry acts like a soft carry filter on trend: trend held more when the curve agrees, less when it does not. Is that where carry's money came from?

| Part of carry's return, 2006-2022 | Return a year | Share of carry's return | Sharpe ratio |
|---|---|---|---|
| Same market as trend, same side | +5.3% | 83% | 0.75 |
| Same market as trend, opposite side | −0.5% | −8% | −0.13 |
| Markets or months trend does not hold | +1.6% | 25% | 0.15 |

<sub><b>How to read the table.</b> Carry's monthly return (the rule, four groups) split by market and month according to trend's position at the end of the month before: on the same side, on the opposite side, or none. The three parts add up to carry's return (the rebuild matches it at 0.9997). Our calculation ([results/split.json](results/split.json)).</sub>

Most of carry's return came from the markets trend also trades, in the months when trend held the same side: a short in a commodity whose curve was in contango while its price fell, a long in a currency whose rate was rising while it rose. In the many markets trend never trades, carry earned little (0.15). So on this sample carry worked largely as **an amplifier of trend where the curve agreed**, a carry filter that adds rather than takes away, more than as an independent source of return. The split does not say which signal deserves the credit, since a return earned where both agree belongs to both; but it tempers §1's picture of two unrelated businesses. Their *timing* is unrelated (correlation 0.06), their *profits* are not.

## 8. Summary

### 8.1 Takeaways

1. **A second strategy needs no forecast.** Lecture 28's switches had to know, on the day, when trend would fail, and none passed. A strategy that earns for a different reason helps without that knowledge (§2).
2. **Check a rebuild against the published series early.** It exposed two design flaws, bonds and equities as two US instruments each, that the backtests alone did not show; where our markets match AQR's, our series track theirs (0.69 to 0.79) (§3).
3. **Carry earns little in any one group and much more in four.** Each group's Sharpe ratio is 0.18 to 0.46; together 0.57, because the income of currencies, commodities, bonds and equities is paid for different risks (§4).
4. **Value needs fundamentals.** Measured by price against its past it lost, as AQR's did in this period; built from real yields, purchasing power, the yield gap and inventories it earned a little (0.14) and held trend steady, but did not add to it (§5).
5. **Evidence is weighed, not passed.** Carry beats all of 1,000 random strategies, but counting the 21 versions tried leaves a deflated Sharpe ratio of 0.90. Realistic edges are noisy by nature; they are judged on the probability, the breadth, a reason they persist, and what they add (§6).
6. **Carry's price is in the tail, and its profits lean on trend.** It improves trend on every measure in 2006-2022 at the cost of sudden losses, does not help in 2013-2026, and made most of its money where it agreed with trend (§6, §7).

**From strategies to a portfolio.** Trend, carry and value are now built on the same machinery and judged the same way. Lecture 30 puts them together once, on fixed rules, with the questions this lecture leaves open: how much of each to hold, what to do with a strategy that earns in one period and not the next, and whether value earns a place.

### 8.2 Exercises

1. **Emerging-market carry.** Add the Mexican peso and the South African rand (spot and 3-month rates free on FRED) and the zloty, forint and koruna (Yahoo spot, OECD rates) to the currency group. Fix your expectation first: does carry earn more, and what did 2008 cost?
2. **Carry on the ETFs.** Build carry for the bond and credit funds of Lecture 25 from their distributions (the last regular payment annualised) and for the equity funds from their dividend yields. Rank them in one fixed-income group and in two classes. Which works, and why might the answer depend on the grouping?
3. **Value on more commodities.** The World Bank's free monthly prices cover dozens of commodities from 1960. Measure value on them against their 10-year trend lines. Without tradable returns, what can and cannot be concluded?
4. **Economic trend.** Turn Lecture 28's real-time growth and inflation directions into positions (bonds long when both fall; commodities long when both rise; equities and credit by growth minus inflation). Judge it as this lecture judged carry, and count your tries.
5. **Carry where trend is flat.** §7.1 found most of carry's return where it agreed with trend. Restrict carry to the markets trend does not trade and to the months trend is flat. What is left, and what does that say about combining the two?
6. **Your own construction.** Choose one group and one published construction (Asness, Moskowitz and Pedersen 2013, or Koijen et al. 2018). Write down every choice you must make to rebuild it from free data, make them before looking at results, and report your series' correlation with AQR's.

### 8.3 Reading

- Lecture 1 §5.3-5.4 (overfitting, many small edges), Lecture 26 (the risk horizon), Lecture 27 (the baseline), Lecture 28 (regimes as a switch).
- Asness, C. S., Moskowitz, T. J. and Pedersen, L. H. (2013). Value and momentum everywhere. *Journal of Finance* 68(3), 929-985.
- Koijen, R. S. J., Moskowitz, T. J., Pedersen, L. H. and Vrugt, E. B. (2018). Carry. *Journal of Financial Economics* 127(2), 197-225.
- Davis, J., Dorsten, M., Gillmann, N. and Tsai, J. (2022). Carry momentum. *Financial Analysts Journal* 78(1), 5-38.
- Boons, M. and Porras Prado, M. (2019). Basis-momentum. *Journal of Finance* 74(1), 239-279.
- Gorton, G. B., Hayashi, F. and Rouwenhorst, K. G. (2013). The fundamentals of commodity futures returns. *Review of Finance* 17(1), 35-105.
- Asness, C. S. (2003). Fight the Fed model. *Journal of Portfolio Management* 30(1), 11-24.
- Jordà, Ò. and Taylor, A. M. (2012). The carry trade and fundamentals: nothing to fear but FEER itself. *Journal of International Economics* 88(1), 74-90.
- Bailey, D. H. and López de Prado, M. (2014). The deflated Sharpe ratio: correcting for selection bias, backtest overfitting, and non-normality. *Journal of Portfolio Management* 40(5), 94-107.
- Bailey, D. H., Borwein, J. M., López de Prado, M. and Zhu, Q. J. (2014). Pseudo-mathematics and financial charlatanism: the effects of backtest overfitting on out-of-sample performance. *Notices of the American Mathematical Society* 61(5), 458-471.
- AQR Capital Management, LLC. Value and Momentum Everywhere: Factors, Monthly. AQR Data Library (free).
