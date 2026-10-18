# Lecture 5: What Trend Following Captures

*Systematic Trading: Lecture Notes (MSc) · Oct 18, 2026 · Max Gnesi*

Before building a trend system, it pays to know what a trend system earns. This lecture splits trend profits into two sources, the drift of a market and the persistence of its returns, shows that the second is concentrated in a few episodes, turns both into questions to ask about any market before trading it, and ends with the choice of what to capture. Data: 16 liquid ETFs across equities, bonds, commodities and real estate. Companion notebook: [05_what_trend_following_captures.ipynb](05_what_trend_following_captures.ipynb).

## 1. The question of this lecture

This lecture is about the **market**, not the system: where do the profits of a trend rule come from, and in which markets should we expect them? Lecture 6 then asks how to design a system that captures the part we want.

| | Lecture 5: What Trend Following Captures | Lecture 6: the Map and the Machinery |
|---|---|---|
| Question | Where do trend profits come from, and in which markets? | How do we design a system that captures the part we want? |
| About | The market | The system |
| Key message | Trend profits have two sources, drift and timing; markets differ in how much of each they offer | Design decides what is captured: direction, speed and exits choose between drift and crisis protection |
| Afterwards the reader can | Judge a market before building anything | Read any trend rule as a set of design choices and turn it into positions |

One rule serves throughout as a **measuring instrument**, not as a system to trade: hold a long position in an asset for the next month if its return over the past 12 months was positive, and a short position if it was negative. This is the time-series momentum rule of Moskowitz, Ooi and Pedersen (2012). The results describe one rule on one history of 16 ETFs; they are evidence about these markets, not laws.

## 2. Two sources of trend profits

A trend rule earns from two different things: the **drift** of the asset, which it collects by being long more often than short, and the **timing** of its positions, which pays when returns persist. The two parts can be measured exactly, and they behave very differently.

### 2.1 Drift and timing

With position $`s_t`$ (+1 long, −1 short) and the asset's return $`r_t`$ in month $`t`$, the average return of the rule splits into two parts:

```math
\overline{s\,r} \;=\; \underbrace{\overline{(s-\bar s)(r-\bar r)}}_{\text{timing}} \;+\; \underbrace{\bar s\;\bar r}_{\text{drift}}
```

| Part | Formula | Financial meaning |
|---|---|---|
| Drift | Average position × average return | What the rule earns by leaning long in an asset that rises over time, or short in one that falls; a buy-and-hold investor with the same average exposure would earn it too |
| Timing | Covariance of the position with the return | What the rule earns by being long in the months that turn out good and short in those that turn out bad; it pays only if returns persist |

The split is exact. A six-month toy series shows it:

| Month | 1 | 2 | 3 | 4 | 5 | 6 | Average |
|---|---|---|---|---|---|---|---|
| Position $`s_t`$ | +1 | +1 | +1 | −1 | −1 | +1 | 0.333 |
| Return $`r_t`$ (%) | 2 | 1 | −3 | −2 | 1 | 3 | 0.333 |
| $`s_t r_t`$ (%) | 2 | 1 | −3 | 2 | −1 | 3 | 0.667 |

The rule earns 0.667% a month. The drift part is 0.333 × 0.333 = 0.111%; the timing part is the remaining 0.556%, the covariance of the two rows (notebook §2.1). Moskowitz, Ooi and Pedersen use a decomposition of this kind, following Lo and MacKinlay (1990), and find that positive autocovariance of returns drives most of time-series momentum in futures.

### 2.2 What a trend rule earned on 16 ETFs

**Table 2.1. The 12-month trend rule, split into drift and timing** (% a year; monthly rebalancing; each ETF from its start to September 2026; notebook §2.2)

| ETF | Asset drift | Months long | Trend return | Drift part | Timing part | Long side | Short side |
|---|---|---|---|---|---|---|---|
| SPY | 10.2 | 82% | 10.6 | 6.6 | 4.1 | 10.4 | 0.2 |
| QQQ | 7.9 | 80% | 11.1 | 4.7 | 6.4 | 9.5 | 1.6 |
| IWM | 8.1 | 69% | 3.8 | 3.2 | 0.7 | 6.0 | −2.1 |
| EFA | 7.3 | 67% | 2.3 | 2.5 | −0.2 | 4.8 | −2.5 |
| EEM | 7.9 | 68% | 7.7 | 2.8 | 4.9 | 7.8 | −0.1 |
| XLE | 8.3 | 68% | 7.9 | 3.0 | 4.9 | 8.1 | −0.2 |
| XLF | 5.8 | 66% | 1.9 | 1.8 | 0.1 | 3.8 | −1.9 |
| XLK | 8.5 | 78% | 10.1 | 4.7 | 5.4 | 9.3 | 0.8 |
| XLU | 7.3 | 79% | 6.5 | 4.2 | 2.3 | 6.9 | −0.4 |
| VNQ | 6.1 | 73% | 2.4 | 2.8 | −0.4 | 4.3 | −1.9 |
| AGG | 2.8 | 79% | 2.8 | 1.7 | 1.1 | 2.8 | 0.0 |
| TLT | 3.1 | 64% | 1.4 | 0.9 | 0.5 | 2.2 | −0.9 |
| GLD | 9.8 | 70% | 7.0 | 3.9 | 3.1 | 8.4 | −1.4 |
| SLV | 7.3 | 55% | −0.6 | 0.8 | −1.4 | 3.3 | −4.0 |
| GDX | 5.0 | 55% | 2.6 | 0.5 | 2.1 | 3.8 | −1.2 |
| USO | −5.3 | 48% | 7.6 | 0.2 | 7.4 | 1.0 | 6.6 |
| **Median** | 7.3 | 69% | **5.2** | **2.8** | **2.2** | 5.4 | **−0.7** |

- **Both sources matter, about equally.** Of the median 5.2% a year, 2.8 points come from drift and 2.2 from timing ([chart D.1](#d1-drift-and-timing-by-etf-22)).
- **Where an asset rises steadily, drift dominates.** SPY earns 6.6 points from drift: being long 82% of the time in an asset that rose 10% a year.
- **Where an asset falls, timing does the work.** USO's drift was −5.3% a year, yet the rule earned 7.6%, almost all of it timing: it was short through oil's long declines.
- **Timing can also be negative.** For SLV, EFA and VNQ, trends reversed often enough that the rule's positions lined up with the wrong months.

### 2.3 The long side and the short side live in different markets

The last two columns of Table 2.1 split the same return by the months spent long and short. The long side earns 5.4% a year at the median; the short side loses 0.7%. Being short an asset that drifts upwards costs the drift, so the short side pays only where downtrends persist: QQQ (+1.6), XLK (+0.8) and USO (+6.6).

**Table 2.2. Next month after an up-trend and after a down-trend** (% a year; notebook §2.3)

| ETF | Mean return after an up-trend | Mean return after a down-trend | Volatility after an up-trend | Volatility after a down-trend |
|---|---|---|---|---|
| SPY | 12.7 | −1.2 | 12.9 | 22.0 |
| QQQ | 11.9 | −8.1 | 18.7 | 35.5 |
| IWM | 8.6 | 7.0 | 16.2 | 27.0 |
| USO | 2.1 | −12.7 | 34.7 | 46.5 |
| **Median of 16** | 7.9 | 2.2 | 17.2 | 27.2 |

After a 12-month downtrend, volatility is about 60% higher than after an uptrend. The short side therefore lives in turbulent markets, where large moves in both directions are common: it pays when the decline continues, as for QQQ after 2000 or oil after 2014, and loses when the market rebounds, as IWM's positive returns after downtrends show. Lecture 6 shows what this means for design: whether a system holds short positions at all decides whether it collects drift, protection, or both.

### 2.4 Timing comes in episodes

Linear autocorrelation of monthly returns is close to zero: summed over twelve lags, its median across the 16 ETFs is −0.03. Yet the rule earns 2.2% a year from timing. The two fit together because the persistence is not spread evenly over time; it is concentrated in a few episodes.

**Table 2.3. Where the timing part is earned** (% a year, median across 16 ETFs; notebook §2.4)

| Months | Timing contribution |
|---|---|
| All months | 2.2 |
| The 10% of months with the largest moves | **2.0** |
| The other 90% | **0.1** |

Almost all of the timing profit comes from one month in ten ([chart D.2](#d2-timing-by-size-of-the-months-move-24)). In ordinary months the rule's positions earn nothing from timing; in the largest months, being on the right side of a persistent move pays. A linear autocorrelation, which weights every month equally, averages these episodes away.

The literature points to the mechanisms behind such episodes.

| Mechanism | What happens | Evidence |
|---|---|---|
| Slow diffusion of information | News reaches investors gradually; prices underreact, then traders who follow momentum push them past fair value | Hong and Stein (1999) |
| Forced selling | Investors who must sell, such as funds facing large outflows, push prices down together; the pressure lasts about two quarters before reversing | Coval and Stafford (2007): abnormal returns of −13% to −18% around fire sales, reversed over the following three quarters |
| Liquidity spirals | Falling prices raise margins and cut traders' capital, which reduces liquidity and pushes prices further | Brunnermeier and Pedersen (2009) |
| Hedging flows | Dealers short options and leveraged ETFs must buy after rises and sell after falls, pushing prices in the direction they are already moving | Baltussen, Da, Lammers and Martens (2021): intraday momentum in more than 60 futures |

**Over days, a shock overshoots.** The persistence that a monthly rule earns from is not the immediate reaction to a shock.

**Table 2.4. The week after a large weekly move** (weekly returns standardised by trailing 52-week volatility; median across 16 ETFs; notebook §2.4)

| | After a week beyond 2 standard deviations | After a normal week |
|---|---|---|
| Next week has the same sign | 46% | 49% |
| Next week's return after a large fall | +0.3% | — |

A large weekly move is slightly more likely to be followed by a move the other way, and a large fall by a small rebound: the first days overshoot. What persists is the regime the shock starts, which can last for months, as the fire sales above did. A monthly trend rule is positioned for that persistence, not for the first shock.

### 2.5 Trend or reversion: patterns, not laws

Trend following and mean reversion use the same estimate, the past return, and act on it in opposite directions (Bruder, Dao, Richard and Roncalli, 2011). The literature documents statistical patterns at different horizons, but each was found in particular markets and periods:

| Horizon | Pattern documented | Where it was found |
|---|---|---|
| A week to a month | Reversal | Individual US stocks (Jegadeesh, 1990; Lehmann, 1990) |
| Three to twelve months | Continuation | US stocks, ranked against each other (Jegadeesh and Titman, 1993); 58 futures markets, each against its own past (Moskowitz, Ooi and Pedersen, 2012) |
| Three to five years | Reversal | US stocks (De Bondt and Thaler, 1985); partial reversal of time-series momentum beyond a year in futures (Moskowitz, Ooi and Pedersen) |

These are tendencies, not rules that every market obeys. Our own weekly data show how much they vary (Table 2.4, notebook §2.4): after a large weekly move, the next week had the same sign 46% of the time at the median, a mild tendency to reverse, but 63% of the time for oil (USO) and 56% for silver (SLV), where large moves tended to continue.

Which behaviour to exploit is therefore a choice, not a fact of the market. It is made after understanding the market (§3) and deciding what to capture (§4).

**Watch out for** reading the absence of autocorrelation as the absence of trends. Persistence that appears in episodes, at inflection points and in cascades, is invisible to an average over all months and is exactly what a trend rule harvests. Equally, do not credit timing with what is drift: in a rising market, a rule that is mostly long earns the drift whatever its timing.

## 3. Understanding the market first: five questions

Before deciding what to capture, understand the market. Five questions do most of the work. For each, the table below says why it matters for a trend rule; the subsections measure it on the 16 ETFs and say what the literature documents. Where only practitioner experience exists, the text says so.

| Question | Why it matters for a trend rule |
|---|---|
| 1. Is there a drift? | It feeds the long side, and it is what the short side pays (§2.2–§2.3) |
| 2. Which frictions create persistence? | They feed the timing part, which is earned in episodes (§2.4) |
| 3. How fast can it fall, and how liquid is it? | A rule on daily bars cannot act inside a gap; stops slip when liquidity disappears |
| 4. How mature is the market, and is the edge decaying? | Patterns that are learned and crowded tend to fade |
| 5. How much intervention is there? | Policy can cut moves short, or create them |

### 3.1 Is there a drift?

**Table 3.1. Average annual return and how precisely it is known** (log returns; standard error = annual volatility / √years; notebook §3.1)

| ETF | Years | Drift (% a year) | Standard error | t-statistic |
|---|---|---|---|---|
| SPY | 33.7 | 10.3 | 2.6 | 4.0 |
| AGG | 23.0 | 2.8 | 0.9 | 3.1 |
| GLD | 21.8 | 9.8 | 3.7 | 2.7 |
| SLV | 20.4 | 6.7 | 7.2 | 0.9 |
| USO | 20.4 | −6.6 | 8.9 | −0.7 |
| **Median of 16** | 24.6 | 6.9 | 4.2 | 2.0 |

Drift is the least precisely measured quantity in this lecture. After a quarter of a century, the median t-statistic is about 2, and for silver, gold miners and oil the drift cannot be told apart from zero. Whether a market has a drift therefore has to come from economics as much as from data: equities and bonds pay a premium for bearing risk; a commodity has no such premium of its own, and an oil fund that rolls futures can drift downwards for reasons unrelated to the price of oil.

### 3.2 Which frictions create persistence?

The timing part of §2 is earned in episodes, and the episodes have causes. The question for a given market is which of them operate there:

| Friction | Where it is strong |
|---|---|
| Forced selling: margin calls, redemptions, liquidations | Markets with high leverage or fragile funding (§2.4: Coval and Stafford; Brunnermeier and Pedersen) |
| Hedging flows | Markets with large option positions or leveraged products (§2.4: Baltussen et al.) |
| Slow diffusion of information | Markets where news is complex or investors are dispersed (§2.4: Hong and Stein) |
| Rebalancing waves | Markets held by large investors who rebalance on rules or schedules (practitioner experience) |

On the 16 ETFs, the timing part ranges from −1.4% a year (silver) to 7.4% (oil), and volatility after a downtrend is about 60% higher than after an uptrend (Tables 2.1–2.2): the frictions differ by market, and they show up when markets are stressed.

### 3.3 How fast can it fall, and how liquid is it?

**Table 3.2. Worst moves and what happens while the market is closed** (daily data; worst day in units of the trailing 252-day volatility; overnight share = variance of the open-to-previous-close gap as a share of daily variance; notebook §3.3)

| ETF | Worst day | Worst overnight gap | Worst day, in standard deviations | Days beyond 5 sd, per 1,000 | Overnight share of variance |
|---|---|---|---|---|---|
| SPY | −11.6% (16 Mar 2020) | −11.0% | −9.2 | 2.8 | 33% |
| EFA | −11.8% (29 Sep 2008) | −12.7% | −11.2 | 2.6 | 58% |
| USO | −29.2% (9 Mar 2020) | −24.7% | −14.0 | 1.8 | 50% |
| SLV | −33.6% (30 Jan 2026) | −16.7% | −14.6 | 3.3 | 56% |
| AGG | −7.1% (10 Oct 2008) | −3.9% | −17.1 | 2.0 | 44% |
| **Median of 16** | −14.6% | −11.9% | −9.8 | 2.2 | 36% |

- **The worst moves arrive when the market is closed.** The median worst overnight gap, −11.9%, is close to the median worst day, −14.6%. A rule on daily bars, or a stop order, cannot act inside a gap.
- **Extremes are far more common than a normal distribution allows.** Days beyond 5 standard deviations occur about twice in every 1,000 days; a normal distribution expects one in about 1.7 million.
- **Where the underlying trades around the clock, much of the risk is overnight.** For international equities, gold, silver and oil, more than half the variance arrives while the US fund is closed, as Lecture 3 found for GLD.

Cascades can be fast. On 6 May 2010, US equity prices fell and recovered within minutes, a sequence reconstructed by the staffs of the CFTC and SEC (2010). On 10–11 October 2025, more than USD 19 billion of leveraged crypto positions were liquidated, about 90% of them long, as Bitcoin fell 14% from its high within hours (industry reports, CoinGecko and CoinShares). Flash crashes can happen in any market; how far they go depends on liquidity and leverage. A trend system has to be built for the gaps of its market, not for the average day.

### 3.4 How mature is the market, and is the edge decaying?

**Table 3.3. The 12-month rule by period** (% a year; median across the ETFs available in each period; notebook §3.4)

| Period | ETFs | Trend return | Drift part | Timing part | Long side | Short side |
|---|---|---|---|---|---|---|
| 2000–2009 | 11 | 9.1 | 1.3 | **9.2** | 5.2 | 3.3 |
| 2010–2019 | 16 | 2.1 | 2.3 | **−2.5** | 3.2 | −1.9 |
| 2020–2026 | 16 | 6.0 | 4.1 | **−0.3** | 9.7 | −3.1 |

On these ETFs, the timing part was large in the 2000s and has been negative since; what the rule earned after 2010 came from drift, through the long side. The panel changes over time, from 11 ETFs to 16, so the comparison is indicative.

The literature documents such decay. In foreign exchange, trend rules earned genuine excess returns in the 1970s and 1980s, after the end of fixed exchange rates, and had lost them by the early 1990s (Neely, Weller and Ulrich, 2009), a pattern consistent with Lo's (2004) adaptive markets hypothesis: opportunities attract traders, and traders erode them. In US equities, the returns of 97 published predictors fell by 58% after publication (McLean and Pontiff, 2016). New markets, where prices are still being discovered, show strong time-series momentum, as cryptocurrencies did (Liu and Tsyvinski, 2021). Practitioners add that novel markets tend to trend more than mature ones; the evidence above is consistent with that view.

### 3.5 How much intervention is there?

**Table 3.4. Zero rates against the rest** (months with the 3-month US Treasury bill below 0.25%, roughly December 2008 to late 2015 and March 2020 to early 2022; 2000–2026; % a year, median across ETFs; notebook §3.5)

| Months | Number (SPY) | Trend return | Drift part | Timing part | Long side | Short side |
|---|---|---|---|---|---|---|
| Zero rates | 108 | 3.3 | 2.9 | **−2.7** | 7.4 | **−4.1** |
| Other months | 213 | 7.2 | 1.2 | **6.2** | 5.0 | **2.1** |

When policy rates were at zero, the timing part was negative and the short side lost; in other months both were positive. This is consistent with a view common among practitioners: when central banks lean against every sell-off, downtrends are cut short, and the short side of a trend system suffers.

The evidence is not conclusive. Zero rates coincide with the 2010s (Table 3.3), so the table cannot separate intervention from other changes of that decade. Baltas and Kosowski attribute the weaker trend-following returns after 2008 to higher correlations across markets. And intervention can also create trends: LeBaron (1999) found that most of the profits of trend rules in foreign exchange came on days when the Federal Reserve intervened, when policy leaned against a move that then continued.

**Watch out for** treating a measured pattern as permanent. Every table in this section describes a history; before relying on a pattern, ask whether its cause is still there.

## 4. What to capture: choose what should last

Understanding the market says what has been available. Choosing what to capture is a judgement about what will remain: which sources are stable, which will decay least, and how the market is likely to behave over the medium to long term, given crowding, investor behaviour and the actions of policymakers.

| Criterion | Question to ask | Example from §2–§3 |
|---|---|---|
| A durable mechanism | Is there a reason for the pattern that will outlast its discovery? | Drift in equities is compensation for risk; forced selling and hedging flows follow from leverage and option positions that do not disappear when the pattern is published |
| Decay and crowding | How widely is it known and traded? | FX trend profits faded by the early 1990s; published equity predictors lost 58%; the timing part of our trend rule turned negative after 2009 |
| The secular regime | How will policy, market structure and investor behaviour evolve? | Zero rates coincided with a losing short side; markets that trade around the clock carry more of their risk overnight |

The choice between trend and reversion, and within trend between drift and timing, follows from this judgement and from the risk profile the designer is willing to carry:

| Question | Trend | Reversion |
|---|---|---|
| What do we want to capture? | The drift, and persistence in episodes: cascades, rebalancing waves, slow diffusion of news (§2) | The overshoot after shocks and the pull back towards a level |
| Which risk profile do we accept? | Many small losses in choppy markets, a few large gains when a move persists: the profile of a long option, as Fung and Hsieh (2001) and Moskowitz, Ooi and Pedersen (2012) document | Many small gains while prices oscillate, occasional large losses when a move persists: the mirror image, the profile of a short option |

The same tools serve either choice: a band around a moving average can be traded as a breakout or as a fade; a breakout that fails is a reversion signal; the Kalman filter that tracks a trend in Lecture 4 can track the spread of a pair in mean-reversion trading. Some tools suit one side better, breakouts for persistence and stretch oscillators for reversion, but the choice of side follows from what the designer wants to capture and which risks to carry, not from the tool. Lecture 6 takes the next step: within trend following, design choices such as direction and speed decide which part of the trend profit a system captures.

**Watch out for** choosing what to capture from the backtest alone. The sources that looked best in the past are often the ones most exposed to decay and crowding; the mechanism, not the history, is the better guide to what will last.

## 5. The evidence, and who uses trend

*To follow:* the long-run record and its caveats; CTAs and their history; trend in other hedge-fund strategies; newer forms.

## Appendix: charts

From the companion notebook, [05_what_trend_following_captures.ipynb](05_what_trend_following_captures.ipynb). Its sections carry the lecture's numbers.

### D.1 Drift and timing by ETF (§2.2)

![The 12-month trend rule's return on 16 ETFs, split into drift and timing](figures/05_01_drift_timing.png)

Each bar splits the trend rule's return into the drift part (blue) and the timing part (orange); the diamond marks the total. Equity indices earn from both. Oil (USO) earns almost entirely from timing; silver (SLV) loses on timing.

### D.2 Timing by size of the month's move (§2.4)

![Median timing contribution by decile of the month's absolute return](figures/05_02_timing_episodes.png)

The timing contribution of each tenth of months, from the calmest to the largest moves, median across the 16 ETFs. The largest tenth contributes 2.1% a year; the others are close to zero, with the ninth slightly negative.

## References (so far)

- Baltas, N. and Kosowski, R. Demystifying time-series momentum strategies: volatility estimators, trading rules and pairwise correlations. Working paper, SSRN 2140091. — correlations and trend returns after 2008 (§3.5).
- Baltussen, G., Da, Z., Lammers, S. and Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics* 142(1), 377–403. — hedging flows (§2.4).
- Brunnermeier, M. and Pedersen, L.H. (2009). Market liquidity and funding liquidity. *Review of Financial Studies* 22(6), 2201–2238. — liquidity spirals (§2.4).
- Bruder, B., Dao, T.-L., Richard, J.-C. and Roncalli, T. (2011). *Trend Filtering Methods for Momentum Strategies.* Lyxor White Paper. — trend following and mean reversion from one estimate (§2.5).
- CFTC and SEC (2010). *Findings Regarding the Market Events of May 6, 2010.* Report of the staffs of the CFTC and SEC, 30 September 2010. — the flash crash (§3.3).
- Coval, J. and Stafford, E. (2007). Asset fire sales (and purchases) in equity markets. *Journal of Financial Economics* 86(2), 479–512. — forced selling and its reversal (§2.4).
- De Bondt, W. and Thaler, R. (1985). Does the stock market overreact? *Journal of Finance* 40(3), 793–805. — long-term reversal (§2.5).
- Fung, W. and Hsieh, D. (2001). The risk in hedge fund strategies: theory and evidence from trend followers. *Review of Financial Studies* 14(2), 313–341. — trend following as a long-option payoff (§4).
- Hong, H. and Stein, J. (1999). A unified theory of underreaction, momentum trading, and overreaction in asset markets. *Journal of Finance* 54(6), 2143–2184. — slow diffusion (§2.4).
- Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of Finance* 45(3), 881–898. — short-term reversal (§2.5).
- Jegadeesh, N. and Titman, S. (1993). Returns to buying winners and selling losers: implications for stock market efficiency. *Journal of Finance* 48(1), 65–91. — medium-term continuation (§2.5).
- LeBaron, B. (1999). Technical trading rule profitability and foreign exchange intervention. *Journal of International Economics* 49(1), 125–143. — trend profits on intervention days (§3.5).
- Lehmann, B. (1990). Fads, martingales, and market efficiency. *Quarterly Journal of Economics* 105(1), 1–28. — short-term reversal (§2.5).
- Liu, Y. and Tsyvinski, A. (2021). Risks and returns of cryptocurrency. *Review of Financial Studies* 34(6), 2689–2727. — time-series momentum in a new market (§3.4).
- Lo, A. (2004). The adaptive markets hypothesis: market efficiency from an evolutionary perspective. *Journal of Portfolio Management* 30, 15–29. — opportunities that attract traders and fade (§3.4).
- Lo, A. and MacKinlay, A.C. (1990). When are contrarian profits due to stock market overreaction? *Review of Financial Studies* 3(2), 175–205. — the decomposition of strategy profits (§2.1).
- McLean, R.D. and Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance* 71(1), 5–32. — decay after publication (§3.4, §4).
- Moskowitz, T., Ooi, Y.H. and Pedersen, L.H. (2012). Time series momentum. *Journal of Financial Economics* 104(2), 228–250. — the rule, the decomposition, persistence and reversal (§1, §2.1, §2.5).
- Neely, C., Weller, P. and Ulrich, J. (2009). The adaptive markets hypothesis: evidence from the foreign exchange market. *Journal of Financial and Quantitative Analysis* 44(2), 467–488. — trend profits in FX and their decay (§3.4).
