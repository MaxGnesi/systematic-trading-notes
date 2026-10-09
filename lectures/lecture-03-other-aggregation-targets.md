# Systematic Trading: Lecture Notes (MSc)

*Oct 9, 2026 · @Max Gnesi*

## 1. Recap: five targets, one shared idea

Lecture 2 built one family of techniques — SMA, EMA, VWAP, KAMA, the Kalman filter — all answering the same question: *net of bar-to-bar noise, where is price actually heading?* Its §3.4 named four other things a causal window of bars can be made to represent instead of price. This lecture works through one of each, at the same depth Lecture 2 gave price level.

### 1.1 Why these are genuinely different jobs

Every technique below still has the shape from Lecture 2, §3.2 — a causal function of a trailing window, $\hat x_t = g(x_{t-N+1:t};\theta)$ — but $x$ and $\hat x$ are no longer both "price." A volatility estimator takes price in and puts a dispersion measure out; a correlation estimator takes two price series in and puts a single relationship statistic out. Using the wrong one for a job (reading a trend-strength number as if it were a volatility forecast, say) produces a well-defined number that answers a different question than the one being asked.

### 1.2 A shared dataset, used throughout

One extended version of Lecture 2 §7's series, now with high/low (needed for volatility and trend-strength) and a second, calmer asset $B$ (needed for the relationship section). $N=5$ throughout, matching Lecture 2.

| $t$ | $O/H/L$ asset $A$ | Close $A$ | Volume $A$ | Close $B$ |
|---|---|---|---|---|
| 0 | H 100.2, L 99.8 | 100.0 | 1000 | 50.00 |
| 1 | H 100.5, L 100.1 | 100.3 | 1020 | 50.20 |
| 2 | H 100.7, L 100.3 | 100.5 | 980 | 50.10 |
| 3 | H 101.0, L 100.6 | 100.8 | 1010 | 50.35 |
| 4 | H 101.2, L 100.8 | 101.0 | 1040 | 50.25 |
| 5 | H 101.5, L 101.1 | 101.3 | 990 | 50.50 |
| 6 | H 101.7, L 101.3 | 101.5 | 1030 | 50.40 |
| **7** | **H 109.0, L 102.0** | **108.5** | **4800** | 50.65 |
| 8 | H 103.3, L 101.6 | 102.5 | 1700 | 50.55 |
| 9 | H 103.0, L 102.5 | 102.8 | 1150 | 50.80 |
| 10 | H 103.2, L 102.8 | 103.0 | 1080 | 50.70 |
| 11 | H 103.5, L 103.1 | 103.3 | 1030 | 50.95 |
| 12 | H 103.7, L 103.3 | 103.5 | 1010 | 50.85 |
| 13 | H 104.0, L 103.6 | 103.8 | 1040 | 51.10 |

$A$ is exactly Lecture 2's series: calm, then one sharp spike on heavy volume, then a calm recovery. $B$ is a separate instrument that trends gently in the same direction throughout but never spikes — the question Section 5 asks is what happens to the *relationship* between them when $A$ has an event $B$ doesn't share.

## 2. Volatility / dispersion: how much is price moving

### 2.1 True range and Wilder's ATR

Close-to-close price change understates a bar's real movement whenever price travels and comes back within the bar. The **true range** fixes this by also checking against the previous close:

$$
\mathrm{TR}_t = \max\big(H_t - L_t,\ \lvert H_t - C_{t-1}\rvert,\ \lvert L_t - C_{t-1}\rvert\big)
$$

The **Average True Range** (Wilder, 1978) smooths $\mathrm{TR}_t$ the same way Wilder smooths everything in this lecture — an EMA-style recursion with $\alpha = 1/\text{period}$, seeded by a simple average of the first `period` values:

$$
\mathrm{ATR}_t = \mathrm{ATR}_{t-1} + \frac{1}{\text{period}}\big(\mathrm{TR}_t - \mathrm{ATR}_{t-1}\big)
$$

This is worth flagging against Lecture 2's rolling/expanding distinction (§4): **Wilder's smoothing is the EMA recursion under a different name**, so ATR is expanding, not a rolling window of recent ranges, even though "period" looks like a window size.

### 2.2 Worked arithmetic

True range for every bar (period 5): $0.40,\allowbreak 0.50,\allowbreak 0.40,\allowbreak 0.50,\allowbreak 0.40,\allowbreak 0.50,\allowbreak 0.40,\allowbreak 7.50,\allowbreak 6.90,\allowbreak 0.50,\allowbreak 0.40,\allowbreak 0.50,\allowbreak 0.40,\allowbreak 0.50$.

$\mathrm{ATR}_4 = (0.40+0.50+0.40+0.50+0.40)/5 = 0.440$ (seed, simple average of the first 5). Then recursively: $\mathrm{ATR}_5 = 0.440 + \tfrac{1}{5}(0.50-0.440) = 0.452$; $\mathrm{ATR}_6=0.442$; at the spike, $\mathrm{ATR}_7 = 0.442+\tfrac15(7.50-0.442)=1.853$.

| $t$ | 4 | 5 | 6 | **7** | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|
| TR | 0.40 | 0.50 | 0.40 | **7.50** | 6.90 | 0.50 | 0.40 | 0.50 | 0.40 | 0.50 |
| ATR(5) | 0.440 | 0.452 | 0.442 | **1.853** | 2.863 | 2.390 | 1.992 | 1.694 | 1.435 | 1.248 |

Two things worth noting. First, ATR *keeps rising* for one more bar after the spike (1.853→2.863) because bar 8's true range is also large (6.90 — the overnight gap back down from 108.5 dominates it, not the day's own high-low), so the "event" is really two outsized bars, not one. Second, ATR decays slowly and smoothly afterward (2.863→1.248 over five bars) rather than snapping back — the same expanding-memory behaviour EMA showed in Lecture 2, now applied to range instead of price. A position-sizing rule reading ATR right after $t=8$ would keep sizing down for several more days than a glance at the (already-calm) price series would suggest.

Parkinson and Garman-Klass estimators use the same high/low information but combine it differently (squared log-range rather than Wilder's smoothed absolute range) to estimate the underlying *variance* more efficiently; the mechanism is the same shape as ATR — a causal transform of $H,L,C$ into a dispersion number — and is left as an exercise rather than worked here.

## 3. Trend strength / quality: how trustworthy is this direction

Lecture 2 used the efficiency ratio only as an internal dial inside KAMA. It is a perfectly good statistic in its own right.

### 3.1 Efficiency ratio, standalone

$$
\mathrm{ER}_t = \frac{\lvert p_t - p_{t-N}\rvert}{\sum_{k=0}^{N-1}\lvert p_{t-k}-p_{t-k-1}\rvert} \in [0,1]
$$

Read on its own, $\mathrm{ER}_t$ says nothing about direction, only about how "clean" the recent path has been.

### 3.2 ADX

Wilder's Average Directional Index asks a related but different question using the *range*, not just the close: is price making new highs, new lows, or neither?

$$
{+}\mathrm{DM}_t = \begin{cases}H_t-H_{t-1} & \text{if } H_t-H_{t-1} > L_{t-1}-L_t \text{ and } H_t-H_{t-1}>0\\ 0 & \text{otherwise}\end{cases}, \qquad {-}\mathrm{DM}_t \text{ symmetrically on new lows}
$$

Each of $+\mathrm{DM}$, $-\mathrm{DM}$ and $\mathrm{TR}$ is Wilder-smoothed (the same recursion as §2.1), then combined into directional indicators, their normalised difference, and a smoothed version of that difference:

$$
{+}\mathrm{DI}_t = 100\,\frac{\overline{{+}\mathrm{DM}}_t}{\overline{\mathrm{TR}}_t}, \qquad \mathrm{DX}_t = 100\,\frac{\lvert{+}\mathrm{DI}_t - {-}\mathrm{DI}_t\rvert}{{+}\mathrm{DI}_t+{-}\mathrm{DI}_t}, \qquad \mathrm{ADX}_t = \text{Wilder-smoothed } \mathrm{DX}_t
$$

$\mathrm{ADX}$ is bounded in $[0,100]$ and, like $\mathrm{ER}$, carries no sign — high means "one direction has been dominating," not which one.

### 3.3 Worked arithmetic

$\mathrm{ER}(5)$ on asset $A$'s closes:

| $t$ | 5 | 6 | **7** | **8** | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|
| ER(5) | 1.000 | 1.000 | **1.000** | **0.124** | 0.130 | 0.124 | 0.130 | 0.714 | 1.000 |

— exactly Lecture 2 §7.1's numbers, since it is the same statistic on the same series.

For ADX, the new-high/new-low mechanics change the story. $+\mathrm{DM}$ and $-\mathrm{DM}$, bar by bar:

| $t$ | 1 | 2 | 3 | 4 | 5 | 6 | **7** | **8** | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| $+\mathrm{DM}$ | 0.30 | 0.20 | 0.30 | 0.20 | 0.30 | 0.20 | **7.30** | 0.00 | 0.00 | 0.20 | 0.30 | 0.20 | 0.30 |
| $-\mathrm{DM}$ | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.40** | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Bar 8 is the interesting one: close falls sharply (108.5→102.5), but $+\mathrm{DM}_8=0$ *and* this is the only bar in the whole series with $-\mathrm{DM}>0$ at all, and even then only $0.40$ — because ADX only registers a down-move when the bar sets a **new low** versus the previous bar's low, and bar 8's low ($101.6$) only just undercuts bar 7's low ($102.0$). A loud reversal in closing price can be almost invisible to ADX if it doesn't also break into new range territory.

$+\mathrm{DI}$ stays around 44–49 throughout except the spike bar (88.1); $-\mathrm{DI}$ is exactly $0$ until bar 8, then a few points. $\mathrm{DX}=100$ whenever $-\mathrm{DI}=0$ (bars 4–7), then drops to the high 80s afterward. $\mathrm{ADX}$ (first value at $t=8$, the simple average of $\mathrm{DX}_{4..8}$):

| $t$ | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|
| ADX | 97.69 | 95.84 | 94.47 | 93.53 | 92.90 | 92.59 |

ADX stays pinned near $95$ throughout: one brief, shallow dip below a prior low barely dents a reading built almost entirely on five clean up-moves (one of them the spike itself, which — per §3.2's rule — still counts as "up" however violent it was). **A very high ADX does not mean "a calm, orderly trend"; it means "one direction has dominated," which a single enormous bar is fully capable of producing on its own.**

## 4. Flow / participation: who is doing the buying

### 4.1 On-balance volume

OBV assigns each bar's entire volume a sign from the direction of its close, and accumulates:

$$
\mathrm{OBV}_t = \mathrm{OBV}_{t-1} + \begin{cases} +v_t & C_t > C_{t-1}\\ -v_t & C_t < C_{t-1}\\ 0 & C_t = C_{t-1}\end{cases}
$$

Unlike every other statistic in this lecture, OBV has **no decay at all** — not rolling (no cutoff), not expanding-with-decay (no $\alpha$ or period shrinking old contributions). It is a plain running sum: a third memory pattern, alongside Lecture 2's rolling and expanding, worth its own name — *cumulative*.

### 4.2 Worked arithmetic

Seeding $\mathrm{OBV}_0=0$:

| $t$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | **7** | **8** | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Close | 100.0 | 100.3 | 100.5 | 100.8 | 101.0 | 101.3 | 101.5 | **108.5** | **102.5** | 102.8 | 103.0 | 103.3 | 103.5 | 103.8 |
| Volume | — | 1020 | 980 | 1010 | 1040 | 990 | 1030 | **4800** | **1700** | 1150 | 1080 | 1030 | 1010 | 1040 |
| OBV | 0 | 1020 | 2000 | 3010 | 4050 | 5040 | 6070 | **10870** | **9170** | 10320 | 11400 | 12430 | 13440 | 14480 |

$\mathrm{OBV}_7 = 6070+4800=10870$: the spike adds its *entire* volume, because OBV only reads the sign of the move, never its size. $\mathrm{OBV}_8=10870-1700=9170$: bar 8's close fell, so its volume subtracts, even though in price terms bar 8 was a partial recovery back toward bar 6's level, not a fresh move down. From $t=9$ OBV resumes climbing with the (now calm) uptrend, never returning to acknowledge that the $t{=}7/8$ episode was, on net, a small round trip in price — OBV has already banked both legs of it as $+4800$ and $-1700$ separately and permanently.

This is OBV's central limitation, visible directly in the numbers: it tracks accumulated *direction-weighted-by-size*, not any kind of level, so it is not mean-reverting and not comparable in magnitude across instruments or time — only its *slope* is generally read, not its value.

## 5. Relationship between series: do two assets still move together

### 5.1 Rolling correlation

Over a trailing window of $N$ returns (not prices — co-movement is about how two series *change*, not their levels):

$$
\rho_t(N) = \frac{\sum_{k=0}^{N-1}(r^A_{t-k}-\bar r^A)(r^B_{t-k}-\bar r^B)}{\sqrt{\sum_{k=0}^{N-1}(r^A_{t-k}-\bar r^A)^2}\,\sqrt{\sum_{k=0}^{N-1}(r^B_{t-k}-\bar r^B)^2}}
$$

with $\bar r^A,\bar r^B$ the window's own means. Bounded in $[-1,1]$; a rolling, fixed-$N$ statistic, with the same hard-edge "cliff" property Lecture 2 found in SMA and VWAP.

### 5.2 Rolling beta

Where correlation asks "how clean is the co-movement," beta asks "how large is it" — a regression slope of $A$'s returns on $B$'s, over the same window:

$$
\beta_t(N) = \frac{\sum_{k=0}^{N-1}(r^A_{t-k}-\bar r^A)(r^B_{t-k}-\bar r^B)}{\sum_{k=0}^{N-1}(r^B_{t-k}-\bar r^B)^2}
$$

The two share a numerator; $\rho$ divides by the geometric mean of both series' dispersion, $\beta$ divides by $B$'s dispersion alone. They can legitimately disagree, as the numbers below show.

### 5.3 Worked arithmetic

Returns, rounded to three decimals (as %):

| $t$ | 5 | 6 | **7** | **8** | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|
| $r^A$ | 0.297 | 0.197 | **6.897** | **$-$5.530** | 0.293 | 0.195 | 0.291 | 0.194 | 0.290 |
| $r^B$ | 0.498 | $-$0.198 | 0.496 | $-$0.197 | 0.495 | $-$0.197 | 0.493 | $-$0.196 | 0.492 |

$B$'s own returns alternate up/down by design (a steady zigzag), so its own rolling variance stays small and stable throughout — needed so that beta (which divides by it) doesn't blow up on a near-empty denominator.

| $t$ | 5 | 6 | **7** | 8 | 9 | 10 | 11 | **12** | 13 |
|---|---|---|---|---|---|---|---|---|---|
| $\rho(5)$ | 0.992 | 1.000 | **0.421** | 0.659 | 0.642 | 0.661 | 0.644 | **0.426** | 1.000 |
| $\beta(5)$ | 0.148 | 0.143 | **3.288** | 7.626 | 7.437 | 7.670 | 7.481 | **2.910** | 0.141 |

Away from the event ($t=5,6,13$), $\rho\approx1$ and $\beta\approx0.14$: within these calm windows the two series' returns move in near-perfect lockstep, at a fixed ratio of roughly 1 part $A$ to 7 parts $B$ — a ratio set entirely by how this particular toy series was constructed, not a general fact about any two correlated assets. Both numbers break down together once the spike enters the window at $t=7$: correlation falls to $0.421$ (the two series are no longer moving cleanly together) **while beta rises to $3.288$ and keeps rising to over $7.6$** — the opposite direction from what the correlation collapse might suggest. The reason is visible directly in the return table: $A$'s one huge move ($6.897\%$) is paired with an ordinary-sized move in $B$ ($0.496\%$), so *whatever* comovement is left in the window gets amplified by the ratio of the two series' typical move sizes. **Correlation and beta answer different questions and can move in opposite directions during the same event**: correlation says the relationship got noisier; beta says that, to whatever extent it still held, it held at a much larger scale than usual. A hedge sized from this window's beta would be badly wrong — not because the statistic is broken, but because the event that produced it was a one-off, not a new steady state. By $t=13$, with the event five bars behind the window, both numbers are back to their pre-event values exactly.

## 6. Distribution shape: is the recent path lopsided

### 6.1 Rolling skewness

$$
\mathrm{Skew}_t(N) = \frac{1}{N}\sum_{k=0}^{N-1}\left(\frac{r_{t-k}-\bar r}{\hat\sigma}\right)^3
$$

Positive means a few large up-moves and mostly small down-moves (or vice versa in sign for the reverse); zero means a symmetric window.

### 6.2 Rolling kurtosis

$$
\mathrm{Kurt}_t(N) = \frac{1}{N}\sum_{k=0}^{N-1}\left(\frac{r_{t-k}-\bar r}{\hat\sigma}\right)^4 - 3
$$

The $-3$ makes this *excess* kurtosis: zero for a Gaussian window, positive for a window with fatter tails (more extreme moves than a Gaussian would produce) than that.

### 6.3 Worked arithmetic, and a caveat

On $A$'s returns, $N=5$:

| $t$ | 5 | 6 | **7** | 8 | 9 | 10 | 11 | **12** | 13 |
|---|---|---|---|---|---|---|---|---|---|
| Skew(5) | $-$0.407 | 0.408 | **1.499** | 0.206 | 0.192 | 0.207 | 0.193 | **$-$1.499** | $-$0.407 |
| Kurt(5), excess | $-$1.832 | $-$1.832 | 0.249 | $-$0.488 | $-$0.489 | $-$0.488 | $-$0.489 | 0.248 | $-$1.832 |

Skew is strongly positive ($1.499$) exactly when the window holds the up-spike and four ordinary bars, and strongly negative ($-1.499$, same magnitude) five bars later when the window instead holds the down-reversal and four ordinary bars — the statistic correctly reads "one outsized move, rest typical" in both directions, with the sign tracking which direction the outlier was in. Away from the event, skew sits modestly positive ($\approx0.19$–$0.21$), a mild artefact of this particular calm uptrend having slightly more small up-days than down-days inside a 5-bar window.

The honest caveat: $N=5$ is a very small sample for a third or fourth moment. These numbers are correctly computed and directionally sensible here only because the series was built to make one single bar obviously dominant; on real data with genuine (not constructed) noise, skewness and kurtosis estimated from 5 points are themselves extremely noisy statistics, and a much larger $N$ — or an exponentially-weighted version of the same formulas, trading the same rolling-vs-expanding choice Lecture 2 made for price — is standard practice before trusting either number.

## 7. Comparing all five targets, side by side

| Target | Statistic | Needs | Memory | Answers |
|---|---|---|---|---|
| Volatility | ATR | $H,L,C$ | Expanding (Wilder = EMA) | How much is price moving, in price units |
| Trend strength | Efficiency ratio | Price only | Rolling, fixed $N$ | How clean (not which direction) the recent path has been |
| Trend strength | ADX | $H,L,C$ | Expanding (Wilder) | How much one direction has dominated via new highs/lows, not closes |
| Flow | OBV | $C$, volume | **Cumulative** (no decay at all) | Accumulated direction-weighted-by-size, read by its slope |
| Relationship | Rolling correlation | Two price series | Rolling, fixed $N$ | How cleanly two series are co-moving |
| Relationship | Rolling beta | Two price series | Rolling, fixed $N$ | How large the co-movement is, in units of one series per unit of the other |
| Distribution shape | Rolling skew / kurtosis | Price only | Rolling, fixed $N$ | Whether the recent path was lopsided or fat-tailed, not its level or direction |

Every row needs a different subset of the available data (some need volume, one needs a second instrument entirely) and targets a different question; only two of the seven (ATR, ADX) share Lecture 2's EMA-style expanding memory, three are rolling in the same hard-edged way SMA was, and OBV is in a category of its own.

## 8. Summary, exercises and reading

### 8.1 Four takeaways

- All five targets reuse the same causal-window template from Lecture 2, but $x$ and $\hat x$ are no longer both price — a volatility, strength, flow, relationship or shape statistic answers a structurally different question than a Baseline does, even when built the same way.
- A statistic can look broken when it is actually just answering a narrow question precisely: ADX staying near 95 through a violent one-bar reversal, or OBV never "giving back" a round trip, are both correct behaviour for what each statistic actually measures, not bugs.
- Two statistics meant to describe the "same" underlying relationship can disagree, and even move in opposite directions, during the same event — correlation and beta here are the clearest example, and neither one is the "wrong" one.
- OBV's complete lack of decay is a third memory pattern beyond Lecture 2's rolling and expanding: a plain, permanent running sum.

### 8.2 Exercises

- [ ] Using §2.2's table, compute what ATR(5) would have been if bar 8's true range had been a normal $0.50$ instead of $6.90$ (i.e. no overnight gap after the spike). How much lower does ATR peak, and does it still take several bars to decay?
- [ ] §3.3 showed ADX barely reacting to bar 8's reversal because it didn't set a new low by much. Construct a low for bar 8 that would make $-\mathrm{DM}_8$ exceed $+\mathrm{DM}_7$, and describe what kind of price action that requires.
- [ ] Compute OBV for a version of the series where bar 8 closes *above* bar 7 (continuing up) instead of reversing. How different does $\mathrm{OBV}_{13}$ end up, and why does a pure accumulator make that comparison meaningful?
- [ ] §5.3 found correlation and beta moving in opposite directions at $t=7$. Construct a different 5-bar window (any two series) where they instead move in the *same* direction. What has to be true of the two series' relative move sizes for that to happen?
- [ ] Recompute §6.3's skewness with $N=10$ instead of $5$ (extend the series however you like for the extra bars). Does the spike's effect on skew get smaller, as the small-sample caveat would predict?

### 8.3 Reading list

- Wilder, J.W. (1978). *New Concepts in Technical Trading Systems.* Trend Research. — the original source for ATR, ADX and the directional movement system.
- Parkinson, M. (1980). The extreme value method for estimating the variance of the rate of return. *Journal of Business.*
- Garman, M. and Klass, M. (1980). On the estimation of security price volatilities from historical data. *Journal of Business.*
- Granville, J. (1963). *Granville's New Key to Stock Market Profits.* Prentice-Hall. — on-balance volume's original source.
- Engle, R. and Granger, C. (1987). Co-integration and error correction: representation, estimation and testing. *Econometrica.* — the formal basis for the relationship statistics in Section 5 and their use in Lecture 1's §4.2 StatArb.
- Cont, R. (2001). Empirical properties of asset returns: stylized facts and statistical issues. *Quantitative Finance.* — on fat tails and why skewness/kurtosis of financial returns need care, the basis for §6.3's caveat.

*References are given from memory and should be checked against the originals before circulation.*
