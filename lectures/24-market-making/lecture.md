# Lecture 24: Market Making on One Venue: What It Takes to Break Even

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 11, 2026 · Max Gnesi*

Lecture 23 showed whom a quote on Bybit's BTCUSDT perpetual meets: mostly ordinary flow, and now and then a trader who takes the quote just after Binance has moved. This lecture puts our own quotes into that market. A market maker posts a bid and an ask, earns the spread when both are filled, and pays when the price moves against what it has just bought or sold. The question is not whether a clever rule beats the market, but what it takes to break even, and what a profitable maker must have that a replay of public data cannot show. Every design runs in Lecture 21's replay of the exchange, with 50 ms between a decision and its arrival, on 20 September to 3 November 2025; the hypotheses were fixed before any result was computed, and every change is dated ([results/hypotheses.md](results/hypotheses.md)).

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
