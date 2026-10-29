# Lecture 19: Statistics of the Book: Imbalance, Microprice, Queues and Markouts

*Systematic Trading: Lecture Notes (MSc) · Oct 29, 2026 · Max Gnesi*

Lecture 18 rebuilt Bybit's BTCUSDT book and measured how deep and how tight it is. This lecture asks what the book's state at one moment says about what comes next: which side outweighs the other, where the price is likely to be once it has moved, how long a queue will last, and what a resting order is worth once it is filled. It first introduces each statistic on invented books, so that what it is meant to capture is clear, and then applies all of them to the 45 days of Lecture 18, 20 September to 3 November 2025, the liquidation cascade of 10 October included.

## 1. The book as a state

Part IV moves from describing the order book to trading on it, one step per lecture:

![Part IV in one line: Lecture 19 measures the book as it stands](figures/19_01_part_iv.png)
<sub><b>How to read the figure.</b> Each box is one lecture of Part IV, each building on the one before; this lecture is outlined, Lecture 18 is done. Above the boxes, the four stages: describing the book, measuring it, simulating our own orders in it, and trading strategies on it.</sub>

This lecture and the next are the measuring stage. They measure two different kinds of quantity, and the difference runs through both:

| Kind | What it is | Like, in accounts | Lecture |
|---|---|---|---|
| **A level** | The state of the book at one moment: how much rests where | A balance sheet: what is there on a given day | 19 |
| **A delta** | What changed over an interval: orders added, cancelled, filled | A cash-flow statement: what came in and went out over a period | 20 |

<sub><b>How to read the table.</b> The same word can name both kinds: Lecture 20 opens with an imbalance of the book (a level) next to an imbalance of the flow (a delta).</sub>

This lecture runs as follows:

| § | Step | Question |
|---|---|---|
| 1 | The book as a state | What can a level say about the next move? |
| 2 | The statistics | What do imbalance, the microprice, the shape of the book, queues and markouts each capture, shown on invented books? |
| 3 | On our 45 days | What do they look like on Bybit, and do they predict what they are meant to predict? |
| 4 | 10 October | Did any of them flag the cascade before it came? |
| 5 | Summary, exercises and reading | |

The idea of the lecture fits in one chart. On the left, a moment of Lecture 18: the best bid holds 28 times the size of the best ask. On the right, every update of our 45 days, sorted by that imbalance, and what the mid did next:

![Book imbalance and the next move of the mid: one lopsided book, and every update of the 45 days](figures/19_02_imbalance_key.png)
<sub><b>How to read the figure.</b> <b>Left:</b> Bybit BTCUSDT on 12 March 2024, 12:20:30 UTC (the moment of Lecture 18, §1), the best 5 levels on each side, sizes in BTC; the best bid and ask are outlined, and the imbalance at the best is worked out below. <b>Right:</b> every update of the 45 days in which the spread was one tick, 39 million, sorted into 20 bands of the imbalance at the best just before; each point is the share of those updates after which the mid's next move was up. The dotted line is 50%, a coin flip. The measure follows Gould and Bonart (2015); the data and the calculation are ours.</sub>

When the two best queues were balanced, the next move of the mid was up about half the time. The more the best bid outweighed the best ask, the more often the next move was up: 82% of the time when the bid held almost everything, 17% when the ask did. Gould and Bonart (2015) found the same kind of relationship on ten Nasdaq stocks, strongest on those whose spread is nearly always one tick, which is the case of BTCUSDT on Bybit (Lecture 18, §5.1).

The chart does not yet say that the imbalance is worth anything. The move it forecasts is one tick, $0.10 or about 0.01 bp, and a market order sent to profit from it pays more to trade than the move is worth. Its value, if it has one, lies with orders that already rest in the book: whether to stay in the queue or step out of it. Whether the relationship holds day by day, after the cascade and once the mechanics of small queues are accounted for, Section 3 tests; Section 2 first introduces the statistics.

## 2. The statistics

Each statistic is introduced the same way: what it is meant to capture, how it is computed, a picture of invented books that shows it at work, and what it misses. The books are invented so that each case is clean; Section 3 measures the same statistics on the data.

### 2.1 Book imbalance

**Key message.** Book imbalance says which side of the book outweighs the other. When one side's best queue is much smaller, a few trades can empty it, and the mid moves towards that side.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Take the size at the best bid, $`q^b`$, and at the best ask, $`q^a`$ | What a seller and a buyer can trade at the best price right now |
| 2 | Imbalance at the best: $`I = \frac{q^b - q^a}{q^b + q^a}`$ | −1: only asks; 0: balanced; +1: only bids |
| 3 | The same with the total size of the best 5 levels, or of all levels within x bp of the mid | How lopsided the book is a little deeper |

<sub><b>How to read the table.</b> Sizes in BTC; the formula is the queue imbalance of Gould and Bonart (2015).</sub>

![Book imbalance on three invented books: balanced, a thin best ask, heavy bids behind the best](figures/19_03_imbalance_card.png)
<sub><b>How to read the figure.</b> Three invented books, the best 5 levels on each side, sizes in BTC (bars full at 4 BTC); the best bid and ask are outlined. Under each book, the imbalance at the best and in the best 5 levels, and what it suggests.</sub>

Book A is balanced at the best and deeper: there is no lean, and the next move is as likely up as down. Book B has a thin best ask, 0.4 BTC against 4.0 BTC of bids: one small buy order empties it, and the mid moves up; the imbalance at the best is +0.82. Book C is balanced at the best, 0.5 BTC on each side, but the bids behind the best are four times the asks; the imbalance at the best reads zero, the one over the best 5 levels +0.58.

**What it misses.** Book C is the first blind spot: a measure at the best price does not see what stands behind it, and a deeper measure must choose how deep to look. The second is that the imbalance counts size, not intentions: an order can be cancelled the moment it is approached (Lecture 18, §5.5), and part of the lean in book B may vanish before a trade reaches it. The third is mechanical: a small queue is emptied by one ordinary trade, so part of what imbalance predicts is the arithmetic of queue sizes rather than information about the price; Section 3 separates the two.

**Can it be gamed?** A statistic that traders act on invites traders who want them to act. The simplest way to move book imbalance is to place a large order that is not meant to trade: a wall a few levels behind the best price, where it is unlikely to be filled, cancelled before the price reaches it. Other traders read a heavy book and lean the wrong way; the one who placed the wall trades against them. This is **spoofing**. Two weights make the imbalance harder to move: depth far from the best counts less, since a wall must stand back to stay unfilled, and depth that has only just arrived counts less, since a spoof is short-lived by design.

![Can imbalance be gamed? An honest book, a 10 BTC sell wall just placed, the wall cancelled](figures/19_05_spoofing_card.png)
<sub><b>How to read the figure.</b> Three moments of one invented book, the best 5 levels on each side, sizes in BTC (bars full at 4 BTC; ▶ larger). <b>2:</b> a sell order of 10 BTC is added at the fifth ask (dotted). Under each book, three versions of the imbalance over the best 5 levels: plain; weighted by distance, each level counting $`e^{-k/1.5}`$ at $`k`$ ticks behind the best; and weighted by distance counting only depth that has rested at least a second.</sub>

The wall turns the plain imbalance from +0.02 to −0.49, a book that seems to lean heavily towards the sellers. Weighting by distance dampens the swing to −0.14; leaving out the depth that arrived within the last second removes it. Neither weight is free. The distance weight needs a setting, how fast the weight falls, and Section 3 tests a wide range of them rather than one; the age weight needs the age of the orders, which L2 data do not show and Section 2.4 estimates. An order book also has honest orders that are short-lived: market makers revise their quotes many times a second (Lecture 18, §5.5), and a patient spoofer can let a wall age, at the price of a real chance of being filled. Weighting by age, as far as we know, is not a published measure; it is our construction, built on what the literature below says about spoofs.

Spoofing is one of several practices that work through the order book:

| Practice | What is done | What it is meant to achieve | What our data can show (L2 every 100 ms, trades, no accounts) |
|---|---|---|---|
| **Spoofing** | A large order not meant to trade, cancelled before execution | Make others lean the wrong way, and trade against them | Orders that look like spoofs: large, behind the best, removed without trades as the price approaches. Not the intent |
| **Layering** | Spoofing at several prices at once | The same, more convincingly | The same, over several levels |
| **Quote stuffing** | A flood of orders and cancellations | Congest the matching engine and the data feeds, so that others see the market late | Little: within 100 milliseconds, the messages net out |
| **Momentum ignition** | A burst of aggressive orders | Start a fast move that triggers others' stops or liquidations, and trade against it | Bursts of aggression followed by a reversal. Not the intent |
| **Wash trading** | Trading with oneself | Fake volume, to lift a venue's or a token's standing | Only statistically, in the trades: round sizes, odd patterns of digits |
| **Pinging** | Small orders sent to probe | Find hidden size, such as icebergs (Section 2.4) | Many trades of the minimum size, 0.001 BTC on Bybit. Often a search for information rather than manipulation |

<sub><b>How to read the table.</b> Spoofing and layering: Lee, Eom and Park (2013); Cartea, Jaimungal and Wang (2020). Quote stuffing: Gai, Yao and Ye (2013). Momentum ignition: SEC (2010). Wash trading on crypto exchanges: Cong et al. (2023).</sub>

Some facts put the table in proportion. In US futures markets, spoofing has been explicitly unlawful since the Dodd-Frank Act of 2010, which forbids "bidding or offering with the intent to cancel the bid or offer before execution"; the offence turns on intent, which market data cannot show, and regulators prove it with account records, not with the book. On the Korea Exchange, where accounts could be identified, about 0.8% of all orders were spoofs, and they paid (Lee, Eom and Park, 2013). On crypto exchanges, the distance at which a large order is posted is what makes it able to move prices, and by one estimate 31% of large orders could have been used to spoof (Fabre and Challet, 2025). Quote stuffing works because every link of the chain handles messages one at a time: on Nasdaq, a burst of messages in one stock slowed trading in other stocks that shared its data channel, and not in the rest (Gai, Yao and Ye, 2013). Venues defend themselves with caps on messages per account; Bybit counts requests per account and second, and its public feed, bundled into 100-millisecond updates, does not pass a flood on to other traders one message at a time.


**Where the profit of a flood comes from.** Quote stuffing earns nothing by itself; it earns by delaying other traders' cancellations. When the price jumps on another venue, every market maker on Bybit sends a cancellation of the quotes that are now too cheap, and the matching engine takes messages strictly in the order they arrive (Lecture 18, §1.3). A trader who sends a buy order first and a flood of junk messages straight after puts the junk between the buy and the cancellations:

![The stale-quote race: the same messages processed first come, first served, and with an asymmetric speed bump](figures/19_06_stale_quote_race.png)
<sub><b>How to read the figure.</b> Schematic. The price has just jumped on Binance; a market maker's ask at 100,000.1 on Bybit is now too cheap. The same messages in both rows, labelled with the time they reach the exchange after the jump; the box nearest the matching engine is processed first. <b>Top:</b> first come, first served. <b>Bottom:</b> orders that would trade at once are held 3 milliseconds at the gateway; all other messages pass.</sub>

In the top row the buy reaches the stale ask before the cancellation: the sniper buys at the old price, and the market maker has sold too cheaply. The profit lies in **stale quotes**, quotes that should have been cancelled but whose cancellation is stuck in the queue; the junk only makes the queue longer. The same race runs without any junk whenever a faster trader reacts to another venue before the market makers do, which is why it is the central risk of quoting on one venue against another (Lecture 24).

Exchanges can take the reward away. In the bottom row, an **asymmetric speed bump** holds orders that would trade at once for a few milliseconds and lets cancellations through, so the cancellation wins: TSX Alpha has delayed such orders by a random 1 to 3 milliseconds since 2015, and Eurex its aggressive orders in French equity options by 3 milliseconds since 2019, after which spreads narrowed and depth grew. Such delays are contested, since they favour one group of traders over another. A more radical design abolishes the race: **frequent batch auctions** collect orders over a short interval and match them together at one price, so that being a microsecond faster no longer counts (Budish, Cramton and Shim, 2015). Hyperliquid comes close to both: it gathers orders into blocks and, within each block, processes cancellations before orders that take liquidity. Caps on messages per account raise the cost of a flood; delays and batches remove its reward.

**How to deal with it.** A trader who uses imbalance cannot tell who placed a wall, but can make the measure hard to move and can check it against what actually trades:

| Defence | What it does |
|---|---|
| Weight depth by distance and by age | Fake depth stands back and is young; honest depth is mostly neither |
| Require persistence | Act on a lean only if it lasts, not on a single update |
| Check against the trades | A wall that is real is traded against; a lean that no trade confirms is suspect (the flow, Lecture 20) |
| Watch for walls that vanish | Count large orders removed without trades as the price approaches; many of them make the book less trustworthy |
| Know the venue's delay | When the exchange's own delay between matching and publishing jumps, the book on screen is older than usual (Section 4) |

<sub><b>How to read the table.</b> Detection in the literature follows the same lines: rules on the size, distance and fate of cancelled orders (Tuccella, Nadler and Serban, 2021), and statistical alarms when the book behaves unlike its normal self (Tao et al., 2020). None of them proves intent; they flag candidates.</sub>

### 2.2 The microprice

**Key message.** The mid is halfway between the best bid and ask whatever the queues look like. The microprice is the mid to expect once the price has moved: it leans towards the side that is likely to give way.

| Estimate | Calculation | Financial meaning |
|---|---|---|
| **Mid** | $`m = \frac{1}{2}(b + a)`$, with $`b`$ the best bid and $`a`$ the best ask | The price halfway between buying and selling, blind to the queues |
| **Weighted mid** | $`\frac{q^a\, b + q^b\, a}{q^b + q^a}`$ | Each price weighted by the size on the other side: it moves towards the thin side, as if that side were sure to be taken |
| **Microprice** | The expected mid after the price has moved, given the imbalance and the spread, estimated from data (Stoikov, 2018) | Where the price is likely to be, on average, once the next moves have happened |

<sub><b>How to read the table.</b> $`b`$, $`a`$: best bid and ask prices; $`q^b`$, $`q^a`$: the sizes there. Stoikov defines the microprice as the expected mid in the limit of many future moves; the figure shows its first step.</sub>

![The microprice on book B: two branches with their probabilities, and the expected mid once the price has moved](figures/19_04_microprice_card.png)
<sub><b>How to read the figure.</b> <b>1:</b> book B of figure 19_03, sizes in BTC. <b>2a, 2b:</b> the two ways the mid can move next, one tick up when the thin ask is taken, one tick down when the bid gives way, each with the book as it would look afterwards and an illustrative probability. <b>3:</b> on a ruler of prices, the mid now, the two future mids (larger dot, more likely), their probability-weighted average, the microprice, and the weighted mid for comparison. The probabilities are an illustration; Section 3 measures them.</sub>

In book B the weighted mid, 100,000.091, sits almost at the best ask: it treats the thin ask as good as gone. The microprice takes into account that the bid sometimes gives way instead; with the illustrative probabilities of the figure, it is 100,000.080. How far the price really tends to move from such a book is not a matter of formula but of data, which is why the microprice is estimated rather than calculated.

**What it misses.** The microprice is only as good as the data it is estimated from: in a regime unlike its sample, a cascade for example, its probabilities may no longer hold. It also inherits the blind spots of the imbalance it is built on: size that is cancelled before it trades, and depth behind the best that it does not use.

### 2.3 The shape of the book

**Key message.** Depth within a given distance of the mid is one number; the shape of the book says how that depth builds up level by level. Two books with the same depth can charge very different prices for the same order, and imbalance at the best price says nothing about it.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Cumulative depth: the size in the best $`k`$ levels of one side, for $`k = 1, 2, \ldots`$ | How much can be traded before the price has moved $`k`$ levels |
| 2 | Slope: the depth added per tick, or per basis point, as the price moves away from the best | A steep book adds much depth close to the price; a flat or hollow one little (Næs and Skjeltorp, 2006) |
| 3 | The cost of a given size: walk the cumulative depth until the size is filled (Lecture 18, §1.2) | What the shape means for an order |

<sub><b>How to read the table.</b> One side of the book at a time: asks for a buy, bids for a sell.</sub>

![The shape of the book: two invented ask sides with the same depth in their best 10 levels](figures/19_07_shape_card.png)
<sub><b>How to read the figure.</b> <b>Left:</b> two invented ask sides, the best 10 levels, sizes in BTC (bars full at 5 BTC). <b>Right:</b> their depth added up from the best ask, level by level; the dotted line is the size of a 3 BTC market buy, and the arrows mark how far it reaches in each.</sub>

Both sides hold 20 BTC in their best 10 levels, so a measure of depth within 10 ticks would call them equal. A 3 BTC market buy disagrees: on the steep side it takes 2 levels and pays on average 0.8 ticks above the mid, on the hollow one it takes 7 levels and pays 4.4 ticks, more than five times as much. A small order sees only the best level; how a book is shaped behind it matters for every order larger than the best queue.

**What it misses.** The shape is that of one moment: orders arrive while a large order walks the book, and depth taken is often replaced within a tenth of a second (Lecture 18, §5.5). The deep levels that make a book look steep are also where walls stand that are not meant to trade (Section 2.1). And the shape changes with the market: Næs and Skjeltorp (2006) find that flatter books go with more trading and higher volatility, so a shape measured on a calm day is not one to rely on in a fast one.

*Sections 2.4 and 2.5 (queues, markouts) and 3 to 5 follow.*

## References

- Budish, E., Cramton, P. and Shim, J. (2015). The high-frequency trading arms race: frequent batch auctions as a market design response. *Quarterly Journal of Economics* 130(4), 1547–1621. — frequent batch auctions (§2.1).
- Cartea, Á., Jaimungal, S. and Wang, Y. (2020). Spoofing and price manipulation in order-driven markets. *Applied Mathematical Finance* 27(1–2), 67–98. — a model of a spoofing seller (§2.1).
- Cong, L. W., Li, X., Tang, K. and Yang, Y. (2023). Crypto wash trading. *Management Science* 69(11), 6427–6454. — wash trading on crypto exchanges (§2.1).
- Fabre, T. and Challet, D. (2025). Learning the spoofability of limit order books with interpretable probabilistic neural networks. arXiv 2504.15908. — distance and spoofing on crypto exchanges (§2.1).
- Gai, J., Yao, C. and Ye, M. (2013). The externalities of high frequency trading. Working paper, SSRN. — quote stuffing across Nasdaq's channels (§2.1).
- Gould, M. D. and Bonart, J. (2015). Queue imbalance as a one-tick-ahead price predictor in a limit order book. arXiv 1512.03492. — the imbalance at the best and the next mid move (§1, §2.1).
- Lee, E. J., Eom, K. S. and Park, K. S. (2013). Microstructure-based manipulation: strategic behavior and performance of spoofing traders. *Journal of Financial Markets* 16(2), 227–252. — spoofing on the Korea Exchange (§2.1).
- Næs, R. and Skjeltorp, J. A. (2006). Order book characteristics and the volume–volatility relation: empirical evidence from a limit order market. *Journal of Financial Markets* 9(4), 408–432. — the slope of the book (§2.3).
- SEC (2010). Concept release on equity market structure. Release No. 34-61358, *Federal Register* 75, 3594. — momentum ignition (§2.1).
- Stoikov, S. (2018). The micro-price: a high-frequency estimator of future prices. *Quantitative Finance* 18(12), 1959–1966. — the microprice (§2.2).
- Tao, X., Day, A., Ling, L. and Drapeau, S. (2020). On detecting spoofing strategies in high frequency trading. arXiv 2009.14818. — statistical alarms (§2.1).
- Tuccella, J.-N., Nadler, P. and Serban, O. (2021). Protecting retail investors from order book spoofing using a GRU-based detection model. arXiv 2110.03687. — rules and a model for detection (§2.1).
