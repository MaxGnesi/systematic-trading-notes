# Lecture 21: Replaying the Exchange: Fill Rules, Queue Position, Latency and Adverse Fills

*Systematic Trading: Lecture Notes (MSc) · Nov 1, 2026 · Max Gnesi*

Lectures 18 to 20 described Bybit's BTCUSDT book, measured its state and measured its flow. This lecture puts our own orders into the recorded market and asks what would have happened to them: when a resting order is filled, at what price a market order is executed, and what the price does afterwards. A replay is only useful if it tells the truth, so the lecture builds one piece by piece and then tests it on the same 45 days, 20 September to 3 November 2025. The hypotheses were fixed before any result was computed ([results/hypotheses.md](results/hypotheses.md)).

*Draft: Sections 1 and 2.1 to 2.3. The rest follows the plan in [results/hypotheses.md](results/hypotheses.md).*

## 1. Three replays of one order

Part IV moves from describing the order book to trading on it, one step per lecture:

![Part IV in one line: Lecture 21 puts our own orders into the recorded market](figures/21_01_part_iv.png)
<sub><b>How to read the figure.</b> Each box is one lecture of Part IV, each building on the one before; this lecture is outlined, Lectures 18 to 20 are done. Above the boxes, the four stages: describing the book, measuring it, simulating our own orders in it, and trading strategies on it.</sub>

A **replay** runs the recorded book and trades forward in time and inserts hypothetical orders of ours into them. The recorded market does not react to our orders: nobody cancels because our bid appeared, and nobody sells into it because it is there. That reaction is left out on purpose here and is the subject of Lecture 22. A market order in a replay is simple to judge: it trades against the book that stands when it arrives. A resting order is not, because the data never say when it would have been filled. The replay has to supply a **fill rule**, and the three rules in common use give different answers:

| Rule | Our resting bid is filled when | What it assumes |
|---|---|---|
| Touch | the first sell trade occurs at our price | we are first in line at our price |
| Queue | the size that stood ahead of us when we joined has been traded or cancelled, and a sell trade then reaches us | we join at the back of the line; how the cancellations split between ahead of us and behind us is unknown |
| Trade-through | a sell trade occurs below our price | everyone at our price has been filled, us included; Lecture 17's rule |

<sub><b>How to read the table.</b> A sell trade is a trade started by a seller (a taker selling into the bids). The same rules apply to a resting ask with buy trades and prices above. Touch and trade-through need only the trades; the queue rule also needs the size displayed at our price, from the book.</sub>

The idea of the lecture fits in one chart. On the left, one real moment followed under each rule; on the right, the same order placed again and again over one day:

![Three replays of one order: when a resting bid at the best is filled under the touch, queue and trade-through rules, and the price after the fill](figures/21_02_three_replays.png)
<sub><b>How to read the figure.</b> Bybit BTCUSDT, a resting bid of 0.001 BTC (Bybit's minimum) placed at the best bid; it becomes active 50 ms after the decision and is held up to 120 s, not moved. <b>Left, top:</b> 1 October 2025 from 09:33:15 UTC: the best bid (black) and ask (grey, one tick above), our price (dotted), sell trades at our price (circles) and below it (crosses); a vertical line marks the fill under each rule, labelled with the wait and with the mid 10 s after the fill minus our price, in basis points (bp, hundredths of a percent; 1 bp is about USD 11.6 here). <b>Left, bottom:</b> the size displayed at our price (grey) and the size ahead of us under the queue rule, with cancellations split evenly over the line (dark blue, a = 1) and with every cancellation put behind us where possible (light blue, dashed, a = ∞); vertical lines mark the two queue fills. <b>Right:</b> the same order placed every 15 s over all of 1 October, 5,760 orders. Top, the share filled within 120 s under each rule; bottom, the average over fills of the mid 1 s and 10 s after the fill minus our price, in bp. Below zero means the price fell after our bid was filled. One day of the in-sample period.</sub>

The bid joined at USD 116,165.90 behind 10.2 BTC already displayed there. Four moments decide the story:

| Seconds after 09:33:15 | What happened | Touch | Queue | Trade-through |
|---|---|---|---|---|
| 0.3 | A seller takes 0.003 BTC at our price | **filled** | 10.2 BTC ahead of us | waiting |
| 0.3 to 5.0 | Sellers take 0.26 BTC at our price; some size is cancelled | | ahead: 8.2 BTC (a = 1), 9.7 BTC (a = ∞) | waiting |
| 5.1 to 5.2 | 9.9 BTC is cancelled at our price within two book updates | | ahead: 0.13 BTC (a = 1), 0.16 BTC (a = ∞) | waiting |
| 7.8 and 10.7 | Sellers take 0.05 BTC, then 0.38 BTC at our price | | **filled** at 7.8 s (a = 1), at 10.7 s (a = ∞) | waiting |
| 15.7 | A seller trades below our price | | | **filled** |

<sub><b>How to read the table.</b> One row per event that moves our order; "ahead" is the size in front of our bid under the queue rule, for the two ends of the unknown split of cancellations. Ten seconds after the trade-through, the best bid stood USD 30.7 below our price.</sub>

Under the touch rule the order was filled within a third of a second by the first small seller, at a moment when the price had not moved; the 10.2 BTC ahead of us would in fact have been filled first. Under the queue rule it waited until the line in front of it had gone, and was filled 5 to 8 seconds before the price fell through its level. Under trade-through it was filled only as the fall began, and 10 seconds later the mid was 2.6 bp below its price. The same order, in the same recorded market, earned a 10-second markout of 0.0 bp, −0.9 bp or −2.6 bp, depending only on the rule the replay used.

The moment also shows what the queue rule cannot know. The book reports how much is displayed at our price, not whose orders left. When 9.9 BTC vanished at 5.1 seconds, the rule had to decide how much of it stood ahead of us. Here the answer hardly mattered: only 0.3 BTC stood behind us, so at least 9.6 BTC of the cancelled size must have been ahead, whatever the split. In calmer moments the split decides how long we wait, which is why the lecture carries both ends of it, and the values between, through every result (hypothesis H3).

Over the whole day the picture is the same, and it explains why the naive rule flatters:

| Rule | Filled within 120 s | Median wait (filled orders) | Mid 1 s after, bp | Mid 10 s after, bp | Fills that came only when the price ran through |
|---|---|---|---|---|---|
| Touch | 96% | 0.6 s | −0.13 | −0.12 | |
| Queue, a = 1 | 87% | 5.5 s | −0.55 | −0.65 | 61% |
| Queue, a = ∞ | 86% | 6.1 s | −0.61 | −0.71 | 77% |
| Trade-through | 84% | 6.8 s | −0.68 | −0.78 | 100% |

<sub><b>How to read the table.</b> The order of the figure, placed every 15 s on 1 October 2025, 5,760 orders. "Mid 1 s after" and "Mid 10 s after": the average over fills of the mid 1 s or 10 s after the fill minus our price, in bp; the bid starts half a tick (0.004 bp) above zero, so values near zero mean the price did not move. Last column: the share of the queue rule's fills that came at the trade-through itself, because the line had not been used up before. The fee is not included. Our calculation for these notes.</sub>

The touch rule fills almost every order and quickly, and its fills see the price barely move. The rules that respect the line fill a few orders fewer, later and at worse prices, and most of their fills come only when the price runs through the level. The fills the touch rule adds are the good ones: a seller arrived while the line was long and the price stable. A replay that uses it reports fills a real order at the back of the line would not have had. Lalor and Swishchuk (2024) make the same point for futures: simulations that assume every fill is non-adverse and at the front of the queue are "over-inflated".

Two cautions keep the chart in proportion. First, it is one day of the in-sample period, and the order is held rather than re-posted, so it shows the mechanism, not a result; whether the touch rule flatters out of sample, with the test order of Section 4, is hypothesis H1. Second, all three rules leave out two things that act on a real order: the time our order needs to reach the exchange, during which the book changes, and the market's reaction to our order itself. The first is part of this lecture; the second is Lecture 22.

This lecture runs as follows:

| § | Step | Question |
|---|---|---|
| 1 | Three replays of one order | Does the fill rule change what a replay reports? |
| 2 | The pieces of the puzzle | What is a replay made of: the latency gap, the queue, adverse fills, our footprint, and the families of models used for each? |
| 3 | The replay on our data | How are trades ordered against the book, how does a market order walk the book after a delay, and how is a resting order's place in the line tracked? |
| 4 | Does the replay tell the truth? | Hypotheses H1 to H9: do the naive rules flatter, are trade-through fills the bad ones, does the unknown split decide the answer, is the replay kinder than real fills, and up to what order size does it hold? |
| 5 | 10 October | What would the replay have done to our orders in the cascade? |
| 6 | Summary, exercises and reading | |

## 2. The pieces of the puzzle

Section 1 showed that one choice, the fill rule, changes what a replay reports. A replay rests on several such choices, and this section lays them out before any of them is measured. Each piece gets the same card: the key message, how it is computed, an invented example and what it misses. The examples share one invented book, so each card adds to the last; Section 3 builds the same pieces on our data.

| § | Piece | The question it answers | Built on our data in |
|---|---|---|---|
| 2.1 | What a replay is | What do the recorded data say, and what must a replay infer? | §3.1 |
| 2.2 | The latency gap | What changes between the moment we decide and the moment our order arrives? | §3.2 |
| 2.3 | The queue | How much stands ahead of our resting order, and when does our turn come? | §3.3 |
| 2.4 | Adverse fills | Why are the fills we do get the worse ones? | §3.4 |
| 2.5 | Our footprint | What does a replay leave out on purpose? | Lecture 22 |
| 2.6 | The models side by side | Which families of models exist for each piece, and where is each used? | |

### 2.1 What a replay is

**Key message.** A replay runs the recorded book and trades forward in one time order and inserts our orders into them. Part of what it needs is recorded; the rest, such as how much was cancelled at our price, it must infer. And the recorded market never responds to our orders.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | Merge the two recorded streams in time order: the book updates (every 100 ms on Bybit's feed of 200 levels, Lecture 18) and the trades (to the millisecond) | One clock for everything that happened at our price |
| 2 | Between two book updates, every trade at our price lowers the size there by its own size | The part of the change we know: it was filled |
| 3 | At the next update, the change beyond those trades: a decrease was cancelled, an increase was added | The part we infer: the book shows how much is there, not who came or left |
| 4 | Our order, decided at time $`t`$, becomes active at $`t + L`$ and meets what stands then | $`L`$ is the latency: the time our order needs to reach the matching engine (§2.2) |
| 5 | Our resting order is filled by the recorded trades, under a fill rule (§1); the recorded streams themselves stay as they were | Non-reactive: nobody responds to our order, and our fills take nothing out of the recorded book (§2.5) |

<sub><b>How to read the table.</b> Steps 1 to 3 rebuild what happened at one price; steps 4 and 5 add our order. The book's clock is the matching engine's time (cts, Lecture 18); trades between two updates are applied before the update, the event order fixed in [results/hypotheses.md](results/hypotheses.md).</sub>

![What a replay is: two recorded streams at one price, and the size traded, cancelled and added inferred from them](figures/21_03_replay_card.png)
<sub><b>How to read the figure.</b> An invented bid at USD 100,000.0. <b>Top:</b> what is recorded: the book, every 100 ms, reports the size displayed at that price (squares); the trades, to the millisecond, report each sale at that price (triangles). <b>Bottom:</b> the size at that price as the replay infers it, with each change coloured by its cause: a trade (orange), a decrease beyond the trades, counted as cancelled (grey), an increase, counted as added (green). Dotted: a bid of ours decided at 10 ms and arriving 50 ms later.</sub>

Between the first two updates the displayed size fell from 2.0 to 1.2 BTC. Trades account for 0.5 of it, 0.3 and then 0.2, so the replay counts the other 0.3 as cancelled. Between the next two, 0.4 BTC was sold and yet the size rose from 1.2 to 1.6: 0.8 was added. Our bid, decided at 10 ms, arrives at 60 ms. The last book the replay has seen still reports 2.0 BTC, but 0.3 has been sold since, so 1.7 BTC stands ahead of our bid when it joins.

**Net, not gross.** The book reports only the net change between two updates. The 0.8 BTC added could have been 1.0 added and 0.2 cancelled, or an order placed and withdrawn twice; a replay built on 100 ms updates cannot tell. Lecture 18 (§4.4) met the same blind spot from the other side: a tenth of the trades happened at prices that the book of up to 100 ms earlier never showed, orders that arrived and were filled between two updates.

**What it misses.** First, the gross flow inside each update, as above. Second, who cancelled: the book says that 0.3 BTC left the price, not whether it stood ahead of our bid or behind it; §2.3 shows why that matters. Third, the exact order of events within the same millisecond, and any difference between the clocks of the two streams, such as Bybit's publish delay (Lecture 19, §4). Fourth, our footprint: in the replay our bid takes part in no trade's record, and its presence changes nobody's behaviour (§2.5).

### 2.2 The latency gap

**Key message.** Our order meets a later book than the one we decided on. In that gap faster traders act, and they act most when the price is about to move: the trades we miss are disproportionately the ones that would have paid.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | The book we decide on was published at the last update and reached us after a delay | Feed latency: our picture is already old when we look at it |
| 2 | An order decided at $`t`$ reaches the matching engine at $`t + L`$ | Order-entry latency $`L`$: the time it takes to get our decision to the exchange |
| 3 | A market order walks the book that stands at $`t + L`$; slippage = the average price expected from the book seen at $`t`$ minus the average price paid (for a buy) | The cost of the gap for an order that must be filled |
| 4 | A limit order at the best price seen at $`t`$ (immediate-or-cancel) takes only what stands at that price at $`t + L`$; the rest is not filled | The gap as missed trades, for an order that must not pay more |
| 5 | A cancellation also takes $`L`$ to arrive: a resting order can be filled after we decided to withdraw it | The gap for a resting order: a stale quote picked off |

<sub><b>How to read the table.</b> Steps 1 and 2 add up to the gap between the book we saw and the book our order meets. Steps 3 to 5 are its cost for the three kinds of order of this lecture. A replay applies them by evaluating every order of ours against the recorded book at $`t + L`$, never at $`t`$.</sub>

![The latency gap: the book we decide on and the book our order meets, on the invented book; and how often live market orders on Bybit missed the best price, by the return that followed](figures/21_04_latency_card.png)
<sub><b>How to read the figure.</b> <b>Left and middle:</b> the ask side of the invented book of §2.1, best three levels. At 10 ms we decide to buy 0.5 BTC on the book last seen (light blue: what we expect to buy); a faster buyer takes 0.4 BTC at the best ask at 40 ms; our order arrives at 60 ms and buys what stands then (dark blue). Grey: size left in the book. <b>Right:</b> from Albers, Cucuringu, Howison and Shestopaloff (2025), eq. 17 with their Table 6: the share of their own minimum-size market orders on Bybit that could not be filled at the best ask or bid they had seen, against the return over the next ten trigger events of their experiment (a median of 1.14 s), positive when the price moved in the order's favour.</sub>

On the book we saw, 0.6 BTC was offered at USD 100,000.1, enough for our 0.5 at one price. By the time our order arrived, a faster buyer had taken 0.4 of it. A market order still gets its 0.5 BTC, 0.2 at USD 100,000.1 and 0.3 one tick higher, an average of USD 100,000.16 instead of 100,000.1. A limit order at USD 100,000.1 pays no more, but buys only 0.2 BTC. Suppose the faster buyer was right and the ask stands at USD 100,000.6 a second later: the 0.3 BTC the limit order missed is exactly the part that would have earned most.

**Good orders fail.** Albers et al. (2025) measured this live: 3.1 million market orders of the minimum size on Bybit's inverse BTCUSD perpetual in April 2023, sent from a server close to the exchange, each one compared with the best price it had seen. Overall 1.35% could not be filled at that price. When the price then fell or stayed, almost none failed (0.09%); as soon as it rose in the order's favour, the share jumped to 4.2% and grew by 2.2 percentage points per basis point of return: 15% at +5 bp, 26% at +10 bp. Failures were also more frequent in volatile hours. A backtest that fills every order at the price seen at the decision is therefore wrong in a biased way: it keeps the trades that paid and that, in reality, others took first.

**What it misses.** First, $`L`$ itself: it differs by trader, connection and moment, and it rises in busy markets, exactly when it matters; the replay takes it as a fixed parameter and reports results at 10, 50 and 100 ms. Second, the race: the recorded trades show who won each race, not who else was racing. In the replay, our order arrives after every recorded trade that happened before $`t + L`$, even if in reality we might have been faster. Third, the recorded book at $`t + L`$ is itself known only to the last update plus the trades since (§2.1). Fourth, Albers et al.'s numbers come from a different contract (inverse, priced in USD with a 0.5 USD tick) and from 2023; on our data the replay can show the mechanism but cannot measure true failure rates, which only live orders reveal.

### 2.3 The queue

**Key message.** A resting order is filled only when everything ahead of it at its price has traded or left. The book shows how long the line is, not who leaves it, so a replay must assume how cancellations split between ahead of us and behind us. One dial, $`a`$, spans the assumptions, from an even split to "never ahead of us".

Lecture 19 (§2.4) introduced the line and showed that L2 data cannot say whose order was cancelled. This card turns the line into the queue rule of §1.

| Step | Calculation | Financial meaning |
|---|---|---|
| 1 | When our order arrives, the size ahead of it is the size displayed at our price: the last update minus the trades since (§2.1) | We join at the back: everyone already there was first |
| 2 | A sell trade of size $`s`$ at our price: if $`s`$ is larger than the size ahead, we are filled; otherwise the size ahead falls by $`s`$ | Trades serve the line from the front |
| 3 | A cancellation of size $`c`$ at our price (§2.1, step 3): the size ahead falls by $`p \cdot c`$, with $`p = x^a`$ and $`x`$ = ahead / (ahead + behind); never more is taken from behind us than stands there | Someone left the line; $`p`$ is the share assumed to have stood in front of us |
| 4 | An increase at our price joins behind us | Later arrivals queue after us |
| 5 | A sell trade below our price fills whatever is left of our order | The whole line at our price has been served |

<sub><b>How to read the table.</b> $`x`$ is our position in the line, the share of the displayed size that stands ahead of us: 1 at the back, 0 at the front. The dial $`a`$ sets $`p`$: $`a = 1`$ splits a cancellation in proportion to the size on each side, as if every unit of size were equally likely to leave; a larger $`a`$ puts more of it behind us; $`a = \infty`$ puts none ahead unless nobody stands behind us, the "risk-averse" model of hftbacktest. Our results use $`a`$ = 1, 2, 5, 20 and ∞ (hypothesis H3).</sub>

![The queue on the invented book: the size ahead of our bid under three dials, and the share of a cancellation put ahead of us as a function of our position](figures/21_05_queue_card.png)
<sub><b>How to read the figure.</b> <b>Left:</b> the bid of §2.1 at USD 100,000.0 joins at 60 ms behind 1.7 BTC, and the invented book runs on to 420 ms. Grey: the size displayed at our price, without our order; blue lines: the size ahead of our bid, under $`a = 1`$ (solid), $`a = 2`$ (dotted) and $`a = \infty`$ (dashed); stars: our fill under each; orange line: the touch rule's fill. Triangles: sell trades at our price, with their size; cross: a sell below our price. <b>Right:</b> $`p = x^a`$ against $`x`$ for $`a`$ = 1, 2, 5 and 20, and $`a = \infty`$ (dashed); the dot marks our bid at 300 ms.</sub>

Until 200 ms the dial plays no part. The cancellation at 100 ms happened before anyone joined behind us, so all of it stood ahead; trades then shorten the line from 1.7 to 0.8 BTC. At 200 ms, 0.8 BTC joins behind us. At 300 ms, 0.8 BTC is cancelled, and now the answer depends on the dial: with 0.6 BTC ahead and 0.8 behind, $`x = 0.43`$.

| Dial | Share of the 0.8 BTC put ahead of us | Size ahead after 300 ms | Filled |
|---|---|---|---|
| Touch rule (no line) | | | at 70 ms, by the first sell of 0.2 BTC |
| $`a = 1`$ | 43% | 0.26 BTC | at 340 ms, by the sell of 0.5 BTC |
| $`a = 2`$ | 18% | 0.45 BTC | at 340 ms, by the sell of 0.5 BTC |
| $`a = \infty`$ | 0% | 0.60 BTC | at 420 ms, when the price runs through |

<sub><b>How to read the table.</b> The invented example of the figure. Under $`a = \infty`$ the sell of 0.5 BTC at 340 ms leaves 0.1 BTC ahead of us, and our turn never comes before the price moves through our level.</sub>

The touch rule fills the bid 270 ms before any version of the line would, while 1.7 BTC still stood in front of it. Among the queue rules, the dial moves the fill from a trade at our price to the moment the price runs through it: the same order becomes a fill at a stable price or a fill just before a fall (§2.4).

**The dial in the literature.** Rigtorp (2013) proposed the split for L2 data, with the share ahead set by a function of the size ahead and behind, and suggested calibrating it on one's own fills. The open-source backtester hftbacktest offers the risk-averse model and probabilistic splits of the same kind. Databento (2025), with order-by-order data from CME's E-mini S&P 500 future, reported that cancellations come mostly from the back of the line, "much stronger than you'd think"; the example code that goes with it uses a power of the position of the same shape as our $`x^a`$, with $`a`$ of 1 or more. One reason for the back, an argument rather than a measurement: an order that has just joined has the least to lose by leaving, while an order near the front is about to be filled.

**What it misses.** First, the truth: which orders were cancelled is recorded only in order-by-order (L3) data, which Bybit does not publish (Lecture 18, §2), so on our data the dial can be varied but not measured. Second, the split may depend on more than our position: on how long the line is, on how fast the price is moving, on the hour (Lecture 19, §3.7). Third, everything inside one 100 ms update (§2.1): a large order that joins and leaves within it is never seen. Fourth, our own order is not in the displayed size, so the line behind us is the size added after we joined, not including us; for an order of 0.001 BTC this changes nothing, for 5 BTC it does (§2.5).
