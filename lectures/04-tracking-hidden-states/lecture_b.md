# Lecture 4b: Tracking Hidden States: the Kalman Filter

*Systematic Trading: Lecture Notes (MSc) · Oct 11, 2026 · Max Gnesi · draft, written section by section*

Lecture 2 smoothed prices from the bottom up, by averaging past bars. The Kalman filter works from the top down: it states a model of the quantities hidden behind prices (a level, and possibly a trend and its acceleration) and revises its estimate of them as each new bar arrives. This lecture builds the linear filter from a single level up to trend speed and acceleration, examines the information each hidden state carries, and covers the nonlinear extensions, the extended and unscented filters, for tracking unobserved volatility. Companion notebook: [04_tracking_hidden_states.ipynb](04_tracking_hidden_states.ipynb).

## 1. From averaging to modelling

Every method of Lecture 2 ends up as a weighted average of past prices, and in steady state so does the Kalman filter. The difference lies in where the weights come from and in what the filter carries besides an average. This section sets out what genuinely distinguishes the filter, the blueprint of its model, the three designs used in this lecture side by side, and the three steps it applies to every bar.

### 1.1 What sets the Kalman filter apart

Adapting to the data is not what distinguishes it. Several methods of Lecture 2 already adapt: the EMA weights recent bars more, KAMA speeds up when the market trends, VWAP weights bars by their volume. The standard Kalman filter, by contrast, does not adapt to the data at all once it has warmed up. What does distinguish it appears dimension by dimension in Table 1.1.

**Table 1.1. Bottom-up averages and the top-down Kalman filter**

| Dimension | Bottom-up (SMA, EMA, KAMA, VWAP) | Top-down (Kalman filter) |
|---|---|---|
| **What it estimates** | **One line:** the level, smoothed directly from past prices. A trend must be approximated separately, for instance from differences of averages | **One to three hidden states:** level; level and slope; level, slope and acceleration. Prices are treated as noisy observations of them |
| **Joint estimation** | **None:** separate averages run in isolation, with disconnected parameters, and can contradict each other | **Joint:** one surprise moves every hidden quantity, through one gain vector $`K_t`$ and one covariance matrix $`P_t`$, so the estimates stay consistent |
| **What gives a bar its influence** | **A rule:** recency (EMA), volume (VWAP) or trend efficiency (KAMA); a bar counts because it is recent, heavy or part of a clean trend | **Its surprise:** a bar moves the estimate in proportion to how far it lands from the forecast, scaled by a gain derived from the model; a bar on the forecast changes nothing |
| **Window and memory** | **A fixed window** of N bars (SMA), or an infinite, exponentially fading memory (EMA) | **No window:** an infinite, exponentially fading memory, as for an EMA, with a separate memory for each hidden quantity, set through $`Q`$ relative to $`r`$ (§5) |
| **Forecast and lag** | **Flat:** the forecast is today's average, so the line lags any trend | **Along the trend:** $`\ell_t + s_t + \tfrac12 a_t`$, so with a slope state there is no lasting lag on a steady trend |
| **Uncertainty and statistics** | **None:** a point estimate only | **A covariance matrix $`P_t`$:** a confidence band around every hidden quantity; a test of whether a bar is unusual (its surprise against $`\sqrt{S_t}`$); and the likelihood of the data, from which the noise settings can be estimated (§5) |

Every row except the window is genuinely distinctive. One nuance concerns surprise: an EMA also updates by the gap between price and its own last value, which is why the level-only filter is an EMA (§2). The difference appears once a trend enters the forecast, because the surprise is then measured against the projected trend and moves the trend as well.

Three properties are often claimed and do not hold for the standard filter. It does not widen its uncertainty and react faster when markets turn volatile: its uncertainty and its gain depend only on the noise settings and the starting uncertainty, never on the prices, so the whole sequence of gains could be computed before the first price arrives (Benhamou, 2018); it reacts to volatility only when its noise is made to depend on the data (§7). Its infinite, exponentially fading memory is not distinctive either: an EMA has the same. And it is not optimal in general: it is the best possible estimator when its model is true, the best linear one when only the model's variances are right, and otherwise a well-defined smoother.

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

**Table 1.4. The first 500 bars of LS on QQQ** (log closes from 10 March 1999; $`r = 10^{-4}`$, a 1% daily price noise; $`q_\ell = 0.1\,r`$ and $`q_s = 5.3 \times 10^{-6}\,r`$, the long-horizon settings of §6, under which the slope remembers like EMA(252); start $`x_0`$ = (first price, 0), $`P_0 = I`$; notebook §2b, which prints every matrix and vector of the first three bars)

| Bar | Date | Price | Forecast | Surprise $`e_t`$ | Gain on level | Gain on slope | Level | Slope (% a year) | Standard deviation of slope (% a year) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 Mar 1999 | 42.98 | 42.98 | 0.00% | 1.000 | 0.500 | 42.98 | 0 | 17,820 |
| 2 | 11 Mar 1999 | 43.19 | 42.98 | +0.49% | 1.000 | 0.999 | 43.19 | +123 | 365 |
| 3 | 12 Mar 1999 | 42.14 | 43.40 | −2.95% | 0.839 | 0.500 | 42.34 | −249 | 187 |
| 10 | 23 Mar 1999 | 41.09 | 43.28 | −5.20% | 0.416 | 0.059 | 42.36 | −60 | 39 |
| 100 | 30 Jul 1999 | 47.64 | 48.60 | −2.00% | 0.279 | 0.003 | 48.33 | +30 | 8.9 |
| 500 | 1 Mar 2001 | 41.08 | 42.11 | −2.49% | 0.275 | 0.002 | 41.82 | −71 | 6.9 |

Three phases are visible. On bar 1 the gain on the level is 1: the first price simply overwrites the starting guess. On bar 2 the gain on the slope is close to 1 as well, so the slope is set to the first daily change, 0.49%, or 123% a year: one observation's worth of trend. From then on both gains fall as evidence accumulates. The slope still swings widely (−249% a year on bar 3), but its standard deviation of 187% a year says that the estimate means little yet. By bar 100 the gains have nearly settled and the slope's standard deviation is under 9% a year; by bar 500 the gains are constant to the third decimal, the steady state in which the filter is a fixed weighted average of past prices. As §1.1 noted, the gain column would be the same for any prices.

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
| **Outputs and extensions** | `states`, `sds` | $`x_{t\mid t}`$, $`\sqrt{\mathrm{diag}\,P_{t\mid t}}`$ | $`T \times n`$ | The history of the estimates and of their standard deviations, for charts and readings |
| | `z` | $`e_t / \sqrt{S_t}`$ | scalar | The normalised surprise: should look like standard normal noise if the model fits (§6) |
| | `cap`, `z_var` | — | scalar | The robust update: caps surprises beyond a multiple of their recent typical size (§7) |
| | `r_series` | $`r_t`$ | $`T`$ | Price noise that changes bar by bar, for instance with the day's range (§7) |
| | `damping` | entry of $`F`$ | scalar | Lets the slope fade by a fixed share each bar (§7) |

Only the first layer is the model. The second is the machinery of Table 1.3, the same for every design. The third is where most practical mistakes are made, so it deserves its own table.

**Table 1.6. Setting what the blueprint leaves open**

| Choice | How it is set in practice | Where in this lecture |
|---|---|---|
| The design: $`F`$ and $`H`$ | A modelling decision: which hidden quantities to track (level; level and slope; level, slope and acceleration) | §2–4 |
| The scale of $`Q`$ and $`r`$ | Irrelevant on its own: only the ratios of the $`q`$ to $`r`$ matter, so $`r`$ can be fixed at 1 | §2.4 |
| The ratios of the $`q`$ to $`r`$ | One of three routes: match the memory of a known average (for instance give the slope the memory of EMA(252)); estimate them by maximum likelihood, choosing the values under which the observed surprises are most probable; or tune them to a trading objective, at a high risk of overfitting (Benhamou, 2018) | §5, §6 |
| The start: $`x_0`$ and $`P_0`$ | Level at the first price, slope and acceleration at zero, with a large $`P_0`$ so that the first prices overwrite the guess | §6 |
| The burn-in | Load one to two horizons of history before the evaluation starts | §6 |


## References (so far)

- Benhamou, E. (2018). Kalman filter demystified: from intuition to probabilistic graphical model to real case in financial markets. arXiv:1811.11618. — the gain sequence does not depend on the observations (§1.1); noise parameters tuned to a trading objective (§1.5).
