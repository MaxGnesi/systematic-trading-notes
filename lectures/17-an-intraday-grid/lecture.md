# Lecture 17: An Intraday Grid on the Tape: Swings, Runs and What a Grid Earns

*Systematic Trading: Lecture Notes (MSc) · Oct 28, 2026 · Max Gnesi*

Lecture 16 applied the tape to a trend rule, a strategy that earns when the price runs. This lecture applies it to the opposite, a grid, which earns when the price swings back, on the same five years of BTCUSDT. A grid is a strategy whose result is decided by the path between bars, so it can only be tested on the tape. The lecture asks where a grid's profit comes from, measures it with fills counted conservatively and all costs charged, and tests whether anything known in advance improves it.

> **What to take away**
>
> 1. **A grid's result has two parts:** the round trips it completes, each worth one step, and the result of the inventory it is left holding. On a price with no pattern the two cancel before costs: every dollar a grid earns comes from the price reverting at the scale of its step.
> 2. **Runs are the grid's risk.** A run is a jump spread over minutes; how much of its time the market spends running decides what a given amount of reversion pays the grid.
> 3. **On five years of BTCUSDT, with fills counted conservatively, the grid loses after costs at every step** tried, and the tape treats it worse than the same minutes in random order.
> 4. **Stepping aside after a violent hour and leaning the inventory with the trend cut the losses** without creating an edge. Where a grid's machinery pays is in lowering the cost of strategies that have an edge of their own.

## 1. How a grid earns

A grid earns one step on every round trip and loses on the inventory a run leaves it holding; this section takes the mechanics apart and follows one real day fill by fill. The rest of the lecture is organised as follows:

| § | Step | Question |
|---|---|---|
| 2 | Where the profit comes from | What does a grid earn on a price with no pattern, with jumps, with runs? |
| 3 | The tape | What does it earn on five years of BTCUSDT, after costs, and against the same minutes in random order? |
| 4 | The levers | Step, levels, stop, restart and refresh: which settings hold across a wide range? |
| 5 | Known in advance | Do a switch on volatility, a lean with the trend, a channel or the hour of the day help? |
| 6 | Next to the trend rule | Does the grid improve the trend rule of Lecture 16? |
| 7 | Where grids pay | Costs, rebates and strategies with an edge of their own |
| 8 | Summary, exercises and reading | |

### 1.1 The grid of this lecture

The grid is the classic two-sided paired grid of Lecture 16, §8: buy orders at levels below the price, sell orders at levels above it, a fixed step apart, each level re-armed only after its paired trade has filled. Its settings throughout the lecture:

| Setting | Value | Why |
|---|---|---|
| Step | 10 to 200 bp of the price at which the ladder is laid | From a few one-minute moves to about two-thirds of a day's move (daily volatility about 3%) |
| Levels | 200 bp ÷ step on each side, so the ladder reaches about 200 bp each way at every step | Every step is tested with the same reach, so a change in results comes from the step, not from the width |
| Size | The same at every level, one unit = capital ÷ number of levels on a side | A full ladder on one side is exactly the capital; Lecture 16, §8 shows the alternatives |
| Stop | One step beyond the last level | §1.3 |
| Daily close | The last second of the UTC day | §1.3 |

**The whole grid in one number.** In paired form, the grid's state is the last level it filled, and its position follows from it:

```math
q_t = -\frac{r_t - c}{s}
```

| Symbol | Meaning | Financial interpretation |
|---|---|---|
| $`q_t`$ | Position, in units (+ long, − short) | What the grid holds after its last fill |
| $`r_t`$ | Reference level: the last level filled | Where the market last traded through the grid |
| $`c`$ | Centre: the price at which the ladder was laid | The price the grid treats as fair until it is restarted |
| $`s`$ | Step, in dollars | The swing the grid is paid for |

The grid is long one unit for every step the price has fallen below the centre and short one for every step it has risen above it: a position that leans against the move. Its resting orders follow from $`r_t`$ alone: a buy one step below it and a sell one step above it, with the farther levels of the ladder resting behind them.

### 1.2 The life of a level

Each level goes through the same four states. For a level one step below the centre:

| Step | What happens | Position | What is earned |
|---|---|---|---|
| 1. Armed | A resting buy order waits at the level | 0 | — |
| 2. Filled | An aggressive seller trades below the level: the buy is filled, and a sell for the same unit is placed one step above | +1 | — |
| 3a. Paired sell fills | The price returns one step: the unit is sold, and only now is the buy at the level re-armed | 0 | One step × one unit: a round trip |
| 3b. Or the price runs on | Lower levels fill in turn; at the last level the next trade through closes every unit at the market (the stop) | up to the cap, then 0 | The loss of every unit against its own buy price |

A level never holds more than one unit, so the position is bounded by the number of levels. What is not bounded is the loss when the price runs through all of them: that is what the stop and the daily close are for.

### 1.3 Fills, exits and costs

**Fills counted conservatively.** A resting buy at a level is counted as filled only if an aggressive seller traded *below* it in that second; a resting sell only if an aggressive buyer traded above it (Lecture 14, §4.3). Touching the level is not enough: an order there would wait in a queue, and it may not be its turn. Trading through it is: every order resting at the level must then have been filled. On BTCUSDT a level that is visited is traded through more than 99.7% of the time (Lecture 14, §4.3), so the rule loses little; it rules out counting the fills that are least likely, on the turning points. The simulation runs second by second, on the highest price paid by aggressive buyers, the lowest price received by aggressive sellers and the last price in every second of the tape:

| Rule | In the simulation |
|---|---|
| A sweep through several levels | Fills all of them in the same second |
| An order re-armed by a fill | Is live from the next second, never in the same one |
| Both sides traded through in one second | The order of the trades is unknown (Lecture 14, §2): the side on which the second closed is taken, and the second is counted. Fewer than one fill in a hundred falls in such a second at a 10 bp step, and almost none at 100 bp |

**Two exits.** The **stop** fires when the position is at the cap and the price trades through one level more: every unit is closed at the worst aggressive price of that second, as a market order, and a new ladder is laid around the price (Lecture 14, §4.3 measured how far such a stop can slip). The **daily close** closes whatever is left in the last second of the UTC day, also at the market. The grid is therefore flat at the 00:00 funding settlement; it pays or receives funding at 08:00 and 16:00 on whatever it holds then (Lecture 16, §1).

**Costs.** A regular account's fees: 2 bp on every resting fill, 5 bp on every stop and close (Lecture 15, §5).

**The accounts.** Every result in this lecture is split into the same parts:

```math
\text{gross} = \underbrace{N_{\mathrm{trips}} \times s \times u}_{\text{round-trip income}} + \text{inventory result}, \qquad
\text{net} = \text{gross} - \text{maker fees} - \text{taker fees} + \text{funding}
```

| Part | How it is computed | Financial interpretation |
|---|---|---|
| Round-trip income | Round trips $`N_{\mathrm{trips}}`$ × step $`s`$ × unit size $`u`$ | What the swings paid: each unit bought and sold one step higher, or sold and bought back one step lower |
| Inventory result | Gross minus round-trip income | What the runs cost: the units closed at stops and at the daily close, against their own fill prices |
| Maker fees | 2 bp of every resting fill | The price of resting orders |
| Taker fees | 5 bp of every stop and close | The price of leaving in a hurry |
| Funding | Position × price × rate, at 08:00 and 16:00 | The cost, or income, of holding inventory through a settlement |

Round-trip income can only grow. The inventory result is where the risk sits: the grid holds inventory exactly when the price has moved away from the centre, and closes it when the move has gone furthest.

### 1.4 One day, fill by fill

Lecture 16's reference day, 12 March 2024, with a step of 50 bp and four levels on each side, on USD 100,000 of capital. The ladder was laid at the day's first price, USD 72,156, so the step was USD 360.78 and one unit was USD 25,000, or 0.3465 BTC. A round trip earned 0.3465 × 360.78 = **USD 125**.

![One day of the grid on the tape, 12 March 2024: the price, the ladder, every fill, the position, and the round-trip income, inventory result and gross result through the day](figures/17_01_grid_day.png)
<sub><b>How to read the figure.</b> <b>Top:</b> the price (the last trade of every 10 seconds); blue lines are the buy levels below each centre, pink lines the sell levels above it, the dotted line the centre, the dashed lines the stops. Blue triangles are buys filled, pink triangles sells filled, black crosses stops, after which a new ladder is laid around the price. <b>Middle:</b> the position, in units. <b>Bottom:</b> the result so far, before fees and funding: the round-trip income (orange), the inventory result (blue, the open units marked to the price) and their sum, the gross result (black).</sub>

The day falls into three parts:

| UTC | What the price did | What the grid did | Round trips | Gross result at the end |
|---|---|---|---|---|
| 00:00–16:12 | Swung within about 1.5% of the open | Bought dips and sold rallies, never more than three units in either direction | 15 | +USD 1,769 |
| 16:12–17:49 | Fell 4.0%, then rebounded 2.8% | Bought four units on the way down and was stopped; bought four more and was stopped again; sold four into the rebound and was stopped a third time | 8 | −USD 907 |
| 17:49–24:00 | Drifted up | Sold rallies; was short three units into the close | 6 | −USD 512 |

| The day's accounts, per USD 100,000 | USD |
|---|---|
| Round-trip income: 29 × 125 | +3,625 |
| Inventory result: three stops and the close | −4,137 |
| **Gross result** | **−512** |
| Maker fees: 73 resting fills | −360 |
| Taker fees: three stops and the close | −182 |
| Funding: the position held at 08:00 and 16:00 | −12 |
| **Net result** | **−1,066** |

Fifteen round trips took sixteen hours to earn USD 1,875; the run took an hour and a half to cost the inventory about twice that, USD 3,676, while its own eight round trips earned USD 1,000. This is the grid's profile in one day: small, frequent gains and rare large losses (Lecture 16, §8). The figures are ours, from a step-by-step copy of the simulator that logs every fill; its totals agree with the simulator to the last digit.

## 2. Where the profit comes from

On a price with no pattern a grid earns nothing before costs, apart from what its own fills give away; every dollar it makes comes from the price reverting at the scale of its step, and every dollar it loses from the price running. This section shows it in simulations where the truth is known, and then asks what kind of pattern a grid needs.

### 2.1 A price with no pattern

**Why nothing.** On a price that is a martingale, a price whose expected next value is its current value, no rule of buying and selling at the market price has an expected profit: whatever the rule, the expected gain on each unit held over the next instant is zero. This is a standard result of probability theory (Williams, 1991, ch. 10). A grid does not trade at the market price, however, but at its levels: when the price jumps through a buy level between two seconds, the order is filled at the level, above the price at which the market now trades. The difference is the **gap**, what the grid's fills paid above the market, and on a martingale it is the only thing the grid's expected profit can come from:

```math
\mathrm{E}[\text{gross}] = -\,\mathrm{E}[\text{gap}] \quad \text{on a price with no pattern}
```

Profit plus gap is therefore what the path's pattern earned the grid. It is zero when there is no pattern, positive when the price swings back, negative when it runs.

**The test.** A Monte Carlo simulation, in which the truth is known by construction:

| Setting | Value |
|---|---|
| Days | 1,000 simulated days of 86,400 one-second steps |
| Price | A random walk with 3% daily volatility |
| Grid | As in §1, 5 levels on each side, steps of 25 and 50 bp, stop and restart, daily close |
| Fills | At the level, also when the price jumps through it; stops and the close at the market price |
| Costs | None |
| Result | Per day, in bp of one unit's value |

Five price paths, three without a pattern and two with one:

| Path | Construction | Pattern |
|---|---|---|
| Random walk | Normal one-second steps | None |
| + small jumps | 10 jumps a day of 40 bp on average; 18% of the variance | None: jumps are as likely up as down |
| + large jumps | 2 jumps a day of 120 bp on average; 32% of the variance | None |
| Control: swings | Random walk + a part that reverts with a half-life of 10 minutes, about 20 bp in size | Reversion |
| Control: a trend day | Random walk + a drift for the whole day, different every day, 2% a day on average in either direction | Persistence |

![Monte Carlo: the grid's profit, minus its gap, and their sum, for three prices without a pattern and two with one](figures/17_02_martingale.png)
<sub><b>How to read the figure.</b> For each simulated price path: <b>blue</b>, the grid's average profit per day; <b>grey</b>, minus the gap, what its fills paid above the market; <b>orange</b>, their sum, what the path's pattern earned the grid. Whiskers are 95% intervals. The shaded paths are the two controls, which have a pattern by construction. Left, a step of 25 bp; right, 50 bp.</sub>

On the three prices without a pattern, the grid loses exactly its gap: profit plus gap is within two standard errors of zero in all six cases. Jumps make the grid lose more, 445 bp a day per unit with large jumps at a 25 bp step, but only because they widen the gap; they do not change the identity. A jump adds much to the variance and crosses few levels (Lecture 14, §4.1), and every level it does cross is filled above the market. The controls behave as they must: at a 25 bp step the grid earns 785 bp a day per unit on swings and loses 190 on trend days. The grid has no edge of its own. It sells the price's swings and buys its runs, and it is paid only if swings dominate at the scale of its step.

### 2.2 Runs: jumps spread over minutes

**What a run is.** A jump moves the price in one instant. A run moves it the same distance over minutes, step by step, and fills the grid's levels one after the other on the way, exactly as on the afternoon of 12 March. On the tape, Lecture 14 (§3) found both: on ordinary days the price turns back, and its variance ratio, the variance of one-hour returns divided by what one-minute returns imply, is about 0.9; on explosive days it runs, and the ratio is above 1. A simulation of runs therefore needs a price that switches between the two.

**How a run is simulated.** The price is the sum of a random walk, a hidden drift and a reverting part, and at every second it is in one of two states, calm or running:

| Step | Calculation, every second | Financial interpretation |
|---|---|---|
| 1. State | Calm → run with probability $`p_{\mathrm{in}}`$, run → calm with probability $`p_{\mathrm{out}} = 1/1{,}800`$ | Runs start without warning and last 30 minutes on average; $`p_{\mathrm{in}}`$ sets the share of time in runs, $`\pi = p_{\mathrm{in}} / (p_{\mathrm{in}} + p_{\mathrm{out}})`$ |
| 2. Hidden drift | In a run: $`d_t = a\,d_{t-1} + b\,\varepsilon_t`$; when calm: $`d_t = a\,d_{t-1}`$, with $`a = 2^{-1/600}`$ | A push in one direction that builds and turns within a run, with a half-life of 10 minutes, and fades after it; its direction is random |
| 3. Random walk | $`w_t = w_{t-1} + d_t + \sigma\,\eta_t`$ | The news: unpredictable moves, plus the drift |
| 4. Reverting part | When calm: $`y_t = a\,y_{t-1} + e\,\zeta_t`$; frozen in a run | Temporary pressure that is undone within minutes: the swings a grid lives on |
| 5. Price | $`p_t = w_t + y_t`$ | What trades |

Here $`\varepsilon_t`$, $`\eta_t`$ and $`\zeta_t`$ are independent standard normal draws, and $`b`$ and $`e`$ set the sizes of the drift and the reverting part. The drift is never seen by the grid; it is only felt, as levels filled one after another.

**Calibration.** For each share of time in runs, the model is fitted to two facts of the tape, so that every model below has the same average behaviour and differs only in how it is split between swings and runs:

| Step | What is set | To match |
|---|---|---|
| 1 | The strength of the drift, fixed for all models: its standard deviation is 0.07 times the random walk's per second | Runs that move the price visibly within half an hour |
| 2 | The size of the reverting part, by bisection | A variance ratio of one-hour to one-minute returns of 0.90, as on the tape |
| 3 | Every part scaled by the same factor | A daily volatility of 3%, as on the tape; the ratio is unchanged by the scaling |

**Switching off.** A grid that knew it was in a run would close its position at the market and pause, and restart around the price when the run ended. The simulation tests this with the true state seen at once, and seen 5, 15 or 30 minutes late.

![Monte Carlo with runs: one simulated day with its runs and hidden drift, and the grid's profit by the share of time in runs](figures/17_03_runs.png)
<sub><b>How to read the figure.</b> <b>Top:</b> one simulated day of the calibrated model with 10% of its time in runs; the shaded bands are the run episodes. <b>Middle:</b> the hidden drift, in bp per minute: it moves only in a run and fades with a 10-minute half-life afterwards. <b>Bottom left:</b> the grid's average profit per day, by the share of time in runs, with the swings held fixed: on a random walk (grey) and on a random walk with swings (black); volatility is not held fixed here and rises with the runs. <b>Bottom right:</b> every model calibrated to the tape's variance ratio and volatility: the grid always on (dashed), and switched off during runs seen at once or 5, 15 or 30 minutes late. Step 25 bp, 5 levels a side, no costs.</sub>

Two results, one from each lower panel:

1. **With the swings held fixed, runs cost the grid.** With a reverting part of 20 bp, the grid earns 800 bp a day per unit when the price never runs; with 5% of the time in runs it earns 450, with 10% about 80, and with 20% it loses 610. On a random walk with runs it loses at every share. Runs do to the grid what jumps do, spread over minutes, and the gap is no longer the channel: the grid is filled at its levels, one after another, and loses on the inventory.
2. **With the tape's average held fixed, the split decides.** When every model has the tape's variance ratio, a market that runs more often must swing back harder in between. The grid always on earns 53 bp a day per unit when the market never runs and 130 to 270 when it does, a fraction of what the swings offer: the runs take most of it back. Switched off during the runs, the grid keeps up to three times as much: 1.3 times at 2% of the time in runs, 2.8 times at 20%. Seen 5 or 15 minutes late, the switch loses nothing and even gains a little: the drift outlives the run's label, so a grid that restarts a little late also avoids the drift's tail. Seen 30 minutes late, the switch loses part of its value.

**What the simulations say about the tape.** The grid earns nothing from a price without a pattern, and the tape's average reversion is no guarantee of profit: what matters is how the reversion and the runs are spread over the day, and whether the runs can be recognised early enough to step aside. Two things in these simulations are kinder than the tape. Fills are counted at the level, whereas the tape fills only what is traded through; and the reversion of the simulated price happens over minutes, whereas part of the tape's reversion is the bounce between buyers and sellers within the same second, which no resting order a step away can earn. Section 3 measures what is left on the tape.
