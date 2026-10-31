# Lecture 20: Statistics of the Flow: Order-Flow Imbalance, Impact, VPIN, Hawkes Processes and Lead-Lag

*Systematic Trading: Lecture Notes (MSc) · Oct 31, 2026 · Max Gnesi*

Lecture 19 read the book at one moment: which side outweighs the other, and what that says about the next move. This lecture measures what changes between moments: orders added, cancelled and filled over an interval, which together are called the flow. It asks how much of a price move the flow accounts for, whether it forecasts the next one, how long a trade's impact lasts, whether one-sided flow warns of a crash, how far trading feeds on itself, and whether Bybit or Binance moves first. As in Lecture 19, each statistic is first introduced on invented examples and then measured on the same 45 days of Bybit BTCUSDT, 20 September to 3 November 2025, with the trades of Binance beside them. The hypotheses were fixed before any result was computed ([results/hypotheses.md](results/hypotheses.md)).

## 1. The flow as a delta

Part IV moves from describing the order book to trading on it, one step per lecture:

![Part IV in one line: Lecture 20 measures what changes in the book](figures/20_01_part_iv.png)
<sub><b>How to read the figure.</b> Each box is one lecture of Part IV, each building on the one before; this lecture is outlined, Lectures 18 and 19 are done. Above the boxes, the four stages: describing the book, measuring it, simulating our own orders in it, and trading strategies on it.</sub>

Lecture 19 distinguished two kinds of quantity: a **level**, the state of the book at one moment, like a balance sheet, and a **delta**, what changed over an interval, like a cash-flow statement. The same word, imbalance, names one of each. **Book imbalance** compares the sizes resting at the best bid and the best ask at one moment (Lecture 19, §2.1). **Order-flow imbalance** adds up, over an interval, everything that pushed on the best prices: size added to the best bid or taken from the best ask pushes the price up; size added to the best ask or taken from the best bid pushes it down, whether it was taken by a trade or by a cancellation (Cont, Kukanov and Stoikov, 2014; Section 2.1 gives the calculation). **Trade imbalance** counts only the trades: size bought by takers minus size sold, the net aggressive flow of Lecture 15.

The idea of the lecture fits in one chart. On the left, one minute of our data; on the right, the whole of that day:

![A level forgets, a delta adds up: one minute of the mid, book imbalance and the added-up flow; and the share of the mid's change each explains over one day](figures/20_02_level_vs_delta.png)
<sub><b>How to read the figure.</b> <b>Left:</b> Bybit BTCUSDT, 1 October 2025, 12:00 to 12:01 UTC, 600 book updates and 5,405 trades. Top, the mid; middle, the book imbalance at the best after each update, from −1 (only asks) to +1 (only bids); bottom, the order-flow imbalance at the best (blue) and the trade imbalance (orange), each added up from 12:00, in BTC. <b>Right:</b> every interval of 1, 10 and 60 seconds of the same day; each bar is the share of the variance of the mid's change over the interval explained by one quantity alone (R², from a straight-line fit): the book imbalance just before the interval (grey), the trade imbalance during it (orange), the order-flow imbalance during it (blue). One day of the in-sample period; Section 3 measures all 45 days.</sub>

The book imbalance changed sign 69 times in the minute. Each value describes the book at that moment and nothing earlier: when the queue at the best is used up and the price moves, the new best queue starts afresh, and the imbalance with it. The added-up order-flow imbalance followed the mid almost step for step. Three moments of the minute show why:

| Seconds after 12:00 | What happened | Mid | Trade imbalance | Order-flow imbalance |
|---|---|---|---|---|
| 0 to 39.5 | A steady rise | +$42 | +78 BTC | +90 BTC |
| 27.5 to 31 | Two buys 5 ms apart, 11.5 and 37.5 BTC, filled in 496 trades over $17 of prices | +$11 | +48 BTC | +63 BTC |
| 39.5 to 49 | The fall: new asks placed at lower and lower prices | −$68 | −57 BTC | −261 BTC: −50 at the bid, −211 at the ask |
| 59.35 | One sell of 71 BTC, filled in 809 trades over $29 of prices | the mid ends the minute at $116,711 | −71 BTC | falls with it |

<sub><b>How to read the table.</b> Mid: change of the mid over the stretch. The trade imbalance counts only trades; the order-flow imbalance counts trades and the size added and cancelled at the best. A single buy or sell is all trades of one taker order, which share the same millisecond (Lecture 19).</sub>

In the rise both measures agree, because takers did most of the pushing. In the fall they part. The price dropped $68 while takers sold a net 57 BTC. At the bid, the order-flow imbalance lost 50 BTC, about what sellers took; the larger push came from the ask side, where sellers placed new resting orders at lower and lower prices, 211 BTC counted at the best ask as it came down. Those orders never traded in the interval, so the trade imbalance cannot see them; the order-flow imbalance does. Over the whole day the picture is the same. Measured over ten-second intervals, the order-flow imbalance explains 59% of the variance of the mid's change, the trade imbalance 21%, and the book imbalance at the start of the interval 4%.

Two cautions keep the chart in proportion. First, the flow and the change of the mid are measured over the same interval: the flow describes how the price moved, it does not say in advance that it will move. A forecast needs the flow of the past interval and the move of the next one, which is hypothesis H2. Second, the bars are one day of the in-sample period, fitted on that day. Whether the order-flow imbalance explains more than the trades on days it was not fitted on is hypothesis H1, and the literature disagrees: on 50 US stocks, Cont, Kukanov and Stoikov (2014) found 65% against 32%, while on the BitMEX bitcoin perpetual the trades explained more (Silantyev, 2019).

This lecture runs as follows:

| § | Step | Question |
|---|---|---|
| 1 | The flow as a delta | What does a delta show that a level does not? |
| 2 | The statistics | What do order-flow imbalance, impact over time, VPIN, Hawkes processes and lead-lag each capture, shown on invented flows? |
| 3 | On our 45 days | Does the flow explain and forecast the price, how long does impact last, does VPIN warn, how far does trading feed on itself, and which venue moves first? |
| 4 | 10 October | When did the news arrive, did the flow move before it, and did any statistic of the book or the flow warn of the fall? |
| 5 | Summary, exercises and reading | |

## 2. The statistics

Each statistic is introduced the same way as in Lecture 19: what it is meant to capture, how it is computed, an invented example that shows it at work, and what it misses. The examples are invented so that each case is clean; Section 3 measures the same statistics on the data.

### 2.1 Order-flow imbalance

**Key message.** Order-flow imbalance adds up everything that pushed on the best prices over an interval: trades, new orders and cancellations. It measures the pressure that moves the price, of which the trades are only one part.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Bid side of update $`n`$: if the best bid rose, $`+q^b_n`$, the size at the new best bid; if it stayed, $`+(q^b_n - q^b_{n-1})`$, the change of its size; if it fell, $`-q^b_{n-1}`$, the size that was there | Buying interest arriving at the top of the book, or leaving it: filled, cancelled or outbid |
| 2 | Ask side, with the opposite sign: if the best ask fell, $`-q^a_n`$; if it stayed, $`-(q^a_n - q^a_{n-1})`$; if it rose, $`+q^a_{n-1}`$ | Selling interest arriving at the top, or leaving it |
| 3 | Contribution of the update: $`e_n`$ = bid side + ask side; over an interval, $`\text{OFI} = \sum_n e_n`$ | The net pressure on the price over the interval, in BTC: positive pushes it up |
| 4 | Fit the change of the mid over the interval, $`\Delta m = \beta \cdot \text{OFI}`$ | How far one BTC of pressure moves the price; $`\beta`$ is roughly inversely proportional to the depth at the best (Cont, Kukanov and Stoikov, 2014) |

<sub><b>How to read the table.</b> $`q^b_n, q^a_n`$: size at the best bid and ask after update $`n`$, in BTC. Steps 1 and 2 are the formula of Cont, Kukanov and Stoikov (2014), $`e_n = \mathbb{1}\{P^b_n \ge P^b_{n-1}\}\,q^b_n - \mathbb{1}\{P^b_n \le P^b_{n-1}\}\,q^b_{n-1} - \mathbb{1}\{P^a_n \le P^a_{n-1}\}\,q^a_n + \mathbb{1}\{P^a_n \ge P^a_{n-1}\}\,q^a_{n-1}`$, with $`P^b_n, P^a_n`$ the best bid and ask prices; $`\mathbb{1}\{\cdot\}`$ is 1 if the condition holds and 0 otherwise. The trade imbalance is the part of the same pressure that came from trades: taker buys minus taker sells.</sub>

![Order-flow imbalance on an invented book: a trade, an addition, a cancellation and a new ask, update by update](figures/20_03_ofi_card.png)
<sub><b>How to read the figure.</b> One invented book over four updates, the best two levels on each side, sizes in BTC (bars full at 4 BTC); the best bid and ask are outlined. Above each book, the event that led to it. Below: the mid, the contribution of the update to the order-flow imbalance, and both imbalances added up so far.</sub>

The four updates show each case of the formula. A buyer takes 1.0 BTC at the best ask: the ask queue shrinks at an unchanged price, +1.0, and the trade imbalance records the same. Then 1.2 BTC is added to the best bid: +1.2, and no trade happens. The last 0.5 BTC at the best ask is cancelled, so the best ask rises a tick: the size that was there has left, +0.5, and the mid rises half a tick. A seller then places 1.0 BTC back at 100,000.1: the best ask falls, −1.0, and the mid returns. After four updates the order-flow imbalance stands at +1.7 BTC and the trade imbalance at +1.0: the extra 0.7 is pressure that came from placing and cancelling orders.

**Walls at the best cancel themselves out.** An order placed at the best and cancelled within the same interval adds its size and then takes it away: its net contribution is zero. Added up over an interval longer than a wall's life, the order-flow imbalance is immune to walls at the best price, which book imbalance (Lecture 19, §2.1) is not. A wall placed behind the best price does not enter at all, because only the best levels count; a version over several levels would see it, and would be exposed to it.

**What it misses.** First, depth behind the best: the flow at deeper levels also moves the price, and versions over the best 10 levels explain more of it on stocks (Xu, Gould and Howison, 2019; Cont, Cucuringu and Zhang, 2023); Section 3 reports them beside the best level. Second, what happens inside one update: our book arrives every 100 ms, and a trade followed by a refill of the same size within one update shows as no change at all (Lecture 18, §2). Third, intentions: it counts size, not who placed it or why. Fourth, timing: measured over the same interval as the price change, it describes the move; a forecast needs the flow of one interval and the move of the next, which is hypothesis H2.

### 2.2 Impact over time

**Key message.** Lecture 19 found that after a fill the price kept moving against the resting order for a minute. Either each trade's own impact keeps growing, or each trade's impact fades and more trades on the same side follow. The propagator model separates the two: it splits the move after a trade into the trade's own impact and the impact of the orders that follow it.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Sign of each taker order, $`\varepsilon_i = +1`$ (buy) or $`-1`$ (sell); its autocorrelation $`C(\ell)`$, the average of $`\varepsilon_i \varepsilon_{i+\ell}`$ | Do buys follow buys? A large order split into many small ones makes them |
| 2 | Response: $`R(\ell)`$, the average of $`\varepsilon_i\,(m_{i+\ell} - m_i)`$ | How far the mid moved in the direction of an order, $`\ell`$ orders later: what a maker filled by it sees, as in a markout (Lecture 19, §2.5) |
| 3 | Propagator model: $`m_t = \sum_{i<t} G(t-i)\,\varepsilon_i`$ + noise | Each order leaves a bare impact $`G`$ that may fade with the number of orders since |
| 4 | Then $`R(\ell) = \sum_{n>0} G(n)\,C(\lvert n-\ell \rvert) - \sum_{n>0} G(n)\,C(n)`$; given $`R`$ and $`C`$, solve for $`G`$ by least squares | The response mixes an order's own impact with that of the orders that follow it; the solution separates them |
| 5 | Over an interval: $`\Delta m = \lambda \cdot \text{TI}`$ | **Kyle's lambda**: the price of one BTC of net taker flow, the classic measure of how much trades move a market (Kyle, 1985) |

<sub><b>How to read the table.</b> $`i`$ counts taker orders (trades with the same millisecond and side, Lecture 19); $`m_i`$: the mid just before order $`i`$, in ticks; $`C(0) = 1`$. Steps 3 and 4 follow Bouchaud, Gefen, Potters and Wyart (2004). TI: trade imbalance, taker buys minus taker sells, in BTC.</sub>

![Impact over time on invented orders: one order's bare impact, twenty buys in a row, and the response next to the bare impact](figures/20_04_impact_card.png)
<sub><b>How to read the figure.</b> Invented. <b>Left:</b> the bare impact of one order, 1 tick at once, then fading. <b>Middle:</b> twenty buys in a row, then forty orders of mixed sign; the mid if each order's impact were permanent (dotted) and if it fades as on the left (blue). <b>Right:</b> the response $`R`$ (orange), computed with the propagator model from the bare impact $`G`$ (black) and a correlation of signs that falls from 0.3 at the next order to 0.01 300 orders later; log scale.</sub>

With fading impact, twenty buys lift the mid by 12.7 ticks, not 20, and once orders turn mixed it drifts back to about 7: impact that fades is partly temporary. On the right, each order's own impact falls from 1 tick to 0.32 ticks over 300 orders, yet the response rises from 0.92 to 1.24 ticks: the orders that follow on the same side more than replace what fades. Seen from a maker, the price keeps moving after the fill, though no single trade's impact grows. In this example the two effects balance exactly, a fade of $`\ell^{-0.2}`$ against signs correlated as $`\ell^{-0.6}`$, and the price neither trends nor reverts. Bouchaud et al. (2004) found the bare impact on the Paris Bourse fading in this way and called it the central result of their paper: it is how a market whose order flow is predictable, since buys follow buys, can still have prices that are not.

**What it misses.** It is linear and an average: one large order and one small one count the same, and so do calm hours and a cascade. Time runs in orders, not seconds: on 1 October, 300 taker orders took 20 seconds in the busiest hour and about 3 minutes in the quietest. And the model has no cancellations: it describes trades only, while Section 2.1 showed that much of the pressure comes from orders that never trade.

### 2.3 VPIN

**Key message.** VPIN measures how one-sided trading has been, counted in volume rather than in time. Its authors built it as a warning of **toxic flow**, flow that is informed and that market makers lose to, and reported that it stood high hours before the US flash crash of 6 May 2010 (Easley, López de Prado and O'Hara, 2012). A later study found that it peaked after the crash, not before, and that it mostly tracks how much is being traded (Andersen and Bondarenko, 2014). Which reading holds on our data is hypothesis H4.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Cut the trades into buckets of equal volume $`V`$, one fiftieth of an average day's volume | A clock that ticks with trading: in a busy hour buckets fill in minutes, at night in hours |
| 2 | In each bucket, the volume bought by takers, $`V^B`$, and sold, $`V^S`$ | Who was in a hurry within the bucket |
| 3 | Imbalance of the bucket: $`\lvert V^B - V^S \rvert / V`$ | 0: as much bought as sold; 1: all on one side |
| 4 | VPIN: the average imbalance over the last 50 buckets | How one-sided about the last day's volume has been |
| 5 | Alarm: VPIN above the 90th percentile of its own history | The original use: a signal to widen quotes or step back |

<sub><b>How to read the table.</b> VPIN: volume-synchronized probability of informed trading. The original estimates the sides of step 2 without trade-by-trade data, by **bulk volume classification**: within one-minute bars, the share of a bar's volume counted as bought is $`\Phi(\Delta p / \sigma)`$, with $`\Delta p`$ the bar's price change, $`\sigma`$ its standard deviation and $`\Phi`$ the normal distribution function. Bybit records the taker side of every trade, so we use the true sides and report the estimated version beside them.</sub>

![VPIN on invented volume buckets, and how bulk volume classification turns a price move into one-sided volume](figures/20_05_vpin_card.png)
<sub><b>How to read the figure.</b> Invented. <b>Left:</b> 100 buckets of equal volume; grey bars: the imbalance of each bucket; black line: VPIN, the average of the last 50 buckets, drawn once 50 buckets exist. Buckets 71 to 100 (shaded): sellers take the lead, about a quarter of each bucket's volume is bought. <b>Right:</b> under bulk classification, the share of a bar counted as bought (blue) and the imbalance this implies (dashed), against the bar's price change in standard deviations.</sub>

On the left, VPIN stands at 0.15 while the buckets are balanced and climbs to 0.37 as the selling buckets fill its window. It moves slowly by design: one new bucket replaces one of fifty. Because buckets are counted in volume, the 30 selling buckets may last half a day in a quiet market or an hour in a busy one, and VPIN rises faster in clock time when the volume comes faster.

The right panel shows one source of trouble with the original's estimated sides. Under bulk classification, a bar whose price moved by two standard deviations is counted as 98% bought, whoever actually traded: large moves turn into one-sided volume by construction, so VPIN partly measures volatility. Andersen and Bondarenko (2014) found a second, separate link: VPIN rises mechanically with trading intensity, and once intensity is accounted for it adds nothing to the forecast of volatility; its authors replied in the same journal, and the exchange did not settle the question. With the true sides the first link disappears and the second remains: whether VPIN says anything about the next hour that the last hour's volume and volatility do not already say. That is what H4 tests.

**What it misses.** It has settings that matter: the bucket size, the window of 50, and for the original the classification. It counts trades only, not the orders placed and cancelled that Section 2.1 showed. And a one-sided bucket does not show who was informed: a large trader working an order looks the same as one who knows something.

### 2.4 Hawkes processes

**Key message.** Trades and cancellations come in clusters: one event raises the chance of more. A Hawkes process models this directly (Hawkes, 1971). It splits activity into events that come from outside, such as news or a trader's own decision, and events triggered by earlier events, such as the orders of a split order, traders reacting to a trade, or market makers reacting to each other. The **branching ratio** is the share that is triggered: how far the market feeds on itself.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Outside rate $`\mu`$, events per second | Activity that does not depend on the market's own recent past |
| 2 | Intensity $`\lambda(t) = \mu + \sum_{t_j < t} \phi(t - t_j)`$ | The expected rate of events now: each past event adds a bump $`\phi`$ that fades with time |
| 3 | Branching ratio $`n = \int_0^\infty \phi(s)\,ds`$ | The number of events one event triggers directly, on average; also the share of all events that are triggered |
| 4 | Average rate $`\mu / (1 - n)`$ | With $`n`$ = 0.5 activity is twice the outside rate; with $`n`$ = 0.9 ten times; at $`n`$ = 1 it would never settle |
| 5 | Fit $`\mu`$ and $`\phi`$ by maximum likelihood, hour by hour | So that the daily rise and fall of activity is not read as one event triggering another |

<sub><b>How to read the table.</b> $`t_j`$: times of past events. We use for $`\phi`$ a sum of exponentials with decay times from 1 ms to 100 s, each with its own weight (Bacry, Mastromatteo and Muzy, 2015); the branching ratio is the sum of the weights. Step 5 follows Filimonov and Sornette (2015), who showed that ignoring the daily pattern, outliers or changes of regime makes $`n`$ look larger than it is.</sub>

![A Hawkes process on invented events next to a Poisson process with the same average rate, events by origin, and the intensity](figures/20_06_hawkes_card.png)
<sub><b>How to read the figure.</b> Invented, 120 seconds. <b>Top:</b> events at independent random times, 1.6 per second on average. <b>Middle:</b> a Hawkes process with the same average rate: events from outside (black) at 0.4 per second, each triggering on average 0.75 more after about a second (orange). <b>Bottom:</b> its intensity, the expected rate of events at each moment; the dotted line is the outside rate.</sub>

Both rows hold about the same number of events, but they look different. Without excitation the events are spread evenly; with it they bunch: around 25 seconds one outside event sets off a cascade, and the intensity climbs to almost ten events a second, more than 20 times the outside rate, before it fades. In this simulation 73% of the events were triggered, close to the branching ratio of 0.75 that generated them. A market close to $`n`$ = 1 would be one where small shocks can set off very large bursts. Filimonov and Sornette (2012) estimated that the share rose from about 0.3 in 1998 to above 0.7 from 2007 on S&P 500 futures, and Hardiman, Bercot and Bouchaud (2013), with a kernel that fades more slowly, found it close to 1; whether BTCUSDT stays clearly below 1 is hypothesis H5.

**Two causes of a burst.** A burst of cancellations can be a chain, one market maker reacting to another, or a common trigger, many reacting at once to the same news. The Hawkes kernel separates the two by timing: a chain spreads out with delays of about one reaction time; a common trigger arrives all at once, more events in the same instant than the kernel can explain. Our book arrives every 100 ms and market makers react in milliseconds, so for cancellations a whole chain can fit within one update and look simultaneous. Trades carry millisecond times, which is why Section 3 fits the model to taker orders and reports cancellations only from 100 ms upwards.

**What it misses.** The branching ratio depends on the kernel: a fast-fading kernel and one with a long tail give different answers on the same data, which is part of why the literature disagrees. Excitation in the model is always positive; it does not let one event make others less likely. And a triggered event is a statistical attribution, not an observed cause.

### 2.5 Lead and lag between venues

**Key message.** BTCUSDT trades on many venues at once, and when the price moves, one venue usually moves first and the others follow within milliseconds. Correlating the price changes of two venues at different lags shows how far one is behind the other. On our data the two venues are Bybit and Binance; which one leads is hypothesis H6, and the answer matters to anyone who quotes on one venue and watches the other (Lecture 24).

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | The two price series, each at its own trade times | Prices as they were actually traded, without filling gaps |
| 2 | Shift the times of one venue by a lag $`\tau`$ | Ask: does B, read $`\tau`$ later, move with A? |
| 3 | Correlation of the price changes, from all pairs of changes whose time intervals overlap | The Hayashi-Yoshida estimator, built for prices that change at different times (Hayashi and Yoshida, 2005; Hoffmann, Rosenbaum and Yoshida, 2013) |
| 4 | Repeat for $`\tau`$ from −1 s to +1 s; the lead is the lag with the highest correlation | How long the follower takes |
| 5 | Lead-lag ratio: the sum of squared correlations at positive lags divided by that at negative lags | Above 1: A leads on balance (Huth and Abergel, 2014) |

<sub><b>How to read the table.</b> Resampling both series on a common clock and taking the last price in each interval biases correlations towards zero at short intervals; the Hayashi-Yoshida estimator avoids this by never resampling.</sub>

![Lead and lag on two invented venues: half a second of trades, and the correlation by lag with and without an offset between the clocks](figures/20_07_leadlag_card.png)
<sub><b>How to read the figure.</b> Invented. <b>Left:</b> half a second of trades on two venues that follow the same price, venue B 20 ms behind venue A. <b>Right:</b> the Hayashi-Yoshida correlation of their price changes by lag; positive lags mean A moves first. Solid: both clocks correct; dotted: the same trades with B's clock running 8 ms fast.</sub>

The correlation peaks at 20 ms, the delay that was built in, and the lead-lag ratio is 18: A clearly leads. The dotted line shows the limit of the method. If B's timestamps run 8 ms fast, the peak moves to 28 ms, and nothing in the prices tells the two cases apart. Bybit and Binance stamp their trades with their own clocks, and an offset of a few milliseconds between them is plausible. A lead measured on their data is therefore a lead plus an unknown constant. Two things help. A lead much larger than any plausible offset is real. And an offset is the same at all times, so a lead that changes with market conditions, larger in calm hours than in a cascade, cannot be an offset alone.

**What it misses.** It measures who moves first on average, not why: the follower may be slower, or traders may arbitrage the gap from one side only. A lead of a few milliseconds is visible but not usable by a trader whose orders take longer to arrive. And correlation sees only linear co-movement; a venue can lead in large moves and follow in small ones.

### 2.6 The statistics side by side

| Statistic | Kind | What it captures | From | Blind spot | Tested in |
|---|---|---|---|---|---|
| Book imbalance (Lecture 19) | Level | Which side of the book outweighs the other | The book at one moment | What happened before; walls | Lecture 19 |
| Order-flow imbalance | Delta | Pressure on the best prices: trades, additions, cancellations | Book updates | Deeper levels; events within one update | H1, H2 |
| Trade imbalance | Delta | Net taker buying | Trades | Orders that never trade | H1 (as the rival) |
| Kyle's lambda | Delta | The price move per BTC of net taker flow | Trades and mid | Time: it is one number per interval | Section 4 (H9) |
| Propagator | Delta | Each order's own impact over time, apart from the orders that follow | Trades and mid | Size; cancellations | H3 |
| VPIN | Delta | How one-sided the volume has been | Trades | What volume and volatility already say | H4, H9 |
| Hawkes branching ratio | Delta | How far activity triggers more activity | Times of taker orders | The choice of kernel; causes | H5, H9 |
| Lead and lag | Delta | Which venue moves first, by how much | Trades of both venues | Offsets between clocks | H6, H7 |

<sub><b>How to read the table.</b> Kind: a level is a state at one moment; a delta is a change over an interval (Section 1). Tested in: the hypotheses of [results/hypotheses.md](results/hypotheses.md), fixed before the results; Section 4 tests some of the same statistics on 10 October.</sub>

All statistics but the first are deltas, and all but order-flow imbalance are built from trades alone. They share one limit: they see what was done, not who did it or why. A one-sided hour can be informed selling or a fund rebalancing; a burst of triggered events can be traders reacting to each other or to a common piece of news; a lead can be speed or a clock. Section 3 measures what each says on the 45 days; Section 4 asks whether any of them changed before the fall of 10 October.

*Section 3 follows.*

## References

- Andersen, T. G. and Bondarenko, O. (2014). VPIN and the flash crash. *Journal of Financial Markets* 17, 1–46. — the critique of VPIN (§2.3).
- Bacry, E., Mastromatteo, I. and Muzy, J.-F. (2015). Hawkes processes in finance. *Market Microstructure and Liquidity* 1(1), 1550005. — survey; kernels and estimation (§2.4).
- Bouchaud, J.-P., Gefen, Y., Potters, M. and Wyart, M. (2004). Fluctuations and response in financial markets: the subtle nature of 'random' price changes. *Quantitative Finance* 4(2), 176–190. — the propagator model (§2.2).
- Cont, R., Cucuringu, M. and Zhang, C. (2023). Cross-impact of order flow imbalance in equity markets. *Quantitative Finance* 23(10), 1373–1393. — order-flow imbalance over several levels (§2.1).
- Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics* 12(1), 47–88. — order-flow imbalance (§1).
- Easley, D., López de Prado, M. and O'Hara, M. (2012). Flow toxicity and liquidity in a high-frequency world. *Review of Financial Studies* 25(5), 1457–1493. — VPIN (§2.3).
- Filimonov, V. and Sornette, D. (2012). Quantifying reflexivity in financial markets: towards a prediction of flash crashes. *Physical Review E* 85(5), 056108. — the branching ratio of S&P 500 futures, 1998–2010 (§2.4).
- Filimonov, V. and Sornette, D. (2015). Apparent criticality and calibration issues in the Hawkes self-excited point process model: application to high-frequency financial data. *Quantitative Finance* 15(8), 1293–1314. — what biases the branching ratio upwards (§2.4).
- Hardiman, S. J., Bercot, N. and Bouchaud, J.-P. (2013). Critical reflexivity in financial markets: a Hawkes process analysis. *European Physical Journal B* 86(10), 442. — a branching ratio close to 1 (§2.4).
- Hawkes, A. G. (1971). Spectra of some self-exciting and mutually exciting point processes. *Biometrika* 58(1), 83–90. — the Hawkes process (§2.4).
- Hayashi, T. and Yoshida, N. (2005). On covariance estimation of non-synchronously observed diffusion processes. *Bernoulli* 11(2), 359–379. — correlation without resampling (§2.5).
- Hoffmann, M., Rosenbaum, M. and Yoshida, N. (2013). Estimation of the lead-lag parameter from non-synchronous data. *Bernoulli* 19(2), 426–461. — lead and lag (§2.5).
- Huth, N. and Abergel, F. (2014). High frequency lead/lag relationships — empirical facts. *Journal of Empirical Finance* 26, 41–58. — the lead-lag ratio (§2.5).
- Kyle, A. S. (1985). Continuous auctions and insider trading. *Econometrica* 53(6), 1315–1335. — Kyle's lambda (§2.2).
- Silantyev, E. (2019). Order flow analysis of cryptocurrency markets. *Digital Finance* 1, 191–218. — trade and order-flow imbalance on the BitMEX bitcoin perpetual (§1).
- Xu, K., Gould, M. D. and Howison, S. D. (2019). Multi-level order-flow imbalance in a limit order book. *Market Microstructure and Liquidity* 4(3–4), 1950011. — order-flow imbalance over several levels (§2.1).
