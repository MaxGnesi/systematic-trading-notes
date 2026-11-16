# Lecture 29: Carry and Value

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 16, 2026 · Max Gnesi*

Lecture 28 tried to avoid trend's bad regimes by switching trend off, and no switch passed the test fixed in advance. This lecture takes the other answer to the same problem: hold, next to trend, strategies that earn for different reasons, so that they tend to earn when trend does not, without anyone forecasting the regime. The two best-documented candidates across asset classes are **carry**, what a position earns if prices stand still, and **value**, buying what is cheap against its own past. Both are built across four groups, currencies, commodities, government bonds and equity indices, and judged by what they add to trend. Where a published version exists, ours is checked against it, and every difference is shown with what it costs in agreement. The plan was fixed before any result was computed, and every change made after seeing results is dated and labelled ([results/hypotheses.md](results/hypotheses.md)).

## 1. A second business next to trend

| § | Topic | Question |
|---|---|---|
| 1 | A second business next to trend | What does carry add to trend, in one chart? |
| 2 | Why after Lecture 28 | Why hold another strategy rather than switch trend off? |
| 3 | The published versions and ours | How does AQR build carry and value, and where do we differ? |
| 4 | Carry | What does each group earn, and how is the signal built? |
| 5 | Value | Why is value weak in this period? |
| 6 | Results | Does carry beat luck, and what does it cost in crashes? |
| 7 | What did not add | Which refinements failed, and what does that teach? |
| 8 | Summary | Takeaways, exercises, reading |

The lecture's central result fits in one chart.

![Carry next to trend](figures/29_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> x: time, January 2007 to October 2022, monthly (the capstone futures run out in December 2022); y: the value of 100 invested, excess return over cash, after costs. Black: trend, Lecture 27's baseline portfolio **across all its markets** (not trend on the carry markets). Dotted orange: carry alone, currencies, commodities, government bonds and equity indices together (§4). Blue: trend and carry at equal risk, the total scaled on its past to trend's risk. At the right: each line's Sharpe ratio and compound return a year. Our calculation ([results/key.json](results/key.json)).</sub>

Carry alone earned about what trend did (Sharpe ratio 0.59 against 0.67), but at different times: the two are almost uncorrelated (0.06). Held together at the same total risk, they earned more than either (0.86, 9.7% a year against 6.7%), with a worst loss about as deep as trend's alone (−20.6% against −19.3%). That is the whole case for a second strategy: not a better forecast, but a different source of return. The rest of the lecture asks whether the result is real (it beats all of 1,000 random strategies, §6), what it costs (carry adds sudden losses, §6), where it fails (the ETF years 2013-2026, §6), and which refinements did not help (§7). Value, the second candidate, did not earn in this period (§5).

## 2. Why after Lecture 28: a switch against a second business

Lecture 28 and this lecture answer the same problem, that trend loses money in some regimes, in two ways.

| | Switching trend (Lecture 28) | A second strategy (this lecture) |
|---|---|---|
| What changes | Trend is turned on and off | Carry and value are held next to trend, always in |
| What it needs | A forecast, on the day, of when trend will do badly | A different reason to earn; no forecast |
| Idle capital | Stays idle: a switch can only take away | None: every strategy is always in |
| Judged against | Random switching with the same time in the market | Random strategies on the same markets, added to trend the same way |
| Result on our data | No switch passed; the strongest pattern ran against the plan | Carry passes; value does not |

*Analogy (labelled):* a fisherman can stay in port when a storm is forecast, or also own an umbrella shop. The shop earns in storms without anyone forecasting them. A switch needs the forecast; a second business needs only that its customers come for a different reason.

Why carry and value, rather than strategies built from Lecture 28's regimes? They are the two cross-asset styles with the longest published record next to trend (momentum): Asness, Moskowitz and Pedersen (2013) for value and momentum, Koijen, Moskowitz, Pedersen and Vrugt (2018) for carry. Their returns come from different sources. Trend earns when prices keep moving; carry earns the income of a position while prices stand still; value earns when prices return towards a long-run level. A strategy that earns for a different reason is the "many small edges" of Lecture 1 §5.4 in practice.

Lecture 28's regimes are not thrown away: they are where carry and value are judged (§6), above all in the regimes where trend lost.

## 3. The published versions and ours

Carry and value have published constructions. Rebuilding them from free data forces choices, and each choice is a chance to differ from the literature, by necessity or by design. This section shows the published construction, ours, the reason for each difference, and the evidence of what it costs: the correlation of our series with AQR's published one, month by month, 2006 to October 2022. The pattern of the table, not its entries, is the point: a reader building a version of their own will face the same kinds of choices.

**The published series.** AQR publishes monthly returns of the value and momentum factors of Asness, Moskowitz and Pedersen (2013), by asset group, free in its data library ("Value and Momentum Everywhere: Factors, Monthly", AQR Capital Management, LLC). They are paper portfolios before costs, on more markets than ours. AQR publishes no carry factor in the free library; Koijen et al. (2018) describe the construction.

| Group | Published construction | Ours | Why we differ | Our value against AQR's (correlation) |
|---|---|---|---|---|
| **Currencies** | Value: 5-year change in the real exchange rate; 10 developed currencies. Carry: the interest-rate gap from forward rates | 9 currencies against the dollar, returns from spot rates plus the 3-month rate gap (FRED). Value: BIS real effective exchange rates. Carry: the rate gap | Free data; the same idea | **0.78** |
| **Commodities** | Value: price today against its average 4.5 to 5.5 years ago (5-year reversal); 27 commodities. Carry: slope of the futures curve | 7 commodities (capstone futures). Value: the same on the front contract's price. Carry: front against the contract 12 months later | No free clean futures for more commodities; 12 months removes the seasons | 0.53 |
| **Government bonds** | Value: 5-year change in 10-year yields; 10 countries, futures. Carry: term spread plus roll-down | 9 countries, returns built from each central bank's 10-year yield (no free bond futures). Carry: the term spread | No free bond futures; month-end yields from nine central banks | 0.69 |
| **Equity indices** | Value: book-to-market; 18 countries, futures. Carry: dividend yield minus the rate, from the futures | 15 country funds, hedged into dollars. Value: price against its past. Carry: the S&P 500's **earnings yield** minus the real bill rate; elsewhere the dividend yield minus the real cash rate | Book values are not free per country; earnings, not dividends, are what a holder accrues (buybacks), but free earnings exist only for the US | 0.46 |
| **Across groups** | Ranked within each group, equal risk across groups | The same, but weighted by a carry *score* rather than a rank (§4), and value against a 10-year trend line (§5) | Our design choices, tested against the published versions (§5, §7) | – |

<sub><b>How to read the table.</b> One row per group. "Published": Asness, Moskowitz and Pedersen (2013) for value, Koijen et al. (2018) for carry. "Ours": what this lecture builds from free data. The last column is the correlation of the monthly returns of our value strategy, built with the published construction, with AQR's published value factor for the same group, 2006 to October 2022. Our calculation.</sub>

The agreement follows the universe. Where ours is nearly the same as AQR's, currencies, the two series move together (0.78); where we hold a fraction of the markets, commodities, or measure value differently, equity indices, agreement falls. Two of our first versions agreed far worse, and the comparison is what exposed them:

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

**Key message.** Value buys what is cheap against its own past and sells what is dear, betting that prices return towards a long-run level. In this period it did not earn, on our data or on AQR's. The lessons are about measurement (value must be measured on a price without income, against a trend rather than a flat average) and about patience: a slow strategy needs far more years than we have to show whether it works.

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
3. **Breadth.** Value is a cross-sectional style, and ranking works better with more markets. Where our universe matches AQR's (currencies, 9 of their 10) our value tracks theirs closely (0.78); with 7 commodities against their 27, much of what earned for AQR is missing.

*Our reading (labelled).* Value is not shown to work here, and not shown not to work. Its role in a portfolio is the one the correlation suggests, a diversifier of trend, but on this sample it did not earn enough to pay for its place. Whether it belongs in Lecture 30's final portfolio is a question for that lecture, to be decided before looking at data it was not tested on.

One more observation links value to carry. In currencies and commodities the two point in opposite directions: the high-carry markets tend to be the dear ones (the signals' rank correlation is −0.12 and −0.24; the strategies' returns −0.31 and −0.43). A currency that pays a high rate attracts money and appreciates; a commodity in backwardation has usually just risen. §7 asks whether that can be used.

## 6. Results

**Key message.** Carry passes every test of luck we set, but less comfortably once the search that chose it is counted: about 90% likely to be more than luck, not the near-certainty that a single comparison suggests. It adds to trend on every measure in 2006-2022, at a price, sudden losses, and it did not help in 2013-2026.

### 6.1 Against luck

The rule was compared with 1,000 random strategies on the same markets, each market's position switching at random with the same average holding period, built by the same machinery and added to trend in the same way (futures period, monthly).

| | Carry | Random: median | Random: 95th percentile | Share of random beaten |
|---|---|---|---|---|
| Carry alone | 0.57 | −0.11 | 0.28 | 100% |
| Trend + carry | 0.86 | 0.36 | 0.65 | 100% |
| Value alone | −0.09 | −0.08 | 0.34 | 48% |

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

**How much evidence to expect.** About 90% is good evidence, and a stricter bar would mostly measure the length of the sample. To be 95% sure that a Sharpe ratio is above zero takes about $`(1.65/	ext{SR})^2`$ years:

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
