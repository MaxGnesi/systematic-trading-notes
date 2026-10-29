# Lecture 18: The Order Book: What It Shows and How to Reconstruct It

*Systematic Trading: Lecture Notes (MSc) · Oct 29, 2026 · Max Gnesi*

Part III worked with the tape: every trade, the moment two orders met. This lecture opens Part IV by turning to the orders themselves, those waiting in the order book to be met. It explains what an order book is and how much of it public data show, how to obtain the data and rebuild the book from it, and what the rebuilt book reveals about a market's liquidity. The data are Bybit's BTCUSDT perpetual from 20 September to 3 November 2025, around the liquidation cascade of 10 October; one day of 2024 serves to illustrate the data's format.

## 1. The order book

Part IV moves from describing the order book to trading on it, one step per lecture:

![Part IV in one line: from describing the order book to trading on it](figures/18_01_part_iv.png)
<sub><b>How to read the figure.</b> Each box is one lecture of Part IV, each building on the one before; this lecture is outlined. Above the boxes, the four stages: describing the book, measuring it, simulating our own orders in it, and trading strategies on it.</sub>

This lecture is the first stage: what the book is, what public data show of it, and what it reveals before anything is measured or traded. It runs as follows:

| § | Step | Question |
|---|---|---|
| 1 | The order book | What is in it, and what does a market order do to it? |
| 2 | Three levels of detail | What do L1, L2 and L3 data show, and what does L2, the level we have, leave out? |
| 3 | Getting the data | How do readers download the book and the trades themselves, and why both? |
| 4 | Reconstructing the book | How is the book rebuilt from the data, and how do we know it is right? |
| 5 | What the book shows | Spread, depth, the cost of a market order, refill and cancellations, on calm days and on 10 October |
| 6 | Summary, exercises and reading | |

### 1.1 What is in it

An order book is the list of orders waiting to trade at each price. Every term the rest of Part IV uses is defined here once:

| Term | Meaning | Financial interpretation |
|---|---|---|
| **Limit order** | An order to buy or sell up to a given size at a given price or better | A trader willing to wait for a better price, at the risk of not trading |
| **Resting order** | A limit order that could not trade at once and waits in the book | Liquidity offered to others: the maker's side of a trade (Lecture 12, §3) |
| **Market order** | An order to trade a given size at once, at whatever prices are available | A trader in a hurry: the taker's side, who pays the spread and more |
| **Bid, ask** | A resting order to buy (bid) or to sell (ask) | The two sides of the book |
| **Level** | One price with resting orders | On BTCUSDT, prices come in ticks of $0.10, so levels are at least a tick apart |
| **Best bid, best ask** | The highest bid and the lowest ask | The prices at which a small market order sells or buys |
| **Spread** | Best ask minus best bid | The cost of buying and selling at once; on BTCUSDT usually one tick |
| **Mid** | The average of the best bid and the best ask | The usual reference price between trades |
| **Depth** | The size resting within a distance of the mid, on one side | How much can be traded before the price moves that far |
| **Queue** | The orders resting at one level, in the order they arrived | Who trades first when a market order comes: first come, first served (price-time priority) |

**One moment of the book.** The book of 12 March 2024 at 12:20:30 UTC, rebuilt from Bybit's data (§4 shows how):

![An order book at one moment: Bybit BTCUSDT, 12 March 2024, 12:20:30 UTC](figures/18_02_book_moment.png)
<sub><b>How to read the figure.</b> <b>Left:</b> the best 25 levels on each side, bids (resting buy orders) in blue below the price, asks (resting sell orders) in pink above it; each bar is the size waiting at that price. The horizontal axis is cut at 1.6 BTC so that the small levels show; the best bid's bar runs on to 6.35 BTC. <b>Right:</b> the asks added up from the best ask outwards (pink): the price a market buy reaches after buying a given amount. Black dots: the average price of market buys of 0.5, 1, 2 and 5 BTC, and how far it lies above the mid.</sub>

At that moment the best bid was $71,950.0, with 6.35 BTC queued, and the best ask one tick higher, $71,950.1, with 0.23 BTC: a spread of one tick. The book was lopsided. Within $10 of the mid, 14.7 BTC waited to buy against 2.0 BTC to sell. About three seconds later, buyers took the thin asks and the price rose $35. Whether such an imbalance predicts the next move is the question of Lecture 19.

### 1.2 What a market order does to it

A market order takes the best price first and then the next, level by level, until it is filled: it **walks the book**. Its average price is the cost of its hurry:

| Market buy at 12:20:30 | Levels taken | Average price | Above the mid | Last price paid |
|---|---|---|---|---|
| 0.5 BTC | 4 | 71,951.96 | 0.27 bp | 71,953.6 |
| 1 BTC | 12 | 71,953.30 | 0.45 bp | 71,957.5 |
| 2 BTC | 22 | 71,956.49 | 0.89 bp | 71,960.4 |
| 5 BTC | 40 | 71,960.26 | 1.42 bp | 71,964.5 |

<sub><b>How to read the table.</b> Our calculation from the rebuilt book: the asks taken in order from the best, until the size is filled. bp: basis points of the mid, $71,950.05.</sub>

The cost grows faster than the size, because each additional bitcoin is bought further from the mid. Walking the book this way assumes the book stands still while the order travels to the exchange, and it does not.

**The book moves while the order travels.** An order needs time to reach the exchange, its **latency**. In that time market makers, who see the market and react faster, can revise or cancel their quotes, above all when the price starts to move, which is when a trader most wants to trade. This is **quote fading**: the order arrives at worse prices than it was sent against. Part of the displayed depth was never meant to trade at all: over a third of limit orders on Nasdaq's book are cancelled within two seconds, **fleeting orders** in the term of Hasbrouck and Saar (2009), and a trade on one venue is followed within 100 milliseconds by cancellations on others (van Kervel, 2015). Practitioners call the result the **liquidity mirage**: depth that is displayed but gone when it is reached. Our recorded book adds its own delay, since it is updated every 100 milliseconds. The costs above are therefore a lower bound; §5 measures by how much real market orders did worse, and Lecture 21 makes latency a setting of every replay.

A figure of the book shows how much rests at each price. It does not show who stands behind those amounts, which depends on how much detail the data contain.

## 2. Three levels of detail

Public order-book data come at three levels of detail, and the level decides which questions can be answered:

| Level | What it shows | Example |
|---|---|---|
| **L1** | The best bid and the best ask, with their sizes | Binance's best bid and ask, used in Lecture 15, §5 |
| **L2** | Every level, with the total size resting there | **Bybit's book, used in Part IV**: 500 levels a side until mid-2025, 200 since, updated every 100 milliseconds |
| **L3** | Every single order: when it arrived, at which price and size, and when it was filled or cancelled | Some venues publish it live; historical L3 data are rare and usually paid for |

![The same moment at three levels of detail](figures/18_03_l1_l2_l3.png)
<sub><b>How to read the figure.</b> The book of figure 18_02 at three levels of detail, best 8 levels a side. <b>L1:</b> only the best bid and ask. <b>L2:</b> every level and its total size. <b>L3:</b> each level split into its individual orders, the first to arrive on the left. The split is invented at random for the illustration: our data do not contain it. The axis is cut at 1.6 BTC, so most of the best bid's 6.35 BTC lies off the panel.</sub>

L2 is the level of most public crypto data, and it answers most questions about liquidity: where the depth is, how wide the spread, what a market order costs. What it cannot show is the queue inside a level, and that matters to anyone whose order waits in it.

**What L2 cannot tell: one real window of 100 milliseconds.** On 12 March 2024, between 12:00:27.215 and 12:00:27.314 UTC, the size at the best bid of $72,117.20 changed as follows:

| What the data show | BTC | From |
|---|---|---|
| Resting at the best bid, before | 3.883 | The book (L2) |
| Sold into it by market orders, three trades | 0.132 | The trades |
| Resting at the best bid, after | 0.747 | The book (L2) |
| **Removed otherwise:** cancellations minus new orders that joined | **3.004** | The difference |

The book alone shows that the size fell by 3.136 BTC. Only the trades say that 0.132 BTC of that was filled; without them, a fall of the queue through trading could not be told from orders being withdrawn. Even with both, the last row is a net figure: L2 cannot say whether 3.004 BTC were cancelled, or 4 BTC were cancelled while 1 BTC of new orders joined.

**Why it matters for a waiting order.** Suppose our own order had been waiting at the back of that queue. The trades took 0.132 BTC from its front, so our order moved up by that much. Of the remaining orders ahead of us, some were cancelled. Since only 0.747 BTC rest at the level afterwards, at most 0.747 BTC can still be ahead of us, and as little as nothing if the orders that remain all joined behind us. Our position after 100 milliseconds is somewhere between the front of the queue and 0.747 BTC behind it. With L3, the exact position would be known. With L2, it must be estimated by a model of where in the queue cancellations happen, and the estimate becomes a range. Lecture 21 builds such models; the fills it simulates come as ranges for this reason.

The window has already used the two kinds of data that Part IV needs: the book, for what rests, and the trades, for what traded. Section 3 shows how to obtain both.
