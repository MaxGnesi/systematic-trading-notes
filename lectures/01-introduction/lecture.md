# Lecture 1: Introduction to Systematic Trading

*Systematic Trading: Lecture Notes (MSc) · Oct 9, 2026 · Max Gnesi*

## 1. Introduction and definition

Systematic trading is an investment process in which every decision, from data to executed order, follows explicit rules that can be written down, tested on history, and repeated without discretion.

Two complementary definitions.

**The architecture view.** Systematic trading is an end-to-end information-processing architecture that ingests multi-structured datasets, extracts predictive signals, maps those signals into optimal capital allocations subject to constraints, and systematically executes portfolio adjustments while managing dynamic risk parameters. In short, it is a process that governs how capital is deployed and allocated with minimal human intervention.

**The economics view.** Systematic trading translates economic understanding into algorithms. If a fundamental investment principle can be expressed as clear criteria, it can be backtested across long histories and many countries, and capital allocation can then be automated around lasting economic mechanics. This is the approach associated with macro firms such as Bridgewater, and it is the opposite of black-box prediction.

The first definition says how the machine is built; the second says why it should make money. A strategy needs both: a sound architecture with no economic reason behind it is a well-engineered guess. In compact form, the first view is a function from information to positions:

$$
w_t = f(\mathcal{I}_t;\,\theta), \qquad \mathcal{I}_t = \{\text{data available at time } t\}
$$

Here $w_t$ is the target portfolio, $f$ is the rule set, and $\theta$ are parameters estimated or chosen in research. Two properties matter for everything that follows: $f$ uses only information available at $t$, and the same inputs always produce the same outputs.

### 1.1 A spectrum, not a binary

Most real firms sit between the extremes. What differs is where human judgment enters.

| Style | Who decides | Where the human sits |
|---|---|---|
| Discretionary | Portfolio manager | Every decision |
| Quantamental | Manager, informed by models | Final decision and sizing |
| Systematic, human-supervised | Model | Research, risk overrides, model changes |
| Fully automated | Model | Research only |

The boundary is blurrier than the table suggests. A discretionary manager typically uses screens, risk models and position limits; a systematic fund still relies on people to choose data, set parameters and decide when to switch a model off. Discretionary trading can itself be highly structured: a macro manager who writes down their principles, sizes positions from a fixed risk budget and checks every trade against a rulebook is closer to a systematic process than the label suggests, and some firms deliberately blend the two by turning an economic view into explicit rules. The practical question is how much of the decision is rule-based, not whether any of it is. The trade-offs are:

| Dimension | Discretionary | Systematic |
|---|---|---|
| Consistency | A person can read the same data differently over time or bring in extra information | Same inputs give the same decisions |
| Breadth | Limited by what one team can follow | Many markets and signals monitored at once |
| Novel events | Can reason about situations never seen before | Only as good as what the model has seen; needs human override |
| Cost per decision | Slower and more expensive | Cheap once built, but costly to build and maintain |
| Transparency | Reasoning can be hard to audit | Rules can be audited and tested on history |
| Main risks | Behavioural bias, key-person dependence | Overfitting, crowding, model and data errors |

### 1.2 What the approach removes, and what it does not

The usual claim is that systematic trading removes emotion and bias from execution. That is true of day-to-day decisions: a model does not panic after a drawdown or hold a loser to avoid regret.

The bias does not disappear, though. It moves upstream into research, starting with which hypotheses get tested at all: researchers tend to test ideas they already believe in, or ideas they test because everyone else does. It continues through the choice of data and sample period, the model, its parameters, how far to trust optimised results over simpler ones, and the decision to switch a model off. A backtest tuned until it looked good embeds the researcher's bias, and it does so invisibly.

A short checklist, kept in mind while developing any systematic model:

- [ ] **Hypothesis.** Is there an economic reason to expect this to work, written down before testing? Am I testing it because I believe it, or because others do?
- [ ] **Data.** Is it point-in-time and free of survivorship bias? Was the sample period fixed before seeing results?
- [ ] **Model and parameters.** How many variants did I try? Would a simpler version do almost as well?
- [ ] **Robustness.** Does performance survive small parameter changes, other markets and data the model has never seen?
- [ ] **Switching off.** Are the rules for scaling down or stopping the model set in advance?

Much of this course is about controlling these risks; §3.1 and §5 return to them in detail.

### 1.3 Why it matters

The approach offers three practical advantages: breadth (many markets and signals monitored at once), discipline (consistent behaviour through stress), and testability (a claim about edge can be checked against data). It also has costs: model risk, crowding, and the fact that a rule tested on the past can fail when the market structure changes.

## 2. The systematic pipeline

A systematic strategy is a chain of five stages, each with its own inputs, outputs and failure modes, and each fed back by what the market actually did.

> **Pipeline: 5 stages, 1 feedback loop.** The loop from execution back to data lets a team detect decay; the shaded zone marks the two stages optimised jointly (allocation and risk — see §2.2).

### 2.1 The five stages

- **Data.** Ingest, clean and timestamp market, fundamental, macro and alternative data. Errors here (survivorship bias, look-ahead, bad ticks) propagate to everything downstream.
- **Signal generation.** Convert data into a forecast of return or relative value, usually normalised to a bounded score such as $s_{i,t} \in [-1, +1]$ for asset $i$.
- **Portfolio construction and allocation.** Map signals to target positions, balancing expected return, risk, factor exposures, leverage and transaction costs.
- **Risk management.** Enforce constraints: volatility targets, position and sector limits, drawdown rules, liquidity buffers.
- **Execution.** Route orders with execution algorithms (e.g. TWAP, VWAP, smart order routing) to minimise slippage and market impact.

### 2.2 Allocation and risk are one problem

Presenting risk management as a stage after allocation is a teaching simplification. In practice the two are solved together. A common formulation maximises expected return net of risk and cost:

$$
\max_{w}\; \mu^{\top} w \;-\; \frac{\lambda}{2}\, w^{\top}\Sigma\, w \;-\; c(w - w_{t-1})
$$

where $\mu$ is the vector of signal-based forecasts, $\Sigma$ the covariance matrix, $\lambda$ the risk aversion, and $c(\cdot)$ the transaction-cost penalty on the trade from the previous holdings $w_{t-1}$. Constraints on leverage, concentration or drawdown enter as additional restrictions on $w$.

The simplest example is volatility targeting, which scales each position so that it contributes a chosen amount of risk:

$$
w_{i,t} = s_{i,t}\cdot\frac{\sigma^{*}}{\hat{\sigma}_{i,t}}
$$

with $\sigma^{*}$ the target volatility and the denominator a forecast of asset $i$'s volatility. Risk control is therefore built into position sizing, not bolted on at the end.

> **Example: driving on ice.** Think of volatility targeting as driving to the conditions. On a dry road you hold a steady speed; when the road turns icy you slow down, so the risk of a crash stays about the same. The strategy does the same: when markets become more volatile it shrinks positions, so the portfolio's risk stays near its target.

### 2.3 The feedback loop

The pipeline is not a one-way street. Realised fills, slippage and P&L attribution flow back into research: they show whether costs were underestimated, whether a signal has decayed, and whether risk limits bind too often. A strategy without this loop degrades silently.

## 3. Data in systematic trading

The value of a dataset depends on how much unique information it holds and how quickly that information is priced in. Cheap, widely used data is rarely a source of edge on its own; scarce, hard-to-process data tends to be, until others catch up.

| Category | What it contains | Typical strategies | Edge decay |
|---|---|---|---|
| Market and microstructure | L1/L2/L3 order books, tick data, options surface, dark pool prints, repo rates | High-frequency trading, statistical arbitrage, short-term momentum | Fast; widely available |
| Fundamental and macro | Earnings quality, balance sheets, supply chain links, CPI, central bank balance sheets | Systematic equity long/short, systematic macro, factor investing | Slow; widely available |
| Alternative | Satellite imagery, credit card aggregators, web traffic, geolocation and foot traffic | Information edge ahead of official corporate filings or macro releases | Medium; erodes as adoption spreads |
| Unstructured and NLP | Earnings call transcripts, regulatory filings (10-K, 10-Q), news feeds, social sentiment | Event-driven strategies, real-time sentiment scoring, language-based factor extraction | Fast; crowded |

### 3.1 Data quality comes before modelling

Most backtest failures trace to data, not to the model. Four problems recur:

- **Look-ahead bias:** using information that was not available at the time, such as restated financials or revised macro releases. Use point-in-time data.
- **Survivorship bias:** testing only on assets that still exist today, which overstates historical returns.
- **Timestamp errors:** misaligned clocks between data sources create false predictability.
- **Corporate actions and rollovers:** splits, dividends and futures rolls must be handled consistently.

### 3.2 Cost and decay

Alternative and unstructured data carry real costs: licensing, storage, cleaning and engineering. The edge they provide is also perishable, since a dataset that is profitable when few funds use it becomes much less so once adoption grows. The question to ask of any dataset is not whether it predicts returns, but whether it predicts them after costs and after competitors have found it.

> **Example: counting cars.** Suppose a satellite company sells weekly car counts for the parking lots of a large retailer. If the lots are fuller than last year while analysts expect flat sales, you have an early read on the earnings report. The catch is that once many funds buy the same images, the surprise is priced in before the report arrives, and an edge becomes a cost of doing business.

## 4. Strategy styles, grouped by source of return

A strategy is only as credible as its answer to one question: who is on the other side of the trade, and why are they willing to lose? The three families below answer it differently.

| Family | Source of return | Who pays | Return profile |
|---|---|---|---|
| Trend following | Underreaction, herding, convexity | Late or forced trend-chasers, hedgers | Positive skew, frequent small losses |
| Statistical arbitrage | Liquidity provision, mean reversion | Impatient liquidity demanders | Negative skew, market neutral |
| Factor and quantitative macro | Risk premia, behavioural mispricing | Investors who avoid risk or overreact | Slow, cyclical, regime-dependent |

### 4.1 Trend following (managed futures, CTA)

Trend followers go long assets that have risen and short those that have fallen, across equities, bonds, currencies and commodities. Return comes from the tendency of prices to adjust gradually to news, and from the payoff shape of a rule that cuts losses and lets winners run.

A standard time-series momentum signal takes the sign of the past return, then scales the position to a risk target:

$$
s_{i,t} = \operatorname{sign}\!\big(r_{i,t-L:t}\big), \qquad w_{i,t} = s_{i,t}\cdot\frac{\sigma^{*}}{\hat{\sigma}_{i,t}}
$$

Variants use moving-average crossovers or breakout channels; the lookback $L$, commonly from one month to a year, is the key parameter. Trend following has often performed well in sustained crises, which is why it is marketed as "crisis alpha". The record is not uniform: sharp reversals, such as 2009 and parts of 2022-23, hurt the strategy, so the claim should be presented as a tendency, not a guarantee.

### 4.2 Statistical arbitrage (equity market neutral)

StatArb exploits short-term deviations between related securities while keeping market exposure near zero ($\beta \approx 0$). Return is compensation for providing liquidity: the strategy buys what others are forced or eager to sell and sells what they are eager to buy.

> **Example: two dogs on a leash.** Picture two dogs tied to the same owner, say two oil companies tied to the same oil price. Each wanders, but the leash keeps pulling them back. When the gap between them is unusually wide, bet that it narrows: buy the dog that fell behind and sell the one that ran ahead. The risk is that the leash can snap, for example when one company is taken over, and the gap never closes.

The classic pairs version models the spread between two stocks and trades its standardised deviation:

$$
z_t = \frac{S_t - \mu_S}{\sigma_S}, \qquad S_t = \log P^{A}_t - \beta \log P^{B}_t
$$

Open a position when $|z_t|$ exceeds an entry threshold and close it as $z_t$ returns toward zero. Modern implementations generalise pairs to baskets and to factor residuals: regress each stock on common factors and trade the idiosyncratic residual, whose mean reversion is modelled directly (Avellaneda and Lee, 2010).

The main danger is crowding. In August 2007, many market-neutral funds held similar positions; forced deleveraging by some pushed prices against all of them within days, the so-called quant quake.

### 4.3 Factor investing and quantitative macro

Factor strategies hold diversified portfolios sorted on characteristics that have historically earned a premium. Quantitative macro applies the same logic across asset classes using economic signals such as growth, inflation and rate differentials.

- **Value:** cheap assets versus expensive ones.
- **Momentum:** recent winners versus recent losers.
- **Quality:** firms with stable, profitable earnings.
- **Low volatility:** lower-risk assets, which have historically offered better risk-adjusted returns than theory predicts.

A factor portfolio is typically built by ranking assets on a score and going long the top group and short the bottom group:

$$
r^{\text{factor}}_t = \bar r_t^{\,\text{top}} - \bar r_t^{\,\text{bottom}}
$$

The debate is over why factors pay: as compensation for bearing risk, or as the result of persistent investor behaviour. The answer affects how much a factor should be trusted to survive.

### 4.4 Where edge comes from when the famous factors are crowded

Value, momentum and quality are well documented, widely held and cheap to implement, so most of their premium is available to anyone and what remains is thin or cyclical. A published anomaly is a starting point, not an edge: the more it has been researched, the more it has been exploited. New returns usually come from one of four places:

1. **Processing information differently.** The same data read better, through new features, better models of text or order flow, or a faster path from raw data to forecast.
2. **Technology and infrastructure.** Faster data pipelines, cheaper execution, better simulation and risk systems, which let you trade ideas that others cannot implement profitably.
3. **Niches and neglected markets.** Capacity too small for large funds, markets with limited participation, or relationships nobody has studied closely.
4. **Portfolio construction and cost control.** Combining many weak, diversified signals and trading them cheaply can turn a crowded premium into a net positive one.

All four decay as others catch up, which is why research is a continuous process and not a one-time project (see Section 5).

## 5. Research process and pitfalls

The research process is where most of the value, and most of the damage, happens. Its aim is to separate a real edge from a pattern that only fits the sample.

### 5.1 From idea to deployment

1. **Hypothesis.** State an economic or behavioural reason for the edge before looking at data: who pays, and why.
2. **Data and universe.** Build a point-in-time dataset and fix the universe and sample period in advance.
3. **Backtest.** Simulate the rules with realistic costs, delays and constraints.
4. **Validation.** Test out of sample, across regimes and on neighbouring parameters. Use walk-forward testing, where parameters are re-estimated only on past data.
5. **Paper trading and small live allocation.** Compare live results and fills with the backtest.
6. **Monitoring.** Track performance against expectations and retire the strategy when it breaks.

The usual summary statistic is the annualised Sharpe ratio of excess returns:

$$
\text{SR} = \frac{\mathbb{E}[r - r_f]}{\sigma(r)}\sqrt{T}
$$

with $T$ the number of return periods per year. A high backtest Sharpe ratio is evidence of a good fit, not of a good strategy.

### 5.2 The main pitfalls

| Pitfall | What goes wrong | Defence |
|---|---|---|
| Overfitting and multiple testing | Many variants tried; the best one looks significant by chance | Fewer parameters, out-of-sample data, adjusting for the number of trials (e.g. the deflated Sharpe ratio) |
| Transaction costs and slippage | Paper profits vanish after spread, fees and market impact | Model costs explicitly; test with higher cost assumptions |
| Regime change | Relationships estimated in one environment break in another | Test across crises and rate regimes; monitor live behaviour |
| Crowding | Many funds hold the same trades and exit together | Track position overlap; prefer diversified, less obvious signals |
| Capacity | Returns shrink as assets under management grow | Estimate market impact at target size |
| Operational risk | Bugs, data outages, stale feeds | Independent checks, kill switches, reconciliation |

### 5.3 Multiple testing in one paragraph

If you test 100 independent strategies with no true edge, about five will show a t-statistic above 2 by chance alone. Published work argues that, given how many factors the profession has tried, a new factor should clear a higher bar than the conventional threshold of 2 (Harvey, Liu and Zhu, 2016). The practical rule is to keep a record of everything you tried, not only what worked, and to demand an economic explanation alongside the statistics.

## 6. Worked case study: a diversified trend-following model

This case walks one strategy through every stage of the pipeline. All parameters are illustrative design choices for teaching, not recommendations, and no performance claim is made; students are asked to produce the results themselves in the exercises.

| Stage | Design choice | Why |
|---|---|---|
| Hypothesis | Prices underreact to news and trend persistence is priced across asset classes | Behavioural and flow-based explanation, tested in many markets |
| Data | Daily settlement prices for liquid futures in equity indices, government bonds, currencies and commodities; back-adjusted continuous series | Liquidity and breadth; consistent roll handling |
| Signal | Sign of the trailing 12-month return, optionally blended with 3- and 6-month signals | Simple, few parameters, little scope for overfitting |
| Allocation | Each market sized to an equal volatility contribution, using an exponentially weighted volatility estimate | Prevents the most volatile markets from dominating |
| Risk | Portfolio volatility target of 10% a year, a cap on gross leverage, and a cap on any single market's weight | Keeps risk stable across regimes |
| Execution | Rebalance daily or weekly with a trade threshold to avoid small, costly trades | Controls turnover and cost |

### 6.1 Questions the case should raise

- How sensitive are results to the lookback and to the volatility window? A robust edge survives reasonable changes.
- How much of the return survives realistic costs and a one-day execution delay?
- Which periods hurt the strategy, and does the hypothesis explain why?
- What would you monitor in live trading to know the edge was fading?

### 6.2 Where the discussion goes next

The same template applies to the other families: replace the signal and the sizing logic, and the questions in Section 5 stay the same. For StatArb the signal becomes a standardised residual, the allocation adds market and factor neutrality, and execution costs dominate. For factor investing, the signal is a cross-sectional rank and the horizon is much longer.

## 7. Summary, exercises and reading

### 7.1 Three takeaways

- Systematic trading is a pipeline from data to execution; allocation and risk are solved together, and a feedback loop keeps the system honest.
- Every strategy needs an answer to who is on the other side of the trade. Trend following, StatArb and factors answer it differently, and so have different risks.
- Bias is not removed but relocated into research. Discipline in the research process matters more than sophistication of the model.

### 7.2 Exercises

- [ ] Define systematic trading in two sentences, and name one decision that remains human in a fully automated fund.
- [ ] Implement the volatility-targeted trend signal from Section 4.1 on a set of futures series and report turnover.
- [ ] Re-run it with a one-day execution delay and with doubled costs. Explain what changes and why.
- [ ] Simulate 200 strategies with no edge and report the best Sharpe ratio. Relate the result to Section 5.3.
- [ ] For a pairs strategy, explain how a structural break in the spread would show up, and what rule would stop trading it.
- [ ] Choose one family from Section 4 and describe who loses money to it and under what conditions that stops.

### 7.3 Reading list

- Carver, R. (2015). *Systematic Trading.* Harriman House.
- Grinold, R. and Kahn, R. (2000). *Active Portfolio Management.* McGraw-Hill.
- López de Prado, M. (2018). *Advances in Financial Machine Learning.* Wiley.
- Moskowitz, T., Ooi, Y. and Pedersen, L. (2012). Time series momentum. *Journal of Financial Economics.*
- Hurst, B., Ooi, Y. and Pedersen, L. (2017). A century of evidence on trend-following investing. *Journal of Portfolio Management.*
- Gatev, E., Goetzmann, W. and Rouwenhorst, K. (2006). Pairs trading: performance of a relative-value arbitrage rule. *Review of Financial Studies.*
- Avellaneda, M. and Lee, J.-H. (2010). Statistical arbitrage in the US equities market. *Quantitative Finance.*
- Khandani, A. and Lo, A. (2011). What happened to the quants in August 2007? *Journal of Financial Markets.*
- Asness, C., Moskowitz, T. and Pedersen, L. (2013). Value and momentum everywhere. *Journal of Finance.*
- Harvey, C., Liu, Y. and Zhu, H. (2016). ... and the cross-section of expected returns. *Review of Financial Studies.*
- Bailey, D. and López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management.*

*References are given from memory and should be checked against the originals before circulation.*
