# Lecture 4b: Tracking Hidden States: the Kalman Filter

*Systematic Trading: Lecture Notes (MSc) · Oct 11, 2026 · Max Gnesi · draft, written section by section*

Lecture 2 smoothed prices from the bottom up, by averaging past bars. The Kalman filter works from the top down: it states a model of the quantities hidden behind prices (a level, and possibly a trend and its acceleration) and revises its estimate of them as each new bar arrives. This lecture builds the linear filter from a single level up to trend speed and acceleration, examines the information each hidden state carries, and covers the nonlinear extensions, the extended and unscented filters, for tracking unobserved volatility. Companion notebook: [04_tracking_hidden_states.ipynb](04_tracking_hidden_states.ipynb).

## 1. From averaging to modelling

Every method of Lecture 2 ends up as a weighted average of past prices, and in steady state so does the Kalman filter. The difference lies in where the weights come from and in what the filter carries besides an average. This section sets out what genuinely distinguishes the filter, the blueprint of its model, the three designs used in this lecture side by side, and the three steps it applies to every bar.

### 1.1 What sets the Kalman filter apart

Adapting to the data is not what distinguishes it: the EMA already favours recent bars, KAMA speeds up in trends, VWAP weights by volume. Four things do.

**Table 1.1. Bottom-up averages and the top-down Kalman filter: the highlights**

| | Bottom-up (SMA, EMA, KAMA, VWAP) | Top-down (Kalman filter) |
|---|---|---|
| **What it estimates** | **The level only.** A trend needs a separate average | **As many as the design specifies:** the level alone, or the level with a slope, or with a slope and acceleration, all estimated jointly from the same surprises |
| **What gives a bar its influence** | **Recency, volume or trend efficiency** | **Its surprise:** how far the bar lands from the forecast |
| **Forecast and lag** | **Flat,** so the line lags every trend | **Along the trend,** so there is no lasting lag on a steady trend |
| **Uncertainty** | **None** | **A confidence band for every hidden quantity,** a test for unusual bars, and a likelihood for calibrating the model |

Each of these is built up in the sections that follow.

### 1.2 The blueprint

Every design in this lecture is an instance of one pair of equations, a linear Gaussian state-space model:

```math
\begin{aligned}
x_t &= F\,x_{t-1} + w_t, \qquad w_t \sim N(0,\ Q) \qquad &\text{(state equation)}\\
y_t &= H\,x_t + v_t, \qquad v_t \sim N(0,\ r) \qquad &\text{(observation equation)}
\end{aligned}
```

**Table 1.2. The symbols of the blueprint**

| Symbol | Mathematical role | Financial meaning |
|---|---|---|
| $`y_t`$ | Observation at bar $`t`$ | The log price, the only quantity the market shows |
| $`x_t`$ | State vector, $`n \times 1`$ | The hidden quantities: the level and, in larger designs, the slope and the acceleration. Its size $`n`$ is a modelling choice |
| $`F`$ | Transition matrix, $`n \times n`$ | How the hidden quantities move from one bar to the next, for instance the level drifting by the slope |
| $`w_t`$, $`Q`$ | State noise and its covariance | Genuine, persistent changes in the hidden quantities: a revaluation, a shift in the trend |
| $`H`$ | Observation matrix, $`1 \times n`$ | Which hidden quantity the price reveals: in every design here, the level alone |
| $`v_t`$, $`r`$ | Price noise and its variance | The part of each price that does not persist (§2.1) |

A control term is sometimes added to the state equation for inputs the user sets, such as an engine's thrust. A trader cannot set prices, so it is absent here.

### 1.3 Three designs, side by side

The designs differ only in the size of $`x_t`$ and in $`F`$, $`H`$ and $`Q`$. With one bar as the unit of time, and $`\ell_t`$, $`s_t`$ and $`a_t`$ for the level, the slope and the acceleration:

```math
\begin{array}{r|c|c|c}
 & \text{L: level only} & \text{LS: level + slope} & \text{LSA: level + slope + acceleration} \\ \hline
x_t & \begin{pmatrix}\ell_t\end{pmatrix} & \begin{pmatrix}\ell_t\\ s_t\end{pmatrix} & \begin{pmatrix}\ell_t\\ s_t\\ a_t\end{pmatrix} \\[3ex]
F & \begin{pmatrix}1\end{pmatrix} & \begin{pmatrix}1 & 1\\ 0 & 1\end{pmatrix} & \begin{pmatrix}1 & 1 & \tfrac12\\ 0 & 1 & 1\\ 0 & 0 & 1\end{pmatrix} \\[3ex]
H & \begin{pmatrix}1\end{pmatrix} & \begin{pmatrix}1 & 0\end{pmatrix} & \begin{pmatrix}1 & 0 & 0\end{pmatrix} \\[2ex]
Q & \begin{pmatrix}q_\ell\end{pmatrix} & \begin{pmatrix}q_\ell & 0\\ 0 & q_s\end{pmatrix} & \begin{pmatrix}q_\ell & 0 & 0\\ 0 & q_s & 0\\ 0 & 0 & q_a\end{pmatrix} \\[3ex]
\text{forecast of } y_{t+1} & \ell_t & \ell_t + s_t & \ell_t + s_t + \tfrac12 a_t
\end{array}
```

Each design adds one hidden quantity, one row and column to $`F`$ and $`Q`$, and one term to the forecast. The first row of $`F`$ is the forecast of the level: flat for L, along the trend for LS, along a bending trend for LSA. Each $`q`$ sets how much its hidden quantity may change per bar, relative to the price noise $`r`$. Sections 2, 3 and 4 build the designs one at a time.

### 1.4 One bar of the filter: predict, compare, correct

**Table 1.3. The recursion, applied to every bar**

| Step | Calculation | Financial meaning |
|---|---|---|
| 1. Predict the state | $`x_{t\mid t-1} = F\,x_{t-1\mid t-1}`$ | Project yesterday's estimate one bar ahead: the level, moved by the trend if there is one |
| 2. Predict its uncertainty | $`P_{t\mid t-1} = F\,P_{t-1\mid t-1}\,F^\top + Q`$ | The projection is less certain than yesterday's estimate, because the hidden quantities may have moved overnight |
| 3. Compare | $`e_t = y_t - H\,x_{t\mid t-1}`$ | The surprise: today's price minus the forecast |
| 4. Size the surprise | $`S_t = H\,P_{t\mid t-1}\,H^\top + r`$ | How large a surprise is normal: forecast uncertainty plus price noise |
| 5. Compute the gain | $`K_t = P_{t\mid t-1}\,H^\top / S_t`$ | For each hidden quantity, the share of the surprise to accept as genuine |
| 6. Correct the state | $`x_{t\mid t} = x_{t\mid t-1} + K_t\,e_t`$ | Move each hidden quantity by its share of the surprise |
| 7. Correct its uncertainty | $`P_{t\mid t} = (I - K_t H)\,P_{t\mid t-1}`$ | Having seen today's price, the filter is more certain where the hidden quantities stand |

Here $`x_{t\mid t-1}`$ is the estimate before today's price is seen and $`x_{t\mid t}`$ the estimate after; $`P`$ is the uncertainty of the estimate, the covariance of its error. The gain $`K_t`$ is a vector with one entry per hidden quantity, so a single price surprise updates the level, the slope and the acceleration at once. This is how the filter learns a trend it never observes: when prices keep beating the forecast, the surprises are persistently positive, and each one nudges the slope up by its share.

**Table 1.4. The first 500 bars of LS on QQQ** (log closes from 10 March 1999; $`r = 10^{-4}`$, a 1% daily price noise; $`q_\ell = 0.1\,r`$ and $`q_s = 5.3 \times 10^{-6}\,r`$, settings whose choice is explained in §5; start $`x_0`$ = (first price, 0), $`P_0 = I`$; notebook §2b, which prints every matrix and vector of the first three bars)

| Bar | Date | Price | Forecast | Surprise $`e_t`$ | Gain on level | Gain on slope | Level | Slope (% a year) | Standard deviation of slope (% a year) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 Mar 1999 | 42.98 | 42.98 | 0.00% | 1.000 | 0.500 | 42.98 | 0 | 17,820 |
| 2 | 11 Mar 1999 | 43.19 | 42.98 | +0.49% | 1.000 | 0.999 | 43.19 | +123 | 365 |
| 3 | 12 Mar 1999 | 42.14 | 43.40 | −2.95% | 0.839 | 0.500 | 42.34 | −249 | 187 |
| 10 | 23 Mar 1999 | 41.09 | 43.28 | −5.20% | 0.416 | 0.059 | 42.36 | −60 | 39 |
| 100 | 30 Jul 1999 | 47.64 | 48.60 | −2.00% | 0.279 | 0.003 | 48.33 | +30 | 8.9 |
| 500 | 1 Mar 2001 | 41.08 | 42.11 | −2.49% | 0.275 | 0.002 | 41.82 | −71 | 6.9 |

Three phases are visible. On bar 1 the gain on the level is 1: the first price simply overwrites the starting guess. On bar 2 the gain on the slope is close to 1 as well, so the slope is set to the first daily change, 0.49%, or 123% a year: one observation's worth of trend. From then on both gains fall as evidence accumulates. The slope still swings widely (−249% a year on bar 3), but its standard deviation of 187% a year says that the estimate means little yet. By bar 100 the gains have nearly settled and the slope's standard deviation is under 9% a year; by bar 500 the gains are constant to the third decimal, the steady state in which the filter is a fixed weighted average of past prices. The gain columns depend only on the noise settings and the start, never on the prices: any price series would produce the same gains. The standard filter therefore does not react faster when markets turn volatile; that requires noise that depends on the data (§7).

**The filter runs online.** Each bar needs only three things: yesterday's estimate $`x_{t-1\mid t-1}`$, its uncertainty $`P_{t-1\mid t-1}`$ and today's price. Everything the filter knows about the past is condensed into those two objects, so live, the price can be discarded once it has been processed; a backtest simply loops through the history one bar at a time. A full price history is needed in only two cases. The first is estimating the noise settings from the data (§5). The second is *smoothing*: running a second pass backwards through the history so that each past estimate also uses the prices that came after it (Rauch, Tung and Striebel, 1965). Smoothed estimates are useful for describing the past, but they look ahead, so they must never be used to generate readings in a backtest.

### 1.5 From the blueprint to the code

The blueprint names four objects: $`F`$, $`H`$, $`Q`$ and $`r`$. An implementation handles many more, because the filter needs working quantities of its own and a set of choices the blueprint leaves open. They fall into three layers, and keeping them apart is the easiest way to read any Kalman filter code, including the companion notebook's `kalman()` function.

**Table 1.5. Every object in an implementation, by layer** (names as in the notebook)

| Layer | In the notebook | Symbol | Shape | What it is |
|---|---|---|---|---|
| **Model: what is assumed** | `transition` | $`F`$ | $`n \times n`$ | How the hidden quantities move from bar to bar; fixed by the design (`design()`) |
| | `observe` | $`H`$ | $`1 \times n`$ | Which hidden quantity the price reveals: $`(1, 0, \dots, 0)`$ |
| | `Q` (from `q_diag`, or `full_q`) | $`Q`$ | $`n \times n`$ | How much each hidden quantity may change per bar |
| | `r_price` | $`r`$ | scalar | Variance of the price noise |
| **Filter: computed on every bar** | `state` | $`x_{t\mid t}`$ | $`n`$ | The current estimate of the hidden quantities: level, slope, acceleration |
| | `uncertainty` | $`P_{t\mid t}`$ | $`n \times n`$ | Variances of the estimation errors on the diagonal, their covariances off it |
| | `forecast` | $`H\,x_{t\mid t-1}`$ | scalar | The price expected before today's bar is seen |
| | `surprise` | $`e_t`$ | scalar | Today's price minus the forecast |
| | `surprise_var` | $`S_t`$ | scalar | The variance a surprise should have if the model is right |
| | `gain` | $`K_t`$ | $`n`$ | The share of the surprise each hidden quantity accepts |
| **Settings: chosen by the user** | `start_state` | $`x_0`$ | $`n`$ | The starting guess: first price as level, zero slope and acceleration |
| | `start_uncertainty` | $`P_0`$ | $`n \times n`$ | How much the starting guess is trusted; large means a diffuse start |
| | `Q_REL`, `q_scale` | ratios within $`Q`$ | — | The relative speeds of level, slope and acceleration, and their overall scale |
| **Outputs** | `states`, `sds` | $`x_{t\mid t}`$, $`\sqrt{\mathrm{diag}\,P_{t\mid t}}`$ | $`T \times n`$ | The history of the estimates and of their standard deviations, for charts and readings |

Only the first layer is the model. The second is the machinery of Table 1.3, the same for every design. The third is chosen by the user, and the rest of the lecture shows how; the code's remaining arguments belong to the extensions of §7.

**Table 1.6. What the user must choose, and where the lecture covers it**

| Choice | Covered in |
|---|---|
| The design: which hidden quantities to track ($`F`$ and $`H`$) | §2–4 |
| How fast each hidden quantity may change, relative to the price noise ($`Q`$ and $`r`$) | §5 |
| The start ($`x_0`$, $`P_0`$) and how much history to load first | §6 |

## References (so far)

- Rauch, H.E., Tung, F. and Striebel, C.T. (1965). Maximum likelihood estimates of linear dynamic systems. *AIAA Journal* 3(8), 1445–1450. — the smoother (§1.4).
