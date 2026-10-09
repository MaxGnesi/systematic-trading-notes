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

A fixed *time* window (one day, one hour) is the default convention, and a good starting point: it is simple, universally available, and a solid foundation for a wide range of strategy types, which is why this lecture builds on it. It is not, however, the only way to decide where one bar ends and the next begins. A bar can instead close once cumulative traded volume, cumulative dollar volume, or cumulative realised variance crosses a threshold — producing bars that are short during fast, active markets and long during quiet ones, rather than bars that are always the same length in wall-clock time. This is a different design decision about the data layer itself, not an aggregation technique over bars, and it is the subject of a later lecture on tick data and its aggregation; it is worth knowing these alternatives exist before assuming "daily bar" is the only option.

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

### 3.1 Compression and filtering are two different operations

It is tempting to describe Section 1's bar construction and this section's bar aggregation with the same word — both turn many numbers into fewer. They are not the same operation, and conflating them hides what each one is actually for.

- **Section 1 is compression.** A tick-by-tick trade stream becomes five numbers per bar: strictly less data, with specific information thrown away on purpose (the path inside the bar, the buy/sell split). The goal is data volume.
- **This section is filtering.** One input bar still produces one output number — the data does not shrink at all. The goal is to treat each bar's price as a noisy observation of some slower, less noisy quantity, and recover an estimate of that quantity:

$$
p_t = \text{(a slower-moving "true" level)} + \text{(bar-specific noise)}.
$$

A single $p_t$ cannot separate the two terms on the right. Combining several bars can, *if* the noise is less persistent than the level — which is the working assumption behind every technique below. This is precisely the lineage the term "filter" comes from in signal processing and statistics (and, later in this lecture, from the Kalman filter by name): separating a persistent signal from transient noise, not reducing how much data there is.

### 3.2 The general form

Every technique in this lecture is an instance of the same template: a function of a trailing window of past prices, producing one new number at each $t$:

$$
\hat p_t = g\big(p_{t-N+1},\, p_{t-N+2},\, \dots,\, p_t;\; \theta\big)
$$

for some window length $N$ and parameters $\theta$. This is a special case of Lecture 1's $w_t = f(\mathcal{I}_t;\theta)$: it uses only information available at $t$ (it is causal — no bar ever looks ahead of itself), and the same inputs always produce the same output. It sits at the **data → signal** boundary of the pipeline (Lecture 1, §2.1): $\hat p_t$ is not yet a forecast or a position, but it is usually the first derived quantity a forecast is built from.

### 3.3 The real design choice

Given that template, the only real degree of freedom across the whole family is: **how much should each of the $N$ past bars count?**

In a nutshell, a weighting rule can lean on any of several things: treat every bar the same (equal weight); lean on *recency* (newer bars count more); lean on *trading activity* (bars with more volume count more); lean on *how much the price itself moved* in a bar (its range or realised variance — a volatility-weighted scheme); or adapt automatically between these based on recent behaviour. Every one of these is a legitimate, named technique, not a variation on a single "right" one — the point of this section is that there are genuinely many ways to answer "how much should this bar count," each emphasising a different kind of evidence.

This lecture works through one example each of equal weight, recency and trading activity (§4.1–4.3), an adaptive scheme that blends recency with a measure of trend quality (§4.4), and a structurally different recursive estimator (§5). Volatility- and range-weighted schemes — where a bar's own size of move, rather than its volume, sets its weight — exist in the same family and are left to a later lecture, so as not to overload this one; §4 is not the complete list, only a representative cross-section of it.

**What this whole family is trying to do, and what to call it.** Every method below is an answer to the same single question: *net of bar-to-bar noise, where is price actually heading?* Each produces a smoothed estimate of the same kind of thing — a price level — meant to be read as a trend direction, not (yet) a position. That shared purpose is also what distinguishes this family from the volatility-, strength-, flow- and relationship-based aggregations named in §3.4 below: those estimate something other than price, by design. Generically this family is called a **moving average** (loosely, even for a non-averaging method like Kalman) or, more precisely, a **low-pass filter** — a filter that lets the slow-moving component of a series through and suppresses the fast one. In this course's own code it is called a **Baseline**: a raw trend estimate, deliberately on its own scale, kept separate from the later step that turns it into a sized position (an *Envelope*, outside the scope of this lecture).

### 3.4 A map of what else aggregation can target

The same causal-window idea from §3.2, $\hat x_t = g(x_{t-N+1:t};\theta)$, works for inputs and targets other than price. A short map, each left to a later lecture:

| Target | What it represents | Example statistics |
|---|---|---|
| Price level (this lecture) | Where price is heading, net of noise | SMA, EMA, VWAP, KAMA, Kalman |
| Volatility / dispersion | How much price is moving | ATR, realised variance, Parkinson/Garman-Klass range estimators |
| Trend strength / quality | How trustworthy a direction is, not what it is | ADX, efficiency ratio (used on its own), rolling $R^2$, Hurst exponent |
| Flow / participation | Buying vs. selling pressure over time | On-balance volume, cumulative volume delta |
| Relationship between series | Co-movement between two or more assets | Rolling correlation, rolling beta, a cointegration spread's $z$-score |
| Distribution shape | Tail risk, not level or direction | Rolling skewness, rolling kurtosis of returns |

Confusing these is a real failure mode: feeding a trend-strength statistic into a position-sizing formula that expects a volatility estimate, or reading a flow indicator as if it were a price level, produces a number that is well-defined but means the wrong thing for the use it is put to.

## 4. A taxonomy of weighting schemes

| Method | Weighted by | Needs | Memory | Formula |
|---|---|---|---|---|
| SMA | Equal weight | Price only | Rolling (fixed $N$) | $\mathrm{SMA}_t = \dfrac{1}{N}\sum_{k=0}^{N-1} p_{t-k}$ |
| EMA / EWMA | Recency (exponential decay) | Price only | Expanding (recursive) | $\mathrm{EMA}_t = \alpha p_t + (1-\alpha)\mathrm{EMA}_{t-1},\ \ \alpha = \dfrac{2}{N+1}$ |
| VWAP | Trading activity (volume) | Price **and** volume | Rolling (fixed $N$) | $\mathrm{VWAP}_t = \dfrac{\sum_{k=0}^{N-1} p_{t-k}\,v_{t-k}}{\sum_{k=0}^{N-1} v_{t-k}}$ |
| KAMA | Trend-efficiency (adaptive) | Price only | Hybrid (see §4.4) | see §4.4 |

The **Memory** column is worth reading carefully before the formulas: "rolling" means a literal buffer of the last $N$ bars, each one dropped the instant it ages past $N$; "expanding" means a recursive running number that folds in the *entire* history, with old bars' influence fading smoothly rather than being cut off. This distinction matters more than it looks — §6 and §7 both turn on it.

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

KAMA's memory is a genuine hybrid, and worth being precise about. $\mathrm{ER}_t$ is read from a strict rolling $N$-bar window, exactly like SMA — go back more than $N$ bars and it has no effect on today's ratio at all. But the $\mathrm{KAMA}_t$ recursion itself is expanding, exactly like EMA — $\mathrm{KAMA}_{t-1}$ folds in the entire history before it, geometrically discounted. A rolling-window diagnostic sets the decay rate of an otherwise-expanding recursive update.

## 5. A different kind of estimator: the Kalman filter

Sections 4.1–4.4 all share one shape: pick $N$, pick a weight for each of the $N$ bars, take a weighted average. **The Kalman filter is not that**, and treating it as a fifth entry in the same table would be misleading.

### 5.1 Why it does not fit the table above

A Kalman filter keeps a running *belief* about the current level and trend — a mean and an uncertainty — and updates that one belief with each new bar, then discards the raw bar. It never re-reads $p_{t-5}$ or $p_{t-50}$ directly the way SMA or VWAP do; its memory of the past is compressed entirely into its current state and uncertainty, not held as a buffer of past prices. There is consequently no $N$ to set.

In the rolling-vs-expanding language from §4: the Kalman filter is **expanding**, same category as EMA, not rolling like SMA and VWAP. Every bar it has ever seen still has some (geometrically shrinking) influence on today's estimate; none is ever cut off at a fixed age the way a rolling window cuts a bar off at exactly $N$ periods.

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

| Method | Memory | Needs volume? | Decay shape | What breaks it |
|---|---|---|---|---|
| SMA | Rolling, hard edge at $N$ | No | Flat, then a cliff at $N$ | A bar's full influence vanishes all at once $N$ periods later, producing a level jump with no price move behind it |
| EMA/EWMA | Expanding (calibrated by $\alpha$) | No | Smooth geometric decay | Reacts to every move by the same fixed proportion — cannot tell a real trend from one noisy bar |
| VWAP | Rolling, hard edge at $N$ | Yes | Flat within the window, weighted by size | A high-volume bar can dominate the average long after price itself has moved on, and still disappears abruptly at the same cliff as SMA |
| KAMA | Hybrid: rolling ER, expanding recursion | No | Adaptive: fast when $\mathrm{ER}\to 1$, flat when $\mathrm{ER}\to 0$ | A single sharp move *in the same direction as the recent run* pushes $\mathrm{ER}$ toward its maximum, so KAMA reacts as fast as a 2-bar EMA to what may be a one-off spike, not a genuine trend — and once the path reverses afterward, $\mathrm{ER}$ can collapse just as fast, freezing KAMA near a level only that one anomalous bar ever supported |
| Kalman filter | Expanding (set by $Q,R$, not by age directly) | No (an extension could weight by it) | Smooth, set by $Q,R$ | A sustained shift in volatility that the fixed $Q,R$ don't reflect — the filter keeps using a noise model estimated for calmer (or wilder) conditions than currently apply |

## 7. Worked illustration

Ten clean, gently rising bars, then one bar with a sharp +7% move on roughly 4–5× normal volume, then a return to a calm uptrend. $N=5$ throughout. Bars 0–4 (used to seed the window but not shown): prices $100.0, 100.3, 100.5, 100.8, 101.0$, volumes $1000, 1020, 980, 1010, 1040$.

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

### 7.1 Where the $t=7$ numbers actually come from

The 5-bar window ending at $t=7$ is bars $3$–$7$: prices $100.8,\,101.0,\,101.3,\,101.5,\,108.5$; volumes $1010,\,1040,\,990,\,1030,\,4800$.

**SMA(5):** $\dfrac{100.8+101.0+101.3+101.5+108.5}{5} = \dfrac{513.1}{5} = 102.62$.

**EMA(5):** $\alpha = 2/6 = 0.3333$. Using $\mathrm{EMA}_6=101.06$ from the row above, $\mathrm{EMA}_7 = 0.3333\times 108.5 + 0.6667\times 101.06 = 36.17 + 67.37 = 103.54$.

**VWAP(5):** price$\times$volume for each bar: $100.8{\times}1010=101{,}808$; $101.0{\times}1040=105{,}040$; $101.3{\times}990=100{,}287$; $101.5{\times}1030=104{,}545$; $108.5{\times}4800=520{,}800$. Sum $=932{,}480$. Sum of volumes $=1010+1040+990+1030+4800=8870$. $\mathrm{VWAP}_7 = 932{,}480/8870 = 105.13$ — note how the spike bar's volume (4800, roughly 4–5$\times$ a normal bar) accounts for $520{,}800/932{,}480 \approx 56\%$ of the numerator on its own, despite being only one of five bars.

**KAMA(5):** first the efficiency ratio. Net change over the window: $\lvert p_7-p_2\rvert = \lvert 108.5-100.5\rvert = 8.0$. Sum of each bar's absolute move, bar 3 through bar 7: $\lvert 100.8-100.5\rvert+\lvert101.0-100.8\rvert+\lvert101.3-101.0\rvert+\lvert101.5-101.3\rvert+\lvert108.5-101.5\rvert = 0.3+0.2+0.3+0.2+7.0=8.0$. So $\mathrm{ER}_7 = 8.0/8.0 = 1.0$ exactly — every one of these five bars moved in the *same* direction, spike included, so the net move and the total move are identical. With $\alpha_{\text{fast}}=2/3,\ \alpha_{\text{slow}}=2/31$: $\mathrm{sc}_7 = \big(1.0\times(0.6667-0.0645)+0.0645\big)^2 = 0.6667^2 = 0.4444$ — at $\mathrm{ER}=1$ the formula collapses to exactly $\alpha_{\text{fast}}$, the fastest setting KAMA can ever use. $\mathrm{KAMA}_7 = \mathrm{KAMA}_6 + \mathrm{sc}_7\,(p_7-\mathrm{KAMA}_6) = 101.39 + 0.4444\times(108.5-101.39) = 101.39+3.16=104.55$.

This is worth sitting with, because it contradicts the intuitive guess: KAMA is reacting with its **fastest possible** setting here, not a damped one — it actually moves more than EMA(5) does at this exact bar (104.55 vs. 103.54). KAMA's efficiency ratio cannot distinguish "a clean trend" from "a clean trend plus one anomalous spike in the same direction"; both score $\mathrm{ER}=1$.

The more interesting break comes one bar later. At $t=8$: net change $=\lvert102.5-100.8\rvert=1.7$; total move $=0.2+0.3+0.2+7.0+\lvert102.5-108.5\rvert=0.2+0.3+0.2+7.0+6.0=13.7$ (the window now includes both the spike up *and* the reversal back down, so the total-move denominator roughly doubles while net change collapses). $\mathrm{ER}_8 = 1.7/13.7 = 0.124$, and $\mathrm{sc}_8 = (0.124\times0.6022+0.0645)^2 = 0.139^2=0.0194$ — about $1/23$ of the previous bar's setting. $\mathrm{KAMA}_8 = 104.55+0.0194\times(102.5-104.55)=104.55-0.04=104.51$: KAMA has gone from its fastest possible reaction to very nearly frozen in a single bar, and stays close to $104.5$ for several bars afterward even as price has already settled back to the $102.5$–$103.3$ range.

**Kalman filter:** working in $\log$ price. $\mathrm{EMA}$-style predict/update, from the state after $t=6$ ($\ell_6=4.6203$, i.e. $\exp(\ell_6)=101.52$): predicted level $\hat\ell_{7} = \ell_6+\tau_6 = 4.6228$ (the trend term $\tau_6$ is tiny, so this is close to $\ell_6$ itself). Observation: $\log(108.5)=4.6868$. Innovation (observation minus prediction): $4.6868-4.6228=0.0640$. At this point in the run the filter's gain is $g_0\approx 0.470$ (just under half — it has accumulated enough history to trust its own running estimate about as much as a new bar). Updated level: $4.6228+0.470\times0.0640=4.6528$, and $\exp(4.6528)=104.88$.

### 7.2 What the table shows, corrected

- **At $t=7$**, VWAP reacts hardest (105.13) because the spike bar also carries by far the most volume — the two effects compound, as the 56%-of-numerator figure above makes concrete. **KAMA does not react least** — at $\mathrm{ER}=1$ it is at its fastest possible setting and actually moves more than EMA(5) does. The real KAMA story is the bar *after* the spike, not the spike itself.
- **At $t=8$**, KAMA's efficiency ratio collapses from $1.0$ to $0.124$ the instant the window includes the reversal back down, and its smoothing constant falls by a factor of roughly 23. KAMA then coasts near $104.5$ for several bars while price has already returned to normal — a concrete case of "trend-efficiency" being fooled by a single large bar that was never really a trend.
- **Between $t=8$ and $t=11$**, price is calm again, but SMA and VWAP keep *rising* regardless — the spike bar is still inside their rolling 5-bar window, pulling the average up even though nothing unusual is currently happening.
- **At $t=12$**, the spike bar finally exits the 5-bar window (it was at $t=7$; the window is now $t=8\ldots12$), and both SMA and VWAP drop sharply — $104.02\to103.02$ and $105.63\to102.96$ — with no corresponding move in price itself. This is the rolling-window "cliff" from §6, made concrete: a bar's influence does not fade, it disappears all at once.
- **EMA and the Kalman filter**, both expanding, show nothing resembling a cliff at $t=12$; they decay smoothly throughout, at the cost of never fully forgetting the spike either. Re-running EMA(5) on the same series with the spike bar replaced by a normal one (102.0 instead of 108.5) gives $\mathrm{EMA}_{13}=103.24$ versus the actual $103.44$ — a real, if modest, $+0.19$ that the spike is still contributing six bars later, with no sign of it ever reaching exactly zero.

## 8. Summary, exercises and reading

### 8.1 Four takeaways

- OHLCV construction (§1) is *compression*: the data genuinely shrinks, and specific information is thrown away on purpose. Aggregating bars into a smoothed price (§3–5) is *filtering*: the data does not shrink at all, the goal is separating a persistent signal from transient noise. They are easy to describe with the same words ("many numbers into fewer") but are not the same operation.
- A bar's single price (§2) and the aggregation of several bars' prices (§3–5) are two separate design choices, not one — each answers a different question.
- Four of the five techniques here differ only in *how much weight each past bar gets*, and in whether that weight comes from a rolling, fixed-size window (SMA, VWAP) or an expanding recursive one (EMA). KAMA mixes both: a rolling window for its efficiency-ratio diagnostic, an expanding recursion for the price estimate it drives. The Kalman filter is also expanding, but structurally different again — a running belief updated each step, not a weighted sum of raw bars at all.
- Every method in this lecture targets the same thing: a smoothed estimate of price level, what this course's own code calls a **Baseline**. Aggregation is just as capable of targeting volatility, trend strength, flow, correlation between series, or distribution shape instead (§3.4) — using an estimator built for one of these as if it answered a different one is a well-defined mistake, not a stylistic choice.

### 8.2 Exercises

- [ ] For a single bar, construct an example where Median Price and Body Midpoint differ by more than 1% of the close. What kind of trading session produces that?
- [ ] Reproduce the worked table in Section 7 and extend it to $N=10$. Does the SMA/VWAP cliff at $t=12$ disappear, move, or just get smaller?
- [ ] Derive $N_{\text{eff}}$ (§5.3) for a filter with $Q$ ten times larger than the one used here. Is the filter faster or slower, and does that match your intuition about what a larger $Q$ means?
- [ ] §7.1 showed $\mathrm{ER}_t=1$ exactly when every bar in the window moves in the same direction. Construct a 5-bar window containing one large reversal and find its efficiency ratio. Can you make it arbitrarily close to zero? Arbitrarily close to one?
- [ ] Pick one method from Section 4 and describe a market condition where its specific weighting rule would give a *worse* estimate of the "true" price than plain SMA would.
- [ ] Pick one target from the §3.4 map (volatility, trend strength, flow, relationship, distribution shape) and propose one statistic for it, classified the same way Section 4's table classifies SMA/EMA/VWAP/KAMA: what it is weighted by, what data it needs, and whether its memory is rolling or expanding.

### 8.3 Reading list

- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Wiley. — KAMA's original treatment.
- Harvey, A. (1989). *Forecasting, Structural Time Series Models and the Kalman Filter.* Cambridge University Press.
- Ehlers, J. (2001). *Rocket Science for Traders.* Wiley. — adaptive and digital-signal-processing approaches to price smoothing.
- Chan, E. (2013). *Algorithmic Trading: Winning Strategies and Their Rationale.* Wiley. — Kalman filters applied to hedge-ratio and spread estimation.
- Berkowitz, S., Logue, D. and Noser, E. (1988). The total cost of transactions on the NYSE. *Journal of Finance.* — an early treatment of volume-weighted execution benchmarks, the lineage VWAP comes from.

*References are given from memory and should be checked against the originals before circulation.*
