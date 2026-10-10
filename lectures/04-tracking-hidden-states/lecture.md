# Lecture 4: Tracking Hidden States: the Kalman Filter

*Systematic Trading: Lecture Notes (MSc) · Oct 10, 2026 · Max Gnesi*

> **Draft in progress.** Sections 1–2 are written; sections 3–11 are still an outline (below). All numbers and charts come from the companion notebook [13_tracking_hidden_states.ipynb](13_tracking_hidden_states.ipynb). The Kalman material still in [Lecture 2](../02-ohlcv-and-price-smoothing/lecture.md) moves here once this lecture is complete.

Lecture 2's methods smooth the data from the bottom up; the Kalman filter works from the top down, by modelling what is hidden behind prices and updating that model with each new bar. This lecture builds the linear filter step by step, from a single level to slope and acceleration, describes what each hidden state captures, then covers extensions and the nonlinear extended and unscented filters. Companion notebook: [13_tracking_hidden_states.ipynb](13_tracking_hidden_states.ipynb).

## 1. Bottom-up versus top-down

The methods of Lecture 2 construct a smooth line from the bottom up, as weighted averages of past bars. The Kalman filter proceeds from the top down: it specifies a model of the quantities hidden behind prices and revises its estimate of them as each bar arrives.

- **Bottom-up** (SMA, EMA, VWAP, KAMA). The estimate is a weighted average of past prices and nothing more. These methods contain no explicit representation of a trend: a rise appears in the average only once rising prices have accumulated in its window, which is the source of their lag.
- **Top-down.** A *state-space model* specifies three elements: the hidden quantities (the *state*), how the state evolves from one bar to the next, and how observed prices relate to it. When the state includes a slope, the trend becomes an explicit quantity: the model carries it from bar to bar and uses it to project the level forward. A rising market is then represented directly, as a positive slope, rather than inferred from accumulated past prices. With a level alone the model has no such component and reduces exactly to an EMA (§2); the slope enters in §3.

| Dimension | Bottom-up (SMA, EMA, VWAP, KAMA) | Top-down (Kalman filter) |
|---|---|---|
| Core idea | Average past prices; the trend is whatever the average shows | Model the hidden level, slope and acceleration; check each bar against the model |
| What it knows | Past prices (and volume, for VWAP); no notion of trend speed | An explicit model of how level, slope and acceleration move from bar to bar |
| How it treats a bar | An ingredient, weighted and added to the average | Evidence, compared with the forecast and accepted in proportion to the gain |
| How it reacts | Follows: moves only as new prices pull the average | Projects the current trend one bar ahead, then corrects by the surprise |
| Weights on past prices | All positive: never overshoots, always lags a trend | Slope designs put negative weight on old prices: no lag on a steady trend, overshoot after jumps |
| Uncertainty | None | An uncertainty for every hidden state |

The filter applies the same three steps to every bar:

| Step | What the filter does |
|---|---|
| Predict | Projects the state one bar ahead, using the model of how it evolves |
| Compare | Computes the *surprise*: the observed price minus the forecast |
| Correct | Revises the state by *gain* × *surprise*. The gain is large when the filter's uncertainty about its state is large relative to the price noise, and small otherwise (Kalman, 1960) |

**Example: navigation.** A navigator estimates position from known speed and heading (the model) and adjusts that estimate when a landmark is sighted (the observation). The size of the adjustment depends on the relative reliability of the reckoning and the sighting. The Kalman filter applies the same principle, with prices as the observations.

The two approaches are not ranked. They embody different assumptions about the data, and the appropriate choice depends on what the analysis is meant to capture. The distinctive feature of the top-down approach is that a single model delivers several quantities at once: a level, a trend and its rate of change, and the uncertainty around each (§10). Throughout this lecture each hidden state yields a *reading*, up or down; the use of readings as trading signals is treated in Part II.

## 2. One hidden state: the level

With a single hidden state, the Kalman filter is an EMA whose smoothing constant is set by the ratio of two noise variances.

### 2.1 The model

The hidden level moves at random from bar to bar, and each price equals the level plus noise:

```math
\text{level}_t = \text{level}_{t-1} + \text{level change}_t, \qquad \text{price}_t = \text{level}_t + \text{price noise}_t
```

| Quantity | Financial meaning |
|---|---|
| *level* | The underlying price: where the market is, net of noise |
| $q_{\text{level}}$ | Variance of genuine changes in the underlying price per bar: news, revaluation, persistent shifts in demand |
| $r_{\text{price}}$ | Variance of the noise around it: bid-ask bounce, temporary order-flow pressure, overshoots that reverse |
| *uncertainty* | How unsure the filter is about the underlying price (variance of its error) |
| *gain* | The share of today's unexpected move treated as genuine information rather than noise |
| *surprise* | Today's unexpected move: the price minus the forecast |

### 2.2 The recursion, step by step

| Step | Calculation | Financial interpretation |
|---|---|---|
| 1. Predict the level | $\text{forecast}_t = \text{level}_{t-1}$ | With no new trades, the best estimate of today's underlying price is yesterday's |
| 2. Predict the uncertainty | $\text{forecast uncertainty}_t = \text{uncertainty}_{t-1} + q_{\text{level}}$ | Overnight, news may have moved the underlying price, so the estimate becomes less certain by $q_{\text{level}}$ |
| 3. Compute the gain | $\text{gain}_t = \dfrac{\text{forecast uncertainty}_t}{\text{forecast uncertainty}_t + r_{\text{price}}}$ | How much of today's move to believe: near 1 when genuine changes dominate (a fast-moving market), near 0 when noise dominates (a market that mostly jitters around its value) |
| 4. Compare | $\text{surprise}_t = \text{price}_t - \text{forecast}_t$ | Today's unexpected move |
| 5. Correct the level | $\text{level}_t = \text{forecast}_t + \text{gain}_t \cdot \text{surprise}_t$ | Accept the believed part of the move, discard the rest as noise |
| 6. Update the uncertainty | $\text{uncertainty}_t = (1 - \text{gain}_t)\cdot\text{forecast uncertainty}_t$ | Having seen today's price, the filter is more certain where the underlying price is |

### 2.3 Equivalence to the EMA

Substituting step 1 into step 5 gives $\text{level}_t = \text{gain}\cdot\text{price}_t + (1-\text{gain})\cdot\text{level}_{t-1}$, an EMA whose $\alpha$ is the gain. After a few bars the gain converges to a constant: the steady forecast uncertainty $u$ solves $u^2 - q_{\text{level}}\,u - q_{\text{level}}\,r_{\text{price}} = 0$, and the steady gain is $u/(u + r_{\text{price}})$. With $q_{\text{level}}/r_{\text{price}} = 1/6$ the steady gain is exactly $1/3$, the $\alpha$ of EMA(5).

On Lecture 2's toy series, with $q_{\text{level}}/r_{\text{price}} = 1/6$ and the filter started at its steady uncertainty, the level reproduces EMA(5) on every bar, including the 103.54 after the spike ([chart C.1](#c1-predict-compare-correct-2)). Started instead from a wide uncertainty, the gain begins close to 1, so the first prices are accepted almost in full, and converges within a few bars ([chart C.2](#c2-only-the-ratio-matters-24)).

### 2.4 Only the ratio of the noise variances matters

Scaling both noise variances by the same constant leaves the estimates unchanged, because the gain depends only on $q_{\text{level}}/r_{\text{price}}$. The same ten prices, filtered at two scales:

| Bar | Price | Level, $(q_{\text{level}}, r_{\text{price}}) = (1, 4)$ | Level, $(10, 40)$ | Gain, both | Uncertainty band ±1 sd, $(1, 4)$ | Band, $(10, 40)$ |
|---|---|---|---|---|---|---|
| 1 | 101 | 100.556 | 100.556 | 0.556 | 1.49 | 4.71 |
| 4 | 104 | 102.036 | 102.036 | 0.398 | 1.26 | 3.99 |
| 9 | 110 | 107.633 | 107.633 | 0.390 | 1.25 | 3.95 |

Only the uncertainty band changes, by a factor of $\sqrt{10}$. The equivalence is exact when the starting uncertainty is scaled by the same factor; with an unscaled start it is approximate during the warm-up and exact once the start has been forgotten ([chart C.2](#c2-only-the-ratio-matters-24)).

**Example: a thermometer.** Let one variance describe how far the room temperature can drift in an hour and the other how noisy the thermometer is. Scaling both by the same factor leaves the relative reliability of model and instrument unchanged, so the estimate is unchanged; only the stated uncertainty increases.

## Sections still to write (outline)

3. **Adding a slope.** The one-bar transition in plain words (next level = level + slope; next slope = slope) as the model's assumption; the matrix form with every entry given a financial meaning; diagonal versus derived $Q$ (chart C.4); Holt's method in steady state; negative weights (chart C.3); why the level can sit above price in a rising market.
4. **Adding acceleration.** Next level = level + slope + ½·acceleration, next slope = slope + acceleration, next acceleration = acceleration (one bar = one time step). Acceleration moves the level and the slope; early warning of regime change against false alarms; the three designs and their readings (chart C.5).
5. **Design versus tuning.** Two separate choices. The *design* (which states the model has) decides, for every parameter setting, which kind of motion it follows with no lasting gap and whether it overshoots a jump. The *tuning* ($Q$ and $R$, of which only the ratio matters) sets only the speed. Prototype check at a slow and a very fast setting: Then the dials: a table of what each entry of $Q$ does to how the filter follows price (raise *q_level*, *q_slope*, *q_acceleration* or $r_{	ext{price}}$ → effect → measured cost from chart C.6).

    | Design | Price jump: overshoot | Steady trend: gap behind price | Parabolic move: gap behind price |
    |---|---|---|---|
    | Level only | None (0% at both speeds) | Fixed gap (0.99 slow, 0.095 fast) | Growing gap (2.8 → 5.8 slow, 0.28 → 0.57 fast) |
    | Level + slope | Always (20% slow, 17% fast) | None | Fixed gap (0.02 slow, 0.0006 fast) |
    | Level + slope + acceleration | Always, larger (29% slow, 23% fast) | None | None |

    Tuning shrinks a gap but never removes it; only adding a state does. Overshoot follows from the weights: positive weights on past prices can never overshoot a jump, and any negative weight forces an overshoot, because the cumulative weights must exceed one before settling back to one. Each design is a different bet about what the market is doing; none is best.

    **How each design follows price after a jump.** Because the slope designs overshoot, they turn against a move on their own when price stalls, simply by correcting their own overshoot, as if tightening a stop; the level-only design just waits for price to come to it. Prototype test, same pattern at both speeds (days on which each state points against the move):

    | State | After a jump, then flat | After a jump inside a continuing uptrend |
    |---|---|---|
    | Position, level only | Never against the move | Never against the move |
    | Position, level + slope | Turns against it early (from bar +6 to +34) | Points against it for about 150 bars |
    | Slope, level + slope | Turns against it late (from +27 to +143) | Never against the move |
    | Position, three-state | Turns first (from +3 to +15) | Points against it for about 140 bars |
    | Slope, three-state | Turns (from +13 to +61) | Points against it for 16–47 bars |
    | Acceleration | Turns early (from +9 to +43) | Points against it for about 160 bars |

    In these tests only the level + slope model's slope stayed with a trend that continued after a jump, yet still turned once the move stopped. What this means for entering and leaving positions is the subject of Part II. Then the dials *q_level*, *q_slope*, *q_acceleration* ([chart C.6](#c6-the-dials)) and matching a Kalman filter to an EMA on variance reduction.
6. **Starting and running the filter.** Warm-up phases per design measured in the notebook (no universal bar count); the starting uncertainty $P_0$ and the diffuse start (chart C.7); a best-practice table: history to load, start, what to store, matched comparisons, surprise monitoring, re-estimating $q/R$.
7. **Extensions and what each changes.** A robust update for fat-tailed surprises; $R$ per bar from the bar's range; a damped slope. Each profiled with the market conditions of §9 (what it gains, what it gives up), not ranked; early single-asset results are preliminary.
8. **Nonlinear models, in depth.** Hidden volatility from daily ranges; linearisation (EKF) versus sigma points (UKF), with a table of the unscented parameters $lpha$, $eta$, $\kappa$ and what they actually control; transform first (log range) and the outlier lesson of 6 May 2010 (chart C.10); what neither fixes (fat tails, regime breaks).
9. **What each filter captures: a profile by market condition, not a ranking.** Market conditions defined mechanically, across SPY, QQQ, GLD, AGG:

    | Market condition | Defined by | What we describe for each filter |
    |---|---|---|
    | Choppy, trendless | Low efficiency ratio (Lecture 3) | How often it flips; how much it chases noise |
    | Steady trend | High efficiency ratio, moderate slope | How far it lags; how stable its signal stays |
    | Parabolic or accelerating move | Rising slope, positive acceleration | Whether it keeps up or falls behind |
    | Regime change | Mechanically defined turning points | How early it turns; how often it warns falsely |

    Two case studies with all three designs: **the 2000 top**, a parabolic rise followed by violent counter-trend rallies all the way to the October 2002 low, the phase that whipsawed trend followers; and **the 2020 V-shaped crash and recovery**, two sharp turns in quick succession.

    The output is a pros-and-cons profile per filter and per signal family, backed by numbers per condition. Plus a time-varying hedge ratio as a bridge to stat arb (Chan, 2013).
10. **Side by side.** The three models and their three signal families: position (price versus level), slope (direction), acceleration (strengthening or fading) ([chart C.5](#c5-three-designs-states-and-readings)); comparison with the Lecture 2 methods; practical notes and common mistakes.
11. **Summary, exercises and reading.** References verified before citing.

## Preliminary observations (prototype, QQQ)

Three models matched on memory to EMA(20) (variance reduction 1/20), so that differences come from structure, not from smoothing more or less. How often each pair of long/short signals agrees, QQQ 1999–2026:

| | Position signals | Slope signals | Acceleration |
|---|---|---|---|
| **Position signals** | 78–91% | 45–68% | 50–58% |
| **Slope signals** | 45–68% | 89% | 70–75% |

Signals from the same state largely agree; signals from different states agree only about half to two-thirds of the time, i.e. three distinct signal families. This is agreement, not performance: whether any of them, or a combination, earns money is tested in Part II.

## Appendix: main charts

### C.1 Predict, compare, correct (§2)

![One hidden state on Lecture 2's toy series: price, forecast, updated level and the correction gain × surprise](figures/c01_predict_compare_correct.png)

Each bar the forecast is yesterday's level; the correction is the gain (1/3) times the surprise. On the spike at bar 7 the level moves a third of the way to the price, exactly like EMA(5).

### C.2 Only the ratio matters (§2.4)

![Gain and level with uncertainty bands for (q, R) = (1, 4) and (10, 40)](figures/c02_ratio_invariance.png)

The gain starts near 1 and settles within a few bars; it is the same at both scales, and so is the level. Only the uncertainty band is wider at the larger scale.

### C.5 Three designs: states and readings

![Three Kalman models matched on memory: level, slope, acceleration and one signal per state, QQQ 2021–2023](figures/c05_three_designs.png)

The level-only filter lags price; the level + slope and three-state levels lead it, falling below price earlier in the 2022 decline and rising above it in rebounds. Acceleration turned negative before the November 2021 peak and positive ahead of the slope in mid-2022, but also wobbled around zero at other times: the false alarms the evaluation must count.

### C.6 The dials

![Level, slope and acceleration for four noise settings of the three-state filter, QQQ 2020](figures/c06_dials.png)

Each setting raises one entry of $Q$ a hundredfold from the balanced case. Emphasising the slope makes it turn within days at the 2020 turning points but flip sign far more often; emphasising acceleration makes the slope and level overshoot. The settings are illustrative, not estimated.
