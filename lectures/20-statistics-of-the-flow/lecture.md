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

*Section 2.3 follows.*

## References

- Bouchaud, J.-P., Gefen, Y., Potters, M. and Wyart, M. (2004). Fluctuations and response in financial markets: the subtle nature of 'random' price changes. *Quantitative Finance* 4(2), 176–190. — the propagator model (§2.2).
- Cont, R., Cucuringu, M. and Zhang, C. (2023). Cross-impact of order flow imbalance in equity markets. *Quantitative Finance* 23(10), 1373–1393. — order-flow imbalance over several levels (§2.1).
- Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics* 12(1), 47–88. — order-flow imbalance (§1).
- Kyle, A. S. (1985). Continuous auctions and insider trading. *Econometrica* 53(6), 1315–1335. — Kyle's lambda (§2.2).
- Silantyev, E. (2019). Order flow analysis of cryptocurrency markets. *Digital Finance* 1, 191–218. — trade and order-flow imbalance on the BitMEX bitcoin perpetual (§1).
- Xu, K., Gould, M. D. and Howison, S. D. (2019). Multi-level order-flow imbalance in a limit order book. *Market Microstructure and Liquidity* 4(3–4), 1950011. — order-flow imbalance over several levels (§2.1).
