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

*Section 2 follows.*

## References

- Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics* 12(1), 47–88. — order-flow imbalance (§1).
- Silantyev, E. (2019). Order flow analysis of cryptocurrency markets. *Digital Finance* 1, 191–218. — trade and order-flow imbalance on the BitMEX bitcoin perpetual (§1).
