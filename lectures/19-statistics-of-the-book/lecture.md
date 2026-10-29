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

*Sections 2.3 to 2.5 (the shape of the book, queues, markouts), 3 to 5 and the references follow.*
