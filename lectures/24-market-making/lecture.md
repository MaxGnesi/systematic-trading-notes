# Lecture 24: Market Making on One Venue: What It Takes to Break Even

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 12, 2026 · Max Gnesi*

Lecture 23 showed whom a quote on Bybit's BTCUSDT perpetual meets: mostly ordinary flow, and now and then a trader who takes the quote just after Binance has moved. This lecture puts our own quotes into that market. A market maker posts a bid and an ask, earns the spread when both are filled, and pays when the price moves against what it has just bought or sold. The question is not whether a clever rule beats the market, but what it takes to break even, what a profitable maker must have that a replay of public data cannot show, and where resting quotes earn their place when they do not pay on their own: as the way a strategy with its own edge, a trend rule or a relative-value trade, gets into and out of its positions. Every design runs in Lecture 21's replay of the exchange, with 50 ms between a decision and its arrival, on 20 September to 3 November 2025; the hypotheses were fixed before any result was computed, and every change is dated ([results/hypotheses.md](results/hypotheses.md)).

## 1. Where a market maker's money goes

The lecture's result fits in one chart: five ways of quoting, and where each one's money went.

![Where a market maker's money goes](figures/24_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Result in bp of the value traded (x), one bar per quoting rule (y), over the 24 out-of-sample days (11 October to 3 November 2025). Each bar is split into the parts of the result: <b>orange</b>, at the fill and in the first second after it, the spread earned less the move of the mid against us; <b>yellow</b>, the move against us from 1 to 10 s; <b>blue</b>, the gain or loss on positions held beyond 10 s; <b>grey</b>, fees, 2 bp of the value for a resting order and 5.5 bp for a market order (Bybit's standard tier). <b>Diamond:</b> the result after fees. The rules are described in §3. Our calculation, Bybit BTCUSDT perpetual, 0.001 BTC orders.</sub>

Every rule loses, and almost all of the loss before fees comes in the first second. A quote at the best price earns half the spread, but on bitcoin the spread is one tick, 0.1 USDT, about 0.005 bp per fill; what decides the result is that the orders which reach our quote are, on average, followed by a move against us of 0.4 to 0.9 bp within the second. The positions the rules carry beyond ten seconds cost nothing on average, which is why stops do not help (§3). Fees then add 2 bp on every unit of value for a rule that only rests, and more for one that closes with market orders: ping-pong halves the loss before fees, but 37% of what it trades goes through its stops at the taker fee, and after fees it does worst.

Seen this way, a rule changes the result by a tenth of a basis point here and there, and the gap to break even is about 0.9 bp before fees, plus whatever fee is paid. The rest of the lecture asks where that gap could be closed:

| § | Step | Question |
|---|---|---|
| 1 | Where the money goes | What does a quote earn, and what does it lose? |
| 2 | A quoting rule as a family | Which choices define a market-making rule, and which did we test? |
| 3 | The designs | What does each choice change: guard, depth, inventory skew, ping-pong, stops? (H1 to H4) |
| 4 | Tests | Which designs beat the baseline out of sample, and over what range of settings? |
| 5 | 10 October 2025 | Which rule does best through a crash, and where does each lose? A case study |
| 6 | What it takes to break even | Fees, rebates, speed, queue position and hedging, against the 0.9 bp gap; what we cannot see |
| 7 | Where market making pays | Resting quotes as the execution of another strategy: what they save against market orders, and what they cost |

## 2. A quoting rule as a family of choices

A market-making rule is not one strategy but a set of choices, each answering a question that every maker has to answer. The table lists them, the options open at each, which we tested and what the test gave. The results are on our implementation and our sample, Bybit's BTCUSDT perpetual at 0.001 BTC and 50 ms; a different implementation can give different results, and the untested options are left open on purpose.

| Choice | The question | Options | Tested here | What it gave, before fees (§3, §4) |
|---|---|---|---|---|
| **Price** | Where do our quotes sit? | At the best; k ticks behind it; k bp deep; around a reservation price | At the best (baseline); 1 to 5 ticks behind (H3); 1 to 10 bp deep | Behind by ticks is worse (−0.16 bp, H3 fails); 1 bp deep slightly better; deeper becomes a bet on a few fills |
| **Width** | How far apart are bid and ask? | One tick; fixed; scaled by recent volatility | Scaled by the volatility of the last 60 s (Avellaneda-Stoikov, H2) | +0.11 bp out of sample (H2 holds), mostly by trading less when the market moves |
| **Inventory** | How do we keep the position in check? | A hard limit; a lean of both quotes against the position; one position at a time (ping-pong); stops | Limit of 10 lots; lean (Avellaneda-Stoikov); ping-pong (H4); stops of 1 to 20 bp | Positions held beyond 10 s cost little, so inventory control matters little; stops add taker fees and do not pay |
| **When to quote** | When do we step aside? | Always; after a move on another venue; after a large move here; after our own fill; at certain times | Binance guard (H1); kill switch (10 October); pause after a fill; hour of the day, round times | Guard about 0; pause of 0.2 to 0.5 s about +0.04 bp; kill switch large in the crash; times of day too small to use |
| **Exit** | How is a position closed? | A resting order at the best; a target; a stop or time limit at market | All three, within ping-pong (H4) | Exits at market halve the loss before fees and lose most after fees |
| **Information** | What do the quotes react to? | Our own book; the trades; another venue; a forecast | The book every 100 ms; Binance's last trade | Binance warns too little, even with no delay (§6) |
| **Speed** | How fast do our orders arrive? | 5 to 100 ms in practice | 5, 10, 25, 50 ms | Faster orders made the baseline worse: it rejoins sooner into the same sweep |
| **Size and levels** | How much, at how many prices? | One lot at one level; a ladder of levels (Lecture 17's grid); size by queue | One lot, one level | Not tested |

<sub><b>How to read the table.</b> Each row is one decision a market maker has to make. "Options" lists the common answers; "Tested here" the ones run in this lecture; the last column the result before fees, in bp of the value traded, against the baseline (one lot at the best on both sides, re-posted at every book update), on the 24 out-of-sample days for H1 to H4 and on the sampled hours otherwise. H1 to H4 are the tests fixed in advance (§4); the rest are described, not tested.</sub>

Open-source frameworks supply the machinery for all of these choices, but not the settings. Hummingbot's grid executor, which Lecture 17 used, closes positions with a stop and a time limit at market; with a stop of 1 bp, inside a minute's noise of about 5 bp, three quarters of our ping-pong's positions ended on the stop and paid the taker fee (§3). Every number in a rule, a stop, a target, a pause, has to be set against the noise of the market at its horizon and against the fees, and its result shown over a range of settings rather than at one value.
