# Systematic Trading: Lecture Notes (MSc)

*Oct 9, 2026 · @Max Gnesi*

## 1. OHLCV: what a bar actually is

A price series is not a sequence of prices. Underneath it is a stream of individual trades, each with its own timestamp, price and size. An OHLCV bar is a deliberate compression of that stream into five numbers for a fixed time window (a minute, an hour, a day): the price the window **O**pened at, the **H**igh and **L**ow it touched, the price it **C**losed at, and the total **V**olume traded during it.

### 1.1 A bar as a lossy summary of the tape

Compression means information is discarded on purpose. A daily bar cannot tell you whether the high came before or after the low, how many separate trades built the volume figure, or whether buying or selling pressure dominated at any point inside the window — only that the price was *somewhere* in $[L, H]$ at some point, and *ended* at $C$. This is a deliberate trade-off: five numbers per period are enough to drive almost every signal and risk calculation in this course, at a tiny fraction of the storage and processing cost of keeping every trade.

### 1.2 The five fields

| Field | What it captures | What it does *not* capture |
|---|---|---|
| Open ($O$) | The first traded price in the window | Nothing before the window started |
| High ($H$) | The highest traded price in the window | When it happened, or how long price stayed there |
| Low ($L$) | The lowest traded price in the window | Same as High |
| Close ($C$) | The last traded price in the window | Everything that happened earlier in the window |
| Volume ($V$) | Total size traded in the window | The split between buyer-initiated and seller-initiated volume (most feeds do not report this; some crypto exchanges do, as "taker buy volume") |

Two bars with identical $O,H,L,C$ can come from completely different paths inside the window — one that opened, spiked to the high immediately and drifted down to the close, and one that did the reverse. The bar cannot distinguish them. Any technique built only from OHLCV inherits this blind spot.

### 1.3 The window itself is a choice, not a law of nature

A fixed *time* window (one day, one hour) is the default convention and the one this course mostly uses, but it is not the only way to decide where one bar ends and the next begins. A bar can instead close once cumulative traded volume, cumulative dollar volume, or cumulative realised variance crosses a threshold — producing bars that are short during fast, active markets and long during quiet ones, rather than bars that are always the same length in wall-clock time. These are a different design decision about the data layer itself, not an aggregation technique over bars, and are out of scope here; they are worth knowing exist before assuming "daily bar" is the only option.

## 2. From a bar to a single price

Every technique in Sections 3–5 needs one number per bar to work with, not four. $C$ is the default choice, but it is only one of several reasonable ways to collapse $(O,H,L,C)$ into a single representative price — and the choice changes what the number emphasises.

### 2.1 Why one number is not automatically the close

The close is simply whichever trade happened last. Depending on the question being asked, that can be exactly the right thing to anchor to (it is the price a mark-to-market happens at) or the wrong thing (a single late print can be noisy, or unrepresentative of where most of the period's volume actually traded).

### 2.2 Seven constructions

| Name | Formula | Emphasises |
|---|---|---|
| Close | $C$ | Where trading ended |
| Open | $O$ | Where trading began |
| Median Price (HL2) | $\dfrac{H+L}{2}$ | The midpoint of the range; ignores the body entirely |
| Typical Price (HLC3) | $\dfrac{H+L+C}{3}$ | A one-number summary that leans slightly toward where the bar settled |
| Weighted Close (HLCC4) | $\dfrac{H+L+2C}{4}$ | Like Typical Price, but the close counts twice |
| OHLC4 ("Average Price") | $\dfrac{O+H+L+C}{4}$ | All four prices equally; the formula behind a Heikin-Ashi candle's close |
| Body Midpoint | $\dfrac{O+C}{2}$ | The midpoint of the body only; ignores the wicks entirely — the opposite emphasis from Median Price |

### 2.3 Choosing among them

None of these is more "correct" than the others; they encode different judgments about what a bar is evidence of. Median Price and Body Midpoint are opposite extremes on the same question (wicks only vs. body only); Typical Price and Weighted Close sit between them, differing only in how much extra weight the close gets. The choice matters less for a smooth, liquid instrument with a narrow daily range, and more for a thinly traded one where a bar's wicks can be a single outsized print away from its body.

## 3. Why aggregate across bars at all

A single bar's price — whichever of the seven above is chosen — is still one noisy observation. Section 2 answers "what number represents *this* bar"; it says nothing about the slower-moving thing the bar is evidence of: the price level or trend the market is actually converging toward, net of the bar-to-bar jitter around it.

### 3.1 A bar's price as a noisy read of a slower state

Treat each bar's price as

$$
p_t = \text{(a slower-moving "true" level)} + \text{(bar-specific noise)}.
$$

A single $p_t$ cannot separate the two terms. Combining several bars can, *if* the noise is less persistent than the level — which is the working assumption behind every technique below. Aggregation is therefore a filtering problem: recovering an estimate of the slow-moving term from a sequence of noisy observations of it.

### 3.2 The general form

Every technique in this lecture is an instance of the same template: a function of a trailing window of past prices, producing one new number at each $t$:

$$
\hat p_t = g\big(p_{t-N+1},\, p_{t-N+2},\, \dots,\, p_t;\; \theta\big)
$$

for some window length $N$ and parameters $\theta$. This is a special case of Lecture 1's $w_t = f(\mathcal{I}_t;\theta)$: it uses only information available at $t$ (it is causal — no bar ever looks ahead of itself), and the same inputs always produce the same output. It sits at the **data → signal** boundary of the pipeline (Lecture 1, §2.1): $\hat p_t$ is not yet a forecast or a position, but it is usually the first derived quantity a forecast is built from.

### 3.3 The real design choice

Given that template, the only real degree of freedom across the whole family is: **how much should each of the $N$ past bars count?** Equal weight, recent bars weighted more, bars with more trading activity weighted more, or something that adapts automatically — each answer is a different named technique, not a different problem.

## 4. A taxonomy of weighting schemes

| Method | Weighted by | Needs | Formula |
|---|---|---|---|
| SMA | Equal weight | Price only | $\mathrm{SMA}_t = \dfrac{1}{N}\sum_{k=0}^{N-1} p_{t-k}$ |
| EMA / EWMA | Recency (exponential decay) | Price only | $\mathrm{EMA}_t = \alpha p_t + (1-\alpha)\mathrm{EMA}_{t-1},\ \ \alpha = \dfrac{2}{N+1}$ |
| VWAP | Trading activity (volume) | Price **and** volume | $\mathrm{VWAP}_t = \dfrac{\sum_{k=0}^{N-1} p_{t-k}\,v_{t-k}}{\sum_{k=0}^{N-1} v_{t-k}}$ |
| KAMA | Trend-efficiency (adaptive) | Price only | see §4.4 |

### 4.1 SMA: equal weight

The plain average of the last $N$ bars. Every bar inside the window counts exactly the same, and every bar outside it counts exactly zero — a hard edge, not a taper. That edge is the source of a specific, predictable artefact: a bar's influence does not fade, it disappears completely and all at once, $N$ periods later (see §6).

### 4.2 EMA / EWMA: recency

"EMA" and "EWMA" name the same construction — Exponential(ly Weighted) Moving Average — and the terms are used interchangeably in finance. Instead of an equal weight inside a hard window, weight decays geometrically with age and never reaches exactly zero:

$$
\mathrm{EMA}_t = \alpha p_t + (1-\alpha)\,\mathrm{EMA}_{t-1}
$$

$N$ enters only through the convention $\alpha = 2/(N+1)$, which calibrates the decay rate to (loosely) "about $N$ bars' worth of memory" — a $k$-bar-old observation still carries weight $\alpha(1-\alpha)^k$, just a small one. There is no literal window being read; the whole history is folded into one running number, $\mathrm{EMA}_{t-1}$.

### 4.3 VWAP: trading activity

Volume-Weighted Average Price replaces "age" with "size": a bar that saw heavy trading counts for more, a quiet bar barely moves the result, regardless of which is more recent.

$$
\mathrm{VWAP}_t = \frac{\sum_{k=0}^{N-1} p_{t-k}\,v_{t-k}}{\sum_{k=0}^{N-1} v_{t-k}}
$$

$p$ is conventionally Typical Price (§2.2), on the reasoning that a single representative price per bar should be paired with that bar's volume; the same construction works with any of the seven prices from Section 2. True intraday VWAP is usually defined over one trading session with no fixed $N$ (it resets at the open); the trailing, fixed-$N$ version above is the common adaptation for daily bars, where there is no natural session boundary to reset at.

### 4.4 KAMA: trend-efficiency, adaptively

Kaufman's Adaptive Moving Average keeps the EMA recursion but lets the decay rate itself change bar to bar, based on how "trend-efficient" the last $N$ bars have been — net progress relative to total movement:

$$
\mathrm{ER}_t = \frac{\lvert p_t - p_{t-N}\rvert}{\displaystyle\sum_{k=0}^{N-1}\lvert p_{t-k}-p_{t-k-1}\rvert} \in [0,1]
$$

$\mathrm{ER}_t \to 1$ for a straight, one-directional run; $\mathrm{ER}_t \to 0$ for a path that doubled back on itself as much as it progressed. That ratio is mapped into a smoothing constant between a fast and a slow EMA's:

$$
\mathrm{sc}_t = \Big(\mathrm{ER}_t\,(\alpha_{\text{fast}}-\alpha_{\text{slow}}) + \alpha_{\text{slow}}\Big)^2, \qquad \mathrm{KAMA}_t = \mathrm{KAMA}_{t-1} + \mathrm{sc}_t\,(p_t - \mathrm{KAMA}_{t-1})
$$

with $\alpha_{\text{fast}}, \alpha_{\text{slow}}$ fixed EMA-style constants (Kaufman's own recommendation corresponds to a 2-bar and a 30-bar EMA). The result: KAMA tracks price tightly while a trend is clean, and goes nearly flat once the market turns choppy — the weighting rule is not fixed at all, it is itself a function of recent price behaviour.

## 5. A different kind of estimator: the Kalman filter

Sections 4.1–4.4 all share one shape: pick $N$, pick a weight for each of the $N$ bars, take a weighted average. **The Kalman filter is not that**, and treating it as a fifth entry in the same table would be misleading.

### 5.1 Why it does not fit the table above

A Kalman filter keeps a running *belief* about the current level and trend — a mean and an uncertainty — and updates that one belief with each new bar, then discards the raw bar. It never re-reads $p_{t-5}$ or $p_{t-50}$ directly the way SMA or VWAP do; its memory of the past is compressed entirely into its current state and uncertainty, not held as a buffer of past prices. There is consequently no $N$ to set.

### 5.2 The recursion

A local-linear-trend filter tracks two unobserved states, a level $\ell_t$ and a trend $\tau_t$, evolving as a random walk with drift:

$$
\begin{pmatrix}\ell_t\\ \tau_t\end{pmatrix} = \begin{pmatrix}1 & 1\\0 & 1\end{pmatrix}\begin{pmatrix}\ell_{t-1}\\ \tau_{t-1}\end{pmatrix} + \eta_t, \qquad \eta_t \sim \mathcal N(0, Q)
$$

and observes $\log p_t = \ell_t + \varepsilon_t,\ \varepsilon_t \sim \mathcal N(0, R)$. Each step predicts forward from the last belief, then corrects that prediction toward the new observation by an amount — the **Kalman gain** — set by how much the filter currently trusts its own running estimate relative to how noisy it believes a single new observation is ($Q$ versus $R$). A large $R$ relative to $Q$ means "trust the model, barely move toward new data"; a small $R$ means the opposite.

### 5.3 The bridge back: an implied effective memory

Despite having no window, a scalar Kalman filter's gain converges to a fixed point as it runs, and at that fixed point the filter is mathematically an EMA with a specific implied $\alpha^\star$. Running the same $N \leftrightarrow \alpha$ relationship from §4.2 backward,

$$
N_{\text{eff}} = \frac{2}{\alpha^\star} - 1,
$$

gives an "effective window" purely as a basis for comparison with §4.1–4.4 — not a literal lookback the filter is reading from. $N_{\text{eff}}$ grows as $R/Q$ grows (trusting new data less implies, in this sense, a longer memory) and is set entirely by that noise ratio, with no separate parameter to tune it directly.

## 6. Comparing the five, side by side

| Method | Literal window? | Needs volume? | Decay shape | What breaks it |
|---|---|---|---|---|
| SMA | Yes, hard edge at $N$ | No | Flat, then a cliff at $N$ | A bar's full influence vanishes all at once $N$ periods later, producing a level jump with no price move behind it |
| EMA/EWMA | No (calibrated by $\alpha$) | No | Smooth geometric decay | Reacts to every move by the same fixed proportion — cannot tell a real trend from one noisy bar |
| VWAP | Yes, hard edge at $N$ | Yes | Flat within the window, weighted by size | A high-volume bar can dominate the average long after price itself has moved on, and still disappears abruptly at the same cliff as SMA |
| KAMA | Yes, for the efficiency ratio only | No | Adaptive: fast in a trend, flat in chop | A sharp one-bar move surrounded by calm bars lowers the efficiency ratio (little net progress relative to the size of the move), so KAMA can under-react to the move itself and then coast well after price has already settled down |
| Kalman filter | No | No (an extension could weight by it) | Smooth, set by $Q,R$, not by age directly | A sustained shift in volatility that the fixed $Q,R$ don't reflect — the filter keeps using a noise model estimated for calmer (or wilder) conditions than currently apply |

## 7. Worked illustration

Ten clean, gently rising bars, then one bar with a sharp +7% move on roughly 4–5× normal volume, then a return to a calm uptrend. $N=5$ throughout.

| $t$ | Price | Volume | SMA(5) | EMA(5) | VWAP(5) | KAMA(5) | Kalman |
|---|---|---|---|---|---|---|---|
| 5 | 101.3 | 990 | 100.78 | 100.84 | 100.78 | 101.30 | 101.29 |
| 6 | 101.5 | 1030 | 101.02 | 101.06 | 101.02 | 101.39 | 101.52 |
| **7** | **108.5** | **4800** | 102.62 | 103.54 | **105.13** | 104.55 | 104.88 |
| 8 | 102.5 | 1700 | 102.96 | 103.19 | 105.12 | 104.51 | 104.30 |
| 9 | 102.8 | 1150 | 103.32 | 103.06 | 105.28 | 104.47 | 104.02 |
| 10 | 103.0 | 1080 | 103.66 | 103.04 | 105.44 | 104.45 | 103.90 |
| 11 | 103.3 | 1030 | 104.02 | 103.13 | 105.63 | 104.42 | 103.91 |
| **12** | 103.5 | 1010 | **103.02** | 103.25 | **102.96** | 104.20 | 103.97 |
| 13 | 103.8 | 1040 | 103.28 | 103.43 | 103.27 | 104.02 | 104.11 |

Four things to read off this table:

- **At $t=7$**, VWAP reacts hardest (105.13) because the spike bar also carries by far the most volume — the two effects (big price move, big size) compound. KAMA reacts least (104.55): a single sharp move surrounded by five calm bars gives a middling efficiency ratio, not a high one.
- **Between $t=8$ and $t=11$**, price is already calm again, but SMA and VWAP keep *rising* — the spike bar is still inside their 5-bar window, pulling the average up even though nothing unusual is currently happening.
- **At $t=12$**, the spike bar finally exits the 5-bar window (it was at $t=7$; the window is now $t=8\ldots12$) and both SMA and VWAP drop sharply — 104.02→103.02 and 105.63→102.96 — with no corresponding move in price itself. This is the "cliff" from §6, made concrete.
- **EMA and the Kalman filter** show nothing resembling a cliff at $t=12$; both decay smoothly throughout, which is exactly the trade-off a hard window avoids — at the cost of never fully forgetting the spike either (compare EMA at $t=13$, 103.43, to the actual 5-bar-ago-unaffected level around 103.5–103.8).

## 8. Summary, exercises and reading

### 8.1 Three takeaways

- OHLCV is a lossy, deliberate summary of the underlying trade tape; everything built on top of it inherits what it discards.
- A bar's "price" (Section 2) and the aggregation of several bars' prices (Sections 3–5) are two separate design choices, not one — each answers a different question.
- Four of the five techniques here differ only in *how much weight each past bar gets*; the Kalman filter answers the same underlying question (what is the price doing, net of noise) through a structurally different mechanism, with no literal window at all.

### 8.2 Exercises

- [ ] For a single bar, construct an example where Median Price and Body Midpoint differ by more than 1% of the close. What kind of trading session produces that?
- [ ] Reproduce the worked table in Section 7 and extend it to $N=10$. Does the SMA/VWAP cliff at $t=12$ disappear, move, or just get smaller?
- [ ] Derive $N_{\text{eff}}$ (§5.3) for a filter with $Q$ ten times larger than the one used here. Is the filter faster or slower, and does that match your intuition about what a larger $Q$ means?
- [ ] Using the data and volume from Section 7, compute KAMA with $N=3$ instead of 5 and compare its reaction at $t=7$. Explain the difference in terms of the efficiency ratio.
- [ ] Pick one method from Section 4 and describe a market condition where its specific weighting rule would give a *worse* estimate of the "true" price than plain SMA would.

### 8.3 Reading list

- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Wiley. — KAMA's original treatment.
- Harvey, A. (1989). *Forecasting, Structural Time Series Models and the Kalman Filter.* Cambridge University Press.
- Ehlers, J. (2001). *Rocket Science for Traders.* Wiley. — adaptive and digital-signal-processing approaches to price smoothing.
- Chan, E. (2013). *Algorithmic Trading: Winning Strategies and Their Rationale.* Wiley. — Kalman filters applied to hedge-ratio and spread estimation.
- Berkowitz, S., Logue, D. and Noser, E. (1988). The total cost of transactions on the NYSE. *Journal of Finance.* — an early treatment of volume-weighted execution benchmarks, the lineage VWAP comes from.

*References are given from memory and should be checked against the originals before circulation.*
