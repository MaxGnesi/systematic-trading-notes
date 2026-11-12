# Part IV roadmap: why would anyone be paid for quoting?

Part IV starts from the order book and ends with market making. One question runs through its eight lectures: **a market maker offers to buy and to sell, all day, to anyone. What is it paid for, what does it cost, and can we tell in advance whether it pays?** This page is the plot; each lecture explains its part.

## The plot, lecture by lecture

| Lecture | The question | What it adds to the plot | Status |
|---|---|---|---|
| [18. The order book](18-the-order-book/lecture.md) | What is in the book, and what can public data show? | The stage: where quotes stand. Public data show the size at each price, not who stands where, so a fill can never be read directly | Done |
| [19. Levels](19-statistics-of-the-book/lecture.md) | What does the book's state say about the next move? | A better fair price than the mid (the microprice), and the first bad news: filled resting orders lose | Done |
| [20. Deltas](20-statistics-of-the-flow/lecture.md) | What does the flow say? | Who a quote faces: most trading reacts to trading, and Binance moves first by tens of milliseconds. The candidates for telling a quoter when to step back | Done |
| [21. Replay](21-replaying-the-exchange/lecture.md) | What would have happened to our own orders? | The instrument: a way to test quotes on the recorded market, and how far it can be trusted, at the smallest size | Done |
| [22. A market that reacts](22-a-market-that-reacts/lecture.md) | What if the market responds to our order, and when does it tip? | Size and fragility: the measured reaction is added to the replay, and a laboratory market shows how players' behaviour adds up to calm absorption or a cascade. Normal slippage, the tipping point, and how to test an algorithm in both | Done |
| [23. Trading styles](23-trading-styles/lecture.md) | Which kinds of traders are at work, in what shares and when? | The other players: footprints of slicers, trend followers, snipers and makers in public data, tested in the laboratory market where the answer is known, then on Bybit | Done |
| [24. Market making on one venue](24-market-making/lecture.md) | What does it take to break even, and what can we not see? | The strategies: a quoting rule as a family of choices, from Avellaneda-Stoikov and ping-pong to stops, pauses and speed. The loss comes in the first second after a fill; every rule moves it by about a tenth of a basis point, no public fee level closes the gap, and resting orders pay as the execution of a strategy with an edge | Done |
| 25. Cross-exchange market making | Does hedging on a second venue help? | The hedge: quote on Bybit, lay off the risk on Binance, against latency and two sets of fees | Planned |

<sub><b>How to read the table.</b> Read top to bottom: each lecture uses what the ones above established. Planned lectures may change as results come in. Every result in Part IV is a result on one symbol, Bybit BTCUSDT, over 45 days from 20 September to 3 November 2025, with Binance's trades alongside; on this sample we cannot generalise.</sub>

## The sum a quote has to pass

Everything in Part IV feeds one sum. For a resting order:

| Term | What it is | Measured so far, order of 0.001 BTC at the best price |
|---|---|---|
| Half the spread | What we earn if the price does not move | About 0.005 bp |
| The move after the fill | Adverse selection: how far the price goes against us after we are filled | About −0.8 bp after 10 s ([Lecture 21, §3.4](21-replaying-the-exchange/lecture.md)) |
| The position carried | What the fills leave behind, held until it is closed | Small with either sign on ordinary evenings; −7.3 bp in the 10 October cascade for a quoter with no limit ([Lecture 21, §5.1](21-replaying-the-exchange/lecture.md)) |
| The maker fee | What the exchange charges at the base tier | −2 bp |

<sub><b>How to read the table.</b> A quote at the best price, at Bybit's base fee, on our sample, loses about 2.8 bp per fill before the position. A markout is measured from our own price, so the move after the fill already contains the half-spread. The later lectures ask what can change this sum: quoting wider, a lower fee, stepping back at the right moments, a limit on the position, or a hedge.</sub>

## The threads

Each idea below is met more than once. The table shows where it first appears and where it is taken furthest.

| Thread | In plain words | Where it appears | Taken furthest in |
|---|---|---|---|
| What the spread pays for | Order costs, the risk of holding a position, and trading with someone who knows more | 15, 19 | 24 |
| Inventory risk | We hold a position and the price wanders; it can be managed by limits, skewed quotes or a hedge | 17 | 24, 25 |
| Adverse selection | The fill itself is bad news; rules about inventory cannot fix it | 15, 19, 21 | 24 |
| Fills we cannot see | Why market making is the hardest strategy to backtest | 18, 19, 21 | 22 |
| The vanishing book | Displayed size is not promised size: quotes leave when they matter most, and many leave together | 18, 19, 21 | 24 |
| Speed | The latency gap, stale quotes, and who moves first | 20, 21 | 24, 25 |
| The place in the line | Where we stand, and what an early place is worth | 19, 21 | 24 |
| Signals | Whether the book and the flow tell a quoter when to step back | 19, 20 | 24 |
| When to quote | Time of day, the clock of the book, stepping aside after violent hours, decided only from what is known at the time | 17, 19, 20, 21 | 24 |
| Fees | The tier can decide the whole business; the fee at which a rule breaks even is a result in itself | 15, 19, 21 | 24, 25 |
| Size | What works at the minimum may fail at larger sizes | 21 | 22, 24 |
| The crash of 10 October | Every measure again in the cascade | 18, 19, 20, 21 | 22, 24 |
| Crypto's own features | Funding, liquidations, a market with no close | 15, 16 | 24 |
| Running it for real | Risk limits, kill switches, what happens when the feed drops; profit split into spread, adverse selection, inventory and fees | | 24, 25 |
| Who is allowed to do what | Spoofing and layering, speed bumps, quoting obligations, fee schedules as market design | 19 | 24, 25 |

<sub><b>How to read the table.</b> The numbers are lectures. Entries for Lectures 23 to 25 are plans.</sub>
