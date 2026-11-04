# Part IV roadmap: why would anyone be paid for quoting?

Part IV starts from the order book and ends with market making. One question runs through its seven lectures: **a market maker offers to buy and to sell, all day, to anyone. What is it paid for, what does it cost, and can we tell in advance whether it pays?** This page is the plot; each lecture explains its part.

## The plot, lecture by lecture

| Lecture | The question | What it adds to the plot | Status |
|---|---|---|---|
| [18. The order book](18-the-order-book/lecture.md) | What is in the book, and what can public data show? | The stage: where quotes stand. Public data show the size at each price, not who stands where, so a fill can never be read directly | Done |
| [19. Levels](19-statistics-of-the-book/lecture.md) | What does the book's state say about the next move? | A better fair price than the mid (the microprice), and the first bad news: filled resting orders lose | Done |
| [20. Deltas](20-statistics-of-the-flow/lecture.md) | What does the flow say? | Who a quote faces: most trading reacts to trading, and Binance moves first by tens of milliseconds. The candidates for telling a quoter when to step back | Done |
| [21. Replay](21-replaying-the-exchange/lecture.md) | What would have happened to our own orders? | The instrument: a way to test quotes on the recorded market, and how far it can be trusted, at the smallest size | In progress |
| 22. A market that reacts | What if the market responds to our order? | Size: the replay ignores our footprint. Here the measured reaction is added on top, for orders too large to ignore | Planned |
| 23. Market making on one venue | Which quoting rules pay, at which fee, and why? | The strategies: the grid at the best price, Avellaneda-Stoikov with extras, ping-pong, steering by the signals of Lectures 19 and 20, and choosing when to quote. Every result split into what earned and what cost | Planned |
| 24. Cross-exchange market making | Does hedging on a second venue help? | The hedge: quote on Bybit, lay off the risk on Binance, against latency and two sets of fees | Planned |

<sub><b>How to read the table.</b> Read top to bottom: each lecture uses what the ones above established. Planned lectures may change as results come in. Every result in Part IV is a result on one symbol, Bybit BTCUSDT, over 45 days from 20 September to 3 November 2025, with Binance's trades alongside; on this sample we cannot generalise.</sub>

## The sum a quote has to pass

Everything in Part IV feeds one sum. For a resting order:

| Term | What it is | Measured so far, order of 0.001 BTC at the best price |
|---|---|---|
| Half the spread | What we earn if the price does not move | About 0.005 bp |
| The move after the fill | Adverse selection: how far the price goes against us after we are filled | About −0.8 bp after 10 s ([Lecture 21, §3.4](21-replaying-the-exchange/lecture.md)) |
| The maker fee | What the exchange charges at the base tier | −2 bp |

<sub><b>How to read the table.</b> A quote at the best price, at Bybit's base fee, on our sample, loses about 2.8 bp per fill. The later lectures ask what can change this sum: quoting wider, a lower fee, stepping back at the right moments, or a hedge.</sub>

## The threads

Each idea below is met more than once. The table shows where it first appears and where it is taken furthest.

| Thread | In plain words | Where it appears | Taken furthest in |
|---|---|---|---|
| What the spread pays for | Order costs, the risk of holding a position, and trading with someone who knows more | 15, 19 | 23 |
| Inventory risk | We hold a position and the price wanders; it can be managed by limits, skewed quotes or a hedge | 17 | 23, 24 |
| Adverse selection | The fill itself is bad news; rules about inventory cannot fix it | 15, 19, 21 | 23 |
| Fills we cannot see | Why market making is the hardest strategy to backtest | 18, 19, 21 | 22 |
| The vanishing book | Displayed size is not promised size: quotes leave when they matter most, and many leave together | 18, 19, 21 | 23 |
| Speed | The latency gap, stale quotes, and who moves first | 20, 21 | 23, 24 |
| The place in the line | Where we stand, and what an early place is worth | 19, 21 | 23 |
| Signals | Whether the book and the flow tell a quoter when to step back | 19, 20 | 23 |
| When to quote | Time of day, the clock of the book, stepping aside after violent hours, decided only from what is known at the time | 17, 19, 20, 21 | 23 |
| Fees | The tier can decide the whole business; the fee at which a rule breaks even is a result in itself | 15, 19, 21 | 23, 24 |
| Size | What works at the minimum may fail at larger sizes | 21 | 22, 23 |
| The crash of 10 October | Every measure again in the cascade | 18, 19, 20, 21 | 23 |
| Crypto's own features | Funding, liquidations, a market with no close | 15, 16 | 23 |
| Running it for real | Risk limits, kill switches, what happens when the feed drops; profit split into spread, adverse selection, inventory and fees | | 23, 24 |
| Who is allowed to do what | Spoofing and layering, speed bumps, quoting obligations, fee schedules as market design | 19 | 23, 24 |

<sub><b>How to read the table.</b> The numbers are lectures. Entries for Lectures 22 to 24 are plans.</sub>
