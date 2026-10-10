# Lecture 4: Tracking Hidden States: the Kalman Filter

*Systematic Trading: Lecture Notes (MSc) · Oct 10, 2026 · Max Gnesi*

> **Draft outline for review.** Sections below state what each part will contain; the text is not written yet. All numbers and charts come from the companion notebook [13_tracking_hidden_states.ipynb](13_tracking_hidden_states.ipynb); the text is being written section by section. The Kalman material still in [Lecture 2](../02-ohlcv-and-price-smoothing/lecture.md) moves here when this lecture is written.

Lecture 2's methods smooth the data from the bottom up; the Kalman filter works from the top down, by modelling what is hidden behind prices and updating that model with each new bar. This lecture builds the linear filter step by step, from a single level to slope and acceleration, shows that each hidden state carries its own trading signal, then covers extensions and the nonlinear extended and unscented filters.

**Purpose.** A trend filter should find structural, long-horizon trends that are robust to daily noise. No filter is best: each captures different behaviour, so the lecture profiles what each one captures and when that helps or hurts, rather than ranking them. Predicting tomorrow's price is not the goal.

## Planned sections

1. **Bottom-up versus top-down.** Smoothing averages the data; a state-space model says what is hidden, how it moves, and how prices relate to it. The predict, compare, correct loop in plain words.
2. **One hidden state (level only).** The recursion with named variables (*level*, *q_level*, *r_price*, *uncertainty*, *gain*, *surprise*), worked by hand on the toy series. Why it settles into exactly an EMA. Why only the ratio $q/R$ matters (same estimates at any common scale, only the uncertainty bands rescale).
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
10. **Side by side.** The three models and their three signal families: position (price versus level), slope (direction), acceleration (strengthening or fading) ([chart C.5](#c5-three-models-states-and-signals)); comparison with the Lecture 2 methods; practical notes and common mistakes.
11. **Summary, exercises and reading.** References verified before citing.

## Preliminary observations (prototype, QQQ)

Three models matched on memory to EMA(20) (variance reduction 1/20), so that differences come from structure, not from smoothing more or less. How often each pair of long/short signals agrees, QQQ 1999–2026:

| | Position signals | Slope signals | Acceleration |
|---|---|---|---|
| **Position signals** | 78–91% | 45–68% | 50–58% |
| **Slope signals** | 45–68% | 89% | 70–75% |

Signals from the same state largely agree; signals from different states agree only about half to two-thirds of the time, i.e. three distinct signal families. This is agreement, not performance: whether any of them, or a combination, earns money is tested in Part II.

## Appendix: main charts (prototypes)

### C.5 Three models: states and signals

![Three Kalman models matched on memory: level, slope, acceleration and one signal per state, QQQ 2021–2023](figures/c05_three_designs.png)

The level-only filter lags price; the level + slope and three-state levels lead it, falling below price earlier in the 2022 decline and rising above it in rebounds. Acceleration turned negative before the November 2021 peak and positive ahead of the slope in mid-2022, but also wobbled around zero at other times: the false alarms the evaluation must count.

### C.6 The dials

![Level, slope and acceleration for four noise settings of the three-state filter, QQQ 2020](figures/c06_dials.png)

Each setting raises one entry of $Q$ a hundredfold from the balanced case. Emphasising the slope makes it turn within days at the 2020 turning points but flip sign far more often; emphasising acceleration makes the slope and level overshoot. The settings are illustrative, not estimated.
