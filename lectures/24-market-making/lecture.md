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

## 3. The designs

Every design starts from one **baseline**: a bid at the best bid and an ask at the best ask, 0.001 BTC each, re-posted whenever the best price moves, until the position reaches 10 lots on one side. Each design changes one choice of §2 and is compared with the baseline on the same hours. Four designs were fixed as tests before any result (H1 to H4, §4); the others were added after the tests, as the results raised new questions, and are described, not tested; each is dated in [results/hypotheses.md](results/hypotheses.md) before its run.

| Design | What it changes | Fixed |
|---|---|---|
| Binance guard (H1) | Withdraws the quote on the side Binance has moved against, for a gap of θ bp | Before the tests |
| Avellaneda-Stoikov (H2) | Quotes around the microprice, leaned by κ per lot of position, half-width c times the volatility of the last 60 s | Before the tests |
| One tick behind (H3) | Quotes k ticks behind the best | Before the tests |
| Ping-pong (H4) | One position at a time, closed by a resting order at the best, a target, or a target with a stop | Before the tests |
| Deeper quotes | 1 to 10 bp behind the best | After the tests |
| Stops | Close any lot at market once the mid is 5 to 20 bp against it | After the tests |
| Pause | No new quote on a side for 0.2 to 5 s after a fill there | After the tests |
| Speed | Orders arriving 5 to 50 ms after the decision | After the tests |
| Lean on Binance | The most that skipping fills with Binance against us could save | After the tests (diagnostic, on saved fills) |

The figure shows each lever across its range of settings, after fees, against the baseline on the same hours. A lever that helps should help over a range of settings and in both samples; one good setting is not enough (Lecture 7, §5).

![Every lever across its range](figures/24_s3_levers.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Each panel: the lever's setting (x); the design's result after fees, in bp of the value traded, less the baseline's on the same hours (y); above zero the lever helps. Scales differ by panel. <b>Blue:</b> in sample; <b>orange:</b> out of sample. <b>Solid:</b> the lever on the baseline; <b>dotted:</b> on Avellaneda-Stoikov, against Avellaneda-Stoikov without it, except in the second panel, where solid is κ = 5 and dotted κ = 0. <b>Third panel, diamonds:</b> ping-pong out of sample before fees. Panels 1 to 3: 6 in-sample and 6 out-of-sample days, four hours each; panels 4 to 7: 3 and 3 of those days. Panel 6: the baseline at each order latency less the baseline at 50 ms. Panel 7: the most that skipping fills with Binance more than 0.5 bp against us could have saved, per fill, by how long before the fill the quote could still be moved. Our calculation, Bybit BTCUSDT perpetual.</sub>

**Binance guard.** Withdrawing a quote when Binance has moved against it should spare the fills that follow a move there. It helps by less than a hundredth of a basis point at every threshold. Lecture 23 found the reason: after a Binance move of 2 bp, a Bybit taker order in its direction follows within 50 ms in 94% of cases, faster than our cancel arrives.

**Avellaneda-Stoikov.** The quotes sit around the microprice, lean against the position, and widen with recent volatility. Widening is what matters: the design trades a tenth as often as the baseline and stays out of the busiest moments. On the sampled hours c = 1 helps a little in both samples (+0.01 and +0.05 bp with κ = 5, +0.05 and +0.05 with κ = 0), and c = 2 is mixed (+0.06 in sample, −0.03 out of sample); on all 24 test days c = 2 is +0.11 bp (§4). The lean against the position matters little, because the position matters little (§1).

**Behind and deeper.** A quote one to five ticks behind the best earns nothing more, since five ticks are 0.05 bp, and is filled only when the price trades through it: it loses more than the baseline (H3, §4). A quote whole basis points deep does earn more spread, and the figure below shows what happens to it.

![Quoting deeper: more spread, taken straight back](figures/24_s3_depth.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Left: depth of the quote behind the best, bp (x); per fill, in bp of the value traded (y). Right: depth, bp, log scale, 0.01 standing for the baseline at the best (x); fills an hour, log scale (y). <b>Green:</b> the spread earned, the mid just before the fill less the fill price. <b>Orange:</b> the move of the mid against us in the first second. <b>Black:</b> fills an hour. <b>Dotted:</b> in sample; <b>solid:</b> out of sample. 3 in-sample and 3 out-of-sample days, four hours each. Our calculation, Bybit BTCUSDT perpetual.</sub>

The spread earned rises with depth, and the move against us rises almost as fast, because a deep quote is reached only by an order that sweeps the book, and such orders tend to know where the price is going. At 1 bp the two nearly cancel and the result is slightly better than the baseline in both samples (+0.30 and +0.09 bp), on a tenth of the fills. Beyond 2 bp fills fall to a few an hour, and the result is set by the positions held afterwards: whether the price came back after a sweep, which it did in sample and did not out of sample. That is a bet on a handful of events, not market making.

**Ping-pong.** One position at a time, closed before the next is opened. Closed by a resting order at the best, it does as the baseline does. Closed by a target 1 bp away, it holds positions that the price runs away from: about even with the baseline in sample, 1.4 bp worse out of sample. Closed by the same target with a stop 1 bp against or after 60 s, it halves the loss before fees (diamonds), because it no longer holds positions into moves; but the stop sits inside a minute's noise, about 5 bp, so three quarters of its positions end on the stop, 37% of its value pays the taker fee of 5.5 bp, and after fees it is 0.8 bp worse than the baseline in both samples. A stop pays only where the taker fee is less than about 1.2 bp above the maker fee; on Bybit's schedule the difference is 3 to 3.5 bp (§6).

**Stops with room for noise.** Set at 5 to 20 bp, beyond a minute's noise, a stop is hit rarely and does not pay on the baseline at any width. In the minute after a stop fires, the mid comes back about as often as it goes on (in 44 to 62% of cases, for every variant with more than 50 stops), so the stops catch random moves, not trends. On Avellaneda-Stoikov a 20 bp stop helps out of sample, almost all of it on one day, 21 October, when the design held a position into a move; it is insurance against a rare event, not a source of return. A stop at a fixed, predictable level can also be set off on purpose, which the replay cannot show.

**Pause after a fill.** A sweep that fills our quote cannot be cancelled away: by the time the trade is seen, the fill is done. What can be avoided is walking back into the same move. A pause of 0.2 to 0.5 s on the side just filled helps in both samples, by +0.02 to +0.05 bp: it skips the follow-up fills of a sweep. Longer pauses hurt, because 62% of the baseline's fills come within a second of the previous one on the same side, and most of them are the steady, harmless fills of a calm market.

**Speed.** Faster orders made the baseline worse: −0.13 bp at 5 ms against 50 ms, with two thirds more fills. A faster quote returns sooner to the new best price after a sweep and is filled again by the same move; in the replay it also returns on a book seen up to 100 ms earlier. Speed is worth something only together with something that sees the move coming. Binance does not: even with no delay at all, skipping the fills with Binance against us would have saved at most 0.04 bp per fill.

**The time of day.** Neither the hour nor the second of the minute repeats well enough to use: the first three seconds after each minute are 0.15 bp worse per fill, but skipping them gains 0.01 bp, and the hourly profile on the first twelve test days does not predict the last twelve (rank correlation 0.32, p = 0.12). What matters is how volatile the hour is, and that is known only once it is over.

> **How we ran it.** All designs run in Lecture 21's replay: Bybit's book every 100 ms and trades to the millisecond, queue rule Q2 with a = 1, orders of 0.001 BTC, post-only, 50 ms from decision to arrival, and a cancelled order live for 50 ms after the cancel. Days are run in half-hour windows; a design's position carries over between consecutive windows and starts flat after a gap. To keep the runs short, settings were chosen and compared on **sampled hours**: four one-hour windows a day (02:00, 08:00, 14:00, 20:00 UTC) on 6 in-sample and 6 out-of-sample days, three of each for the designs added after the tests; the tests of §4 run the chosen settings on all 24 out-of-sample days. Two errors were found and corrected after the tests, both dated: open positions at the end of a sampled hour were first valued at the day's last price (corrected 10 November; H2's choice changed), and a ping-pong lot closed by a stop could be closed again by its cancelled resting order (corrected 11 November; H4 redone). The position limit of 10 lots can be exceeded by one, when a cancelled order is filled within its 50 ms.

## 4. Tests

Four designs were fixed as tests on 9 November, before any result: the settings were chosen on the sampled in-sample hours, and each design was then run on all 24 out-of-sample days, 11 October to 3 November 2025, whole days. The measure is the result before fees in bp of the value traded, all fills of the 24 days pooled, against the baseline on the same days. For a design that only rests its orders, this number is also its **break-even maker fee**: the fee at which it would neither gain nor lose. The band is a bootstrap over days (2,000 draws), the p-value one-sided, and the four p-values are corrected together (Benjamini-Hochberg at 5%).

![The four tests, day by day](figures/24_s4_tests.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Result before fees less the baseline's, in bp of the value traded (x); one row per tested design (y). <b>Dots:</b> single days, one per out-of-sample day. <b>Diamond and bar:</b> the difference with all 24 days pooled, and its 90% bootstrap band over days. Right of the grey line the design beats the baseline. Our calculation, Bybit BTCUSDT perpetual.</sub>

| Question | Design | Better than the baseline by, bp (90% band) | Days better | p | After Benjamini-Hochberg | Result after fees, USDT a day | Fills an hour |
|---|---|---|---|---|---|---|---|
| — | Baseline: at the best | — (−0.86) | — | — | — | −2,093 | 2,764 |
| Does withdrawing quotes after a Binance move help? (H1) | Binance guard, 2 bp | +0.004 (0.003 to 0.006) | 24 of 24 | < 0.001 | Holds, but tiny | −2,074 | 2,743 |
| Does widening with volatility and leaning against the position help? (H2) | Avellaneda-Stoikov, κ = 5, c = 2 | +0.11 (0.04 to 0.17) | 16 of 24 | 0.004 | Holds | −182 | 250 |
| Does waiting one tick behind the best help? (H3) | One tick behind | −0.16 (−0.17 to −0.15) | 0 of 24 | 1.00 | Fails | −1,766 | 2,208 |
| Does one position at a time, closed at a target or a stop, help? (H4) | Ping-pong, target and stop | +0.45 (0.43 to 0.46) | 24 of 24 | < 0.001 | Holds before fees | −2,178 | 2,222 |

<sub><b>How to read the table.</b> "Better than the baseline by" is the design's result before fees less the baseline's, in bp of the value traded, all 24 days pooled; the baseline's own result is in brackets. "Days better" counts the days on which the design beat the baseline. "p" is the one-sided bootstrap p-value; "After Benjamini-Hochberg" says whether the result survives the correction for testing four designs. "Result after fees" charges 2 bp on resting fills and 5.5 bp on market orders, in USDT a day at 0.001 BTC an order. H2's setting was chosen again after the scoring error of 10 November; the setting chosen before it, c = 1, is +0.085 bp (0.06 to 0.11), 18 days of 24, reported, not tested.</sub>

Three of the four tests hold, and none of them changes the picture of §1. The guard holds on every day by four thousandths of a basis point: real, and of no use. Avellaneda-Stoikov holds by a tenth of a basis point, with 8 days of 24 worse than the baseline; most of its advantage after fees comes from trading a tenth as much, so it loses 182 USDT a day where the baseline loses 2,093. One tick behind fails on every day. Ping-pong holds before fees by almost half a basis point on every day, and after fees loses more than the baseline, because 37% of its value is closed at the taker fee. A test before fees answers the question it was asked; for a design that pays taker fees, it is the wrong question.

**What drove the differences.** Per resting fill, no design loses much less than the baseline in the first second; the differences come from which fills a design gets, and from what it trades instead (results/drivers.json, 24 out-of-sample days):

| Design | Follow-up fills: within 1 s of the last fill on the same side | Move after 1 s: first fills | Move after 1 s: follow-up fills | Stops at market: share of fills, move after 1 s |
|---|---|---|---|---|
| Baseline | 58% | −0.63 bp | −0.87 bp | — |
| Binance guard | 58% | −0.63 bp | −0.87 bp | — |
| Avellaneda-Stoikov | 25% | −0.60 bp | −0.92 bp | — |
| One tick behind | 59% | −0.90 bp | −0.96 bp | — |
| Ping-pong | 55% | −0.63 bp | −0.87 bp | 37%, +0.26 bp |

<sub><b>How to read the table.</b> Each fill's move of the mid one second after it, from the fill price, signed for our side, in bp; below zero the price moved against us. A follow-up fill comes within one second of the design's previous fill on the same side, usually in the same sweep. The middle columns are resting fills only; the last column is ping-pong's stops, sent at market.</sub>

Avellaneda-Stoikov's gain is fewer follow-up fills: it widens when the market moves, so a quarter of its fills are follow-ups against 58% for the baseline, the mechanism the pause of §3 uses directly. One tick behind loses on its first fills too, because a quote behind the best is reached only when the price is already going through it. Ping-pong's resting fills lose exactly what the baseline's do; its gain before fees comes from its stops, which are market orders sent while the price is moving and so gain about a quarter of a basis point in the next second, on 37% of its fills. Before fees that averages out as an improvement; after fees each stop pays 5.5 bp instead of 2 bp, and the improvement is gone several times over.

**Break-even.** A design that only rests breaks even at a maker fee equal to its result before fees with the sign turned: the baseline at a rebate of 0.86 bp, Avellaneda-Stoikov at 0.75 bp, one tick behind at 1.02 bp. Ping-pong at the taker fee of 5.5 bp would need a maker rebate of 3.8 bp. §6 sets these against what Bybit pays.

**Robustness.** The ranking of the settings on the sampled in-sample hours carries over to the sampled out-of-sample hours: across all 85 variants the rank correlation is 0.63. The chosen ping-pong is second of its 56 variants out of sample, and every variant with a target and a stop lies within 0.06 bp of it; Avellaneda-Stoikov's 20 settings span −0.80 to −1.18 bp out of sample, so its gain depends on the setting more than the others'. The designs added after the tests (§3) are not part of this correction, and their results are descriptions of our sample.

## 5. 10 October 2025: a crash as a case study

On the evening of 10 October 2025 bitcoin fell about 13% in half an hour on Bybit's perpetual, from 117,016 USDT at 20:30 UTC to 101,344 at the low, the largest fall in our data (Lectures 19 and 21 describe the book and the replay through it). Which way of quoting does best through such an evening, and where does each lose? One evening is one case: the results are described, not tested, and a different crash may favour a different rule. The designs, four expectations and the phases of the crash were fixed before the run ([results/hypotheses.md](results/hypotheses.md)). Every design starts flat at 20:30 and runs to 23:00.

The phases come from the mid alone: **before**, until the first move of 10 bp within a second (20:44:12); the **fall**, until 2.5 minutes before the low (21:17:40); the **bottom**, 2.5 minutes either side of the low; the **rebound**, until the last new high before a 5-minute pause; and **after**, to 23:00. By the rule as written the rebound lasts 52 seconds, because the price paused soon after the low; most of the recovery falls in "after".

![10 October 2025: what the crash did to five quoting rules](figures/24_s5_crash.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> All panels: time, UTC (x). Top: Bybit's mid, USDT (y); shaded, the fall and the bottom. Middle: each rule's result so far, before fees, USDT (y), the cash from its fills plus its position at the mid. Bottom: the rule's fills per minute (y). <b>Lines:</b> the baseline, the baseline with the kill switch (no new quotes for 30 s after the mid moves 10 bp within 1 s), the Binance guard at 1 bp, ping-pong with target and stop, and ping-pong with the kill switch. Replay with 50 ms latency, 0.001 BTC orders, at most 10 lots either way. Our calculation, Bybit BTCUSDT perpetual.</sub>

The baseline lost steadily through the fall and again at the bottom, quoting into every wave and filled at a rate of hundreds a minute. The kill switch stopped it quoting for most of the half hour from about 21:13 to 21:40, when the moves came fastest, and kept most of its result. The guard on Binance lost through the fall, like the baseline, and gained at the bottom. Ping-pong's line before fees looks flat; its losses are in its fees, which the next figure shows.

![10 October 2025: where each design's money went](figures/24_s5_split.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> USDT over the two and a half hours (x); one bar per design, ordered by the result after fees (y). Each bar is split into: <b>blue</b>, what the fills kept after 10 s, the spread earned less the move against them in that time; <b>green</b>, the gain or loss on positions held beyond 10 s; <b>grey</b>, fees, 2 bp on resting fills and 5.5 bp on market orders. <b>Diamond:</b> the result after fees. 25 designs: the five tested ones with and without the kill switch, and the variants fixed for the case study. Our calculation, Bybit BTCUSDT perpetual.</sub>

Three things stand out. First, the loss before fees came from the fills, not from the positions: the baseline lost 1,117 USDT on what its fills kept after 10 s and 75 USDT on positions held longer. Our limit of 10 lots, 0.01 BTC, capped the loss a position could cause; a maker carrying real size into a 13% fall would have lost on inventory far more than on its fills. Second, what helped was not being there: the kill switch, and Avellaneda-Stoikov with c = 2, which widened with volatility so far that it traded 674 times in the evening against the baseline's 60,000, and ended 45.5 USDT up after fees, the only design with a gain. Third, ping-pong's stops kept its position at three lots or fewer, and turned its loss into fees: 2,508 USDT of fees against 659 USDT lost before fees.

| Expectation, written before the run | Result |
|---|---|
| 1. The kill switch reduces the baseline's loss at every setting, and longer pauses help more | Holds. At every trigger of 5, 10 and 20 bp the loss after fees falls as the pause grows from 10 to 60 s, from −2,538 USDT without it to between −90 and −1,718 |
| 2. The guard helps more in the crash than on normal days, and more at 1 bp than at 5 bp | Holds. −798 USDT at 1 bp, −1,142 at 2 bp, −1,680 at 5 bp, against −2,538; on normal days the guard changes almost nothing (§4) |
| 3. Widening with volatility helps Avellaneda-Stoikov, but less than the kill switch | Half holds. Widening helps by far the most: −2,616 USDT at c = 0, −67 at c = 1, +45.5 at c = 2, better than every kill switch; the kill switch added to it made it worse (−32) |
| 4. Ping-pong's stops keep its position small but turn its loss into fees; the exit without a stop loses most | Mixed. Positions stayed at three lots or fewer, and fees were 79% of its loss; but the exit without a stop lost only 7.8 USDT, because after its first fills it held a position and stopped trading |

<sub><b>How to read the table.</b> Each expectation was written before the run; the result is in USDT after fees over 20:30 to 23:00, at 0.001 BTC an order.</sub>

**What the replay cannot show.** The replay assumes that our orders and our data arrived as on a normal day. On the evening itself, the exchange's interface may have been slow, rate-limited or refusing orders; positions may have been closed by auto-deleveraging; and makers may have withdrawn in ways the book does not reveal (Lecture 21, §5). A rule that wins here by stepping aside would also have needed its cancels to get through.
