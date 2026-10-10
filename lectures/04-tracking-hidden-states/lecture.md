# Lecture 4: Tracking Hidden States: the Kalman Filter

*Systematic Trading: Lecture Notes (MSc) · Oct 10, 2026 · Max Gnesi*

> **Draft in progress.** Sections 1–2 are written; sections 3–11 are still an outline (below). All numbers and charts come from the companion notebook [13_tracking_hidden_states.ipynb](13_tracking_hidden_states.ipynb). The Kalman material still in [Lecture 2](../02-ohlcv-and-price-smoothing/lecture.md) moves here once this lecture is complete.

Lecture 2's methods smooth the data from the bottom up; the Kalman filter works from the top down, by modelling what is hidden behind prices and updating that model with each new bar. This lecture builds the linear filter step by step, from a single level to slope and acceleration, describes what each hidden state captures, then covers extensions and the nonlinear extended and unscented filters. Companion notebook: [13_tracking_hidden_states.ipynb](13_tracking_hidden_states.ipynb).

## 1. Bottom-up versus top-down

Lecture 2's methods build a smooth line from the bottom up, by averaging bars; the Kalman filter works from the top down, by stating what is hidden behind prices and checking every new bar against that statement.

- **Bottom-up** (SMA, EMA, VWAP, KAMA): the estimate is whatever the weighting of past bars produces. The method has no notion of a trend; a trend shows up only because recent prices are higher.
- **Top-down**, an aerial view: a *state-space model* says three things. What is hidden (a level, possibly a slope and an acceleration); how the hidden quantities move from one bar to the next; and how prices relate to them (price = level + noise).

The filter then repeats one loop on every bar:

1. **Predict:** move the hidden state forward one bar with the model.
2. **Compare:** the *surprise* is the price minus the forecast.
3. **Correct:** move the state by *gain* × *surprise*. The gain is high when the filter is unsure of its own state relative to how noisy prices are, and low otherwise (Kalman, 1960).

**Example: dead reckoning.** A navigator knows the ship's speed and heading and estimates its position from them. When a noisy landmark sighting arrives, the navigator corrects the estimate partway, by how much the sighting is trusted against the reckoning. The Kalman filter does the same, with the model as the reckoning and the price as the sighting.

Neither view is better. They are different designs that make different bets about the market, and the right one is whichever fits what you want to capture. What the top-down view offers is one coherent model that delivers several things at once: a smoothed level, a trend and its change, and an uncertainty around them, a theme §10 returns to. This lecture describes what each hidden state measures and how it follows price; each state gives a *reading* (up or down), and turning readings into trading signals is the subject of Part II.

## 2. One hidden state: the level

With a single hidden state the Kalman filter is exactly an EMA, with $\alpha$ set by the ratio of two noise settings.

### 2.1 The model and the loop

The hidden *level* drifts at random from bar to bar, and each price is the level plus noise:

```math
\text{level}_t = \text{level}_{t-1} + \text{level change}_t, \qquad \text{price}_t = \text{level}_t + \text{price noise}_t
```

Here $q_{\text{level}}$ is the variance of the level change (how far the true level may wander per bar) and $r_{\text{price}}$ the variance of the price noise (how noisy a single price is). The *uncertainty* is the variance of the filter's own error about the level. Each bar:

```math
\begin{aligned}
\text{forecast}_t &= \text{level}_{t-1}, & \text{forecast uncertainty}_t &= \text{uncertainty}_{t-1} + q_{\text{level}}\\
\text{gain}_t &= \frac{\text{forecast uncertainty}_t}{\text{forecast uncertainty}_t + r_{\text{price}}}, & \text{surprise}_t &= \text{price}_t - \text{forecast}_t\\
\text{level}_t &= \text{forecast}_t + \text{gain}_t \cdot \text{surprise}_t, & \text{uncertainty}_t &= (1 - \text{gain}_t)\cdot\text{forecast uncertainty}_t
\end{aligned}
```

### 2.2 Why it is an EMA

Rearranging the correction gives $\text{level}_t = \text{gain}\cdot\text{price}_t + (1-\text{gain})\cdot\text{level}_{t-1}$: an EMA whose $\alpha$ is the gain. After a few bars the gain settles to a constant: the steady forecast uncertainty $u$ solves $u^2 - q_{\text{level}}\,u - q_{\text{level}}\,r_{\text{price}} = 0$, and the gain is $u/(u + r_{\text{price}})$. With $q_{\text{level}}/r_{\text{price}} = 1/6$ the steady gain is exactly $1/3$, the $\alpha$ of EMA(5).

**Worked by hand on Lecture 2's toy series** ($q_{\text{level}}/r_{\text{price}} = 1/6$, started at its steady uncertainty), bar 7, the spike:

| Step | Value |
|---|---|
| Forecast (yesterday's level) | 101.062 |
| Surprise | 108.5 − 101.062 = 7.438 |
| Gain | 0.3333 |
| New level | 101.062 + 0.3333 × 7.438 = 103.541 |

That is EMA(5)'s 103.54 from [Lecture 2, §7.1](../02-ohlcv-and-price-smoothing/lecture.md#71-toy-series-one-spike-on-heavy-volume); the notebook checks every bar of the series and they agree exactly ([chart C.1](#c1-predict-compare-correct-2)). Started with a wide uncertainty instead, the gain begins near 1, so the first prices are trusted almost fully, and settles within a few bars ([chart C.2](#c2-only-the-ratio-matters-23)).

### 2.3 Only the ratio matters

Multiply both noise settings by the same constant and the estimates do not change at all: the gain depends only on $q_{\text{level}}/r_{\text{price}}$. Ten prices filtered twice:

| Bar | Price | Level, $(q_{\text{level}}, r_{\text{price}}) = (1, 4)$ | Level, $(10, 40)$ | Gain, both | Uncertainty band ±1 sd, $(1, 4)$ | Band, $(10, 40)$ |
|---|---|---|---|---|---|---|
| 1 | 101 | 100.556 | 100.556 | 0.556 | 1.49 | 4.71 |
| 4 | 104 | 102.036 | 102.036 | 0.398 | 1.26 | 3.99 |
| 9 | 110 | 107.633 | 107.633 | 0.390 | 1.25 | 3.95 |

Only the band rescales, by $\sqrt{10}$. The result is exact when the starting uncertainty is scaled by the same factor; with an unscaled start the agreement is approximate during warm-up and exact once the start is forgotten ([chart C.2](#c2-only-the-ratio-matters-23)).

**Example: a thermometer.** One setting says how far the room temperature can drift per hour, the other how noisy the thermometer is. Double both and you trust a reading exactly as much as before: the estimate is unchanged, you are only less sure in absolute terms.

## Sections still to write (outline)

3. **Adding a slope: the core model.** Level + slope on log price, with a diagonal $Q$ so the level may jump by itself (prices gap); the alternative $Q$ derived from one noise level, compared on a price jump. Holt's method in steady state; zero lag on steady trends, overshoot after jumps. Unlike any positive-weight average, its level can sit above price while the market is still rising, because it extrapolates the slope.
4. **Adding acceleration.** Over one bar the level moves by slope $+\tfrac12\,$acceleration, so acceleration moves both the slope and the level, changing where the filter sits relative to price. Acceleration as a candidate early warning of regime change, judged on lead time against false alarms; the noise each extra derivative brings.
5. **Design versus tuning.** Two separate choices. The *design* (which states the model has) decides, for every parameter setting, which kind of motion it follows with no lasting gap and whether it overshoots a jump. The *tuning* ($Q$ and $R$, of which only the ratio matters) sets only the speed. Prototype check at a slow and a very fast setting:

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
6. **Starting the filter.** The starting uncertainty $P_0$, the diffuse start, warm-up length, and what to store to run it live.
7. **Extensions and what each changes.** A robust update for fat-tailed surprises; $R$ per bar from the bar's range; a damped slope. Each profiled with the market conditions of §9 (what it gains, what it gives up), not ranked; early single-asset results are preliminary.
8. **Nonlinear models: the extended and unscented filters, in depth.** On a case where the nonlinearity is real: hidden volatility estimated from daily ranges (range $\approx \sqrt{8/\pi}\,\sigma$, Lecture 3). Linearisation versus sigma points; taking logs makes the model nearly linear (Alizadeh, Brandt and Diebold, 2002), so transform first and use the UKF only when you cannot; what neither fixes (fat tails, regime breaks).
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

### C.2 Only the ratio matters (§2.3)

![Gain and level with uncertainty bands for (q, R) = (1, 4) and (10, 40)](figures/c02_ratio_invariance.png)

The gain starts near 1 and settles within a few bars; it is the same at both scales, and so is the level. Only the uncertainty band is wider at the larger scale.

### C.5 Three designs: states and readings

![Three Kalman models matched on memory: level, slope, acceleration and one signal per state, QQQ 2021–2023](figures/c05_three_designs.png)

The level-only filter lags price; the level + slope and three-state levels lead it, falling below price earlier in the 2022 decline and rising above it in rebounds. Acceleration turned negative before the November 2021 peak and positive ahead of the slope in mid-2022, but also wobbled around zero at other times: the false alarms the evaluation must count.

### C.6 The dials

![Level, slope and acceleration for four noise settings of the three-state filter, QQQ 2020](figures/c06_dials.png)

Each setting raises one entry of $Q$ a hundredfold from the balanced case. Emphasising the slope makes it turn within days at the 2020 turning points but flip sign far more often; emphasising acceleration makes the slope and level overshoot. The settings are illustrative, not estimated.
