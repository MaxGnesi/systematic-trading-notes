# Lecture 1: Introduction to Systematic Trading

> Every decision, from data to executed order, follows explicit rules that can be written down, tested on history and repeated without discretion.

Part I · The whole pipeline

---

# A function from information to positions

> A strategy needs two views: how the machine is built, and why it should make money. A sound architecture with no economic reason behind it is a well-engineered guess.

$$w_t = f(\mathcal{I}_t;\,\theta), \qquad \mathcal{I}_t = \{\text{data available at time } t\}$$

- $w_t$ is the target portfolio, $f$ the rule set, $\theta$ the parameters chosen in research
- $f$ uses only information available at $t$
- The same inputs always produce the same outputs

---

# A spectrum, not a binary

> Most real firms sit between the extremes. What differs is where human judgment enters.

| Style | Who decides | Where the human sits |
|---|---|---|
| Discretionary | Portfolio manager | Every decision |
| Quantamental | Manager, informed by models | Final decision and sizing |
| Systematic, human-supervised | Model | Research, risk overrides, model changes |
| Fully automated | Model | Research only |

Bias does not disappear: it moves upstream into research, into which hypotheses, data, parameters and switch-off rules are chosen.

---

# The pipeline: five stages, one feedback loop

> A systematic strategy is a chain of five stages, each with its own inputs, outputs and failure modes, and each fed back by what the market actually did.

1. **Data:** ingest, clean and timestamp; errors propagate downstream
2. **Signal generation:** a forecast, e.g. a score $s_{i,t} \in [-1, +1]$
3. **Portfolio construction and allocation:** signals into target positions
4. **Risk management:** volatility targets, limits, drawdown rules
5. **Execution:** route orders to minimise slippage and market impact

The loop from execution back to data lets a team detect decay. Each lecture names its stage under its title.

---

# Allocation and risk are one problem

> Risk control is built into position sizing, not bolted on at the end.

$$\max_{w}\; \mu^{\top} w \;-\; \frac{\lambda}{2}\, w^{\top}\Sigma\, w \;-\; c(w - w_{t-1})$$

- Forecasts $\mu$, covariance $\Sigma$, risk aversion $\lambda$, and the cost of trading from the previous holdings
- The simplest case is volatility targeting: $w_{i,t} = s_{i,t}\cdot\sigma^{*}/\hat{\sigma}_{i,t}$
- **Driving on ice:** slow down when the road turns icy, so the risk of a crash stays about the same

---

# Data comes before modelling

> Most backtest failures trace to data, not to the model.

- **Look-ahead bias:** restated financials, revised macro releases; use point-in-time data
- **Survivorship bias:** only assets that still exist today overstate returns
- **Timestamp errors:** misaligned clocks create false predictability
- **Corporate actions and rollovers:** splits, dividends and futures rolls
- The question for any dataset: does it predict returns **after costs and after competitors have found it?**

---

# Who is on the other side?

> A strategy is only as credible as its answer to one question: who is on the other side of the trade, and why are they willing to lose?

| Family | Source of return | Who pays | Return profile |
|---|---|---|---|
| Trend following | Underreaction, herding, convexity | Late or forced trend-chasers, hedgers | Positive skew, frequent small losses |
| Statistical arbitrage | Liquidity provision, mean reversion | Impatient liquidity demanders | Negative skew, market neutral |
| Factor and quantitative macro | Risk premia, behavioural mispricing | Investors who avoid risk or overreact | Slow, cyclical, regime-dependent |

These families are examples, not the boundary of the field.

---

# From idea to deployment

> A high backtest Sharpe ratio is evidence of a good fit, not of a good strategy.

1. **Hypothesis:** an economic reason, stated before looking at data: who pays, and why
2. **Data and universe:** point-in-time; universe and sample period fixed in advance
3. **Backtest:** realistic costs, delays and constraints
4. **Validation:** out of sample, across regimes, on neighbouring parameters; walk-forward
5. **Paper trading, small live allocation, monitoring:** retire the strategy when it breaks

---

# Overfitting: the gap between past and future

> If the future were an exact copy of the past, there would be no overfitting. Overfitting is the gap between the two.

| Source | What it means | Can it be checked in advance? |
|---|---|---|
| **Dependence on the sample** | The history we saw is one draw among many; the best rule partly fits its noise | Yes: other slices of the past, other markets, a luck baseline |
| **A future unlike the past** | Markets evolve: rate regimes, players, crowding | No: only a mechanism and monitoring help |

---

# Three warning signs

> Prefer a region of parameters to the best point, distrust outlier results, and test across markets.

- **The exact best parameter of an optimisation:** the peak of a search is where noise helped most; prefer a plateau
- **Outlier performance:** most often a mistake, otherwise more often luck than skill; compare with a **luck baseline**
- **A strategy that works in one market only:** the least evidence there is
- **Multiple testing:** of 100 independent strategies with no true edge, about five show a $t$-statistic above 2 by chance

---

# Telling noise from an edge

> No single result can prove it is not noise. What can be done is to measure how large the noise is and look for its fingerprints.

- A Sharpe ratio over $T$ years has a standard error of about $1/\sqrt{T}$: about 0.32 over ten years
- The best of 1,000 tries is lifted about three standard errors above the median by luck
- Lecture 7: trend systems' Sharpe ratios in two periods correlate at 0.62; zero-edge strategies' at 0.02

| Check | Noise | An edge |
|---|---|---|
| Neighbouring parameters | An isolated peak | A plateau |
| Other markets | One place only | Wherever its mechanism applies |
| Mechanism | None, or found after the result | Stated before the test |

---

# Many small edges, not one ace

> Ten modest edges that do not move together reach a Sharpe ratio that almost no single strategy keeps for long.

$$\text{SR}_{\text{combined}} \;=\; s\,\sqrt{\frac{n}{1 + (n-1)\,\rho}}$$

| | One strategy | 10, $\rho = 0$ | 10, $\rho = 0.2$ | 10, $\rho = 0.5$ |
|---|---|---|---|---|
| Sharpe ratio | 0.30 | 0.95 | 0.57 | 0.40 |

- Correlation matters more than the count: a new strategy's value lies in **failing at different times**
- A single ace gets found: 97 published predictors earned 58% less after publication

---

# Working with an AI assistant

> An assistant makes a try cheap, so what is tested must be decided before anything runs.

- **Delegate:** data pipelines, code, backtests, robustness grids, literature searches
- **Keep:** the question, the expectation written before the test, the judgment, the decision to keep or drop
- **Lock in advance, dated:** the question, the variants and search budget, the tests, the data held back
- **Log and count every try;** check references at the source
- **Adapt on findings, with discipline:** judge each change by cost against benefit and by robustness

---

# Takeaways

1. **A pipeline from data to execution:** allocation and risk are solved together, and a feedback loop keeps the system honest
2. **Who is on the other side:** trend following, StatArb and factors answer it differently, and so have different risks
3. **Bias is relocated, not removed:** discipline in research matters more than the sophistication of the model
4. **Overfitting is the gap between the past and the future:** prefer plateaus; distrust outliers and one-market rules
5. **Many robust small edges, not one ace**
