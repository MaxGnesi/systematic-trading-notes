# Lecture 24: hypotheses, fixed before the results

Fixed on 2026-11-09, before any result of the designs below was computed. Every later change is dated here before out-of-sample data are used for it.

**The question.** On our sample, what does it take for a market maker on Bybit's BTCUSDT perpetual to break even: which choices of design, at which fee and at which speed? The answer is a result on our sample and our replay, for the designs below. It cannot rule out that real makers earn in ways the replay does not capture (queue priority held for long, speed below 10 ms, fee arrangements that are not public, hedging elsewhere, better forecasts, netting of many positions); these are stated as open questions, and hedging on Binance is taken up in Lecture 25.

**What is already known.** Lecture 21 (§4.4) ran the baseline below, the instant quoter, on eight out-of-sample days (11-15, 22 and 28 October, 1 November): −0.86 bp per fill after 10 s before the fee, 4,000 fills an hour, 65% of its fills within a second of the previous one on the same side. Lecture 23 (§5) found, out of sample, that orders sent just after a Binance move carry 31% of the makers' adverse move, and that after a Binance move of 2 bp a Bybit taker order in its direction follows within 50 ms in 94% of cases. No result of any other design has been computed.

## Shared definitions

- **Data and replay.** Bybit BTCUSDT perpetual, 20 September - 3 November 2025, replayed with Lecture 21's machinery: the order joins at its price when it arrives; fills under the queue rule Q2 with a = 1 (main) and a = infinity (reported); latency L = 50 ms (main), 10 and 100 ms reported; decisions at every book update, using only data published up to then. Binance aggTrades of Lecture 20 for the Binance price.
- **Samples.** Every parameter is chosen in sample, 20 September - 9 October. Tests out of sample, 11 October - 3 November (24 days). 10 October is reported apart (§5). The eight days of Lecture 21 are among the out-of-sample days; the baseline's result on them is known, the other designs' is not.
- **Size.** 0.001 BTC per order, the minimum. Position limit 0.01 BTC either way for every design (a side is switched off at the limit). Larger sizes reported for the design that does best, as a question of capacity.
- **Measures, per design and day.** Fills an hour; markout per fill at 1, 10 and 60 s before the fee (mid after less fill price, signed for our side, bp); the **result before the fee**: cash from all fills plus the position valued at the mid at the end of the day, in bp of the value traded, which is the **break-even maker fee**; the result after Bybit's standard maker fee (2 bp, Lecture 21; the published fee table is checked at source before the lecture quotes other tiers), in USDT a day; the largest position; the part of the result from the position carried (from 10 s after each fill to the end of the day).
- **Tests.** Each design against the baseline on the same days, difference of the result before the fee (bp of value traded, all fills of the 24 days pooled), bootstrap over days (2,000), one-sided. Benjamini-Hochberg at 5% over the four p-values of H1 to H4. Every design is also shown on a grid of its parameters in sample, so that a result that holds only at one setting shows.

## The designs

- **Baseline (Lecture 21's instant quoter).** A bid at the best bid and an ask at the best ask, kept while the best price on its side is its price, otherwise cancelled and re-posted; re-posted after a fill at the next book update.
- **H1 (the Binance guard: do not post into an open gap).** The gap is Binance's last trade price less Bybit's mid, in bp of the mid, known at the decision. The guard holds no bid while the gap is −θ or below (Binance has fallen; a bid would be stale) and no ask while it is +θ or above; a quote already resting on that side is cancelled. θ = 2 bp (Lecture 23's move), with 1, 3 and 5 bp reported. Otherwise as the baseline. *Hypothesis:* the result before the fee is higher than the baseline's, out of sample. Reason: Lecture 23 found that a stale quote is rarely cancelled in time; a quote never posted into the gap need not be. Reported: fills lost, and the markout of the fills that remain.
- **H2 (position control, Avellaneda-Stoikov with extras).** Quotes at r ± h, rounded away from r to the tick and never crossing the best price on the other side. Reference price r = microprice (Lecture 19) − κ × position; half-spread h = max(one tick, c × σ), σ the standard deviation of 1-s changes of the mid over the last 60 s. κ (ticks per 0.001 BTC of position) and c are chosen in sample on a grid (κ in {0, 0.5, 1, 2, 5}, c in {0, 0.5, 1, 2}), the choice and the grid reported; the perpetual has no end date, so the horizon term of the original model is replaced by the fixed κ (Avellaneda and Stoikov, 2008; the bounded-inventory version of Guéant, Lehalle and Fernandez-Tapia, 2013, to be checked at source). *Hypothesis:* the result before the fee is higher than the baseline's, out of sample. Reported: the part from the position carried, and the largest position.
- **H3 (behind the best).** Bid and ask k ticks behind the best price on their side (the bid k ticks below the best bid), kept while that holds, otherwise moved; k = 1 (main), with 2, 5 and 11 (about 1 bp) reported. *Hypothesis:* the result before the fee is higher than the baseline's, out of sample. Reason: a quote behind the best is filled only when the price has come through the best, and should be filled less often by orders that are already late.
- **H4 (ping-pong: one position at a time).** Wording of 2026-11-03 (Lecture 21's file, then parked for this lecture), unchanged except for the days, which here are the 24 out-of-sample days with parameters fixed in sample. With no position, a bid at the best bid and an ask at the best ask, re-posted at every book update; after one side is filled, that side is switched off and only a closing order works until it is filled, then both sides quote again. Closing order: (a) at the best price on its side, re-posted at every book update (main); (b) a target k ticks from the entry price, k in {1, 11}, left in place until filled (reported). A closing order whose price can trade at once on arrival is filled there as a taker. *Hypothesis:* the result before the fee of (a) is higher than the baseline's, out of sample. Reported: round trips an hour; gain per round trip before the fee; time a position is held; the worst move against it while held; the position open at the end of each day.

## Reported, not tested

- **Stepping back on Lecture 20's signals.** Wording of 2026-11-03, unchanged: for every fill of the baseline and of ping-pong, three signals measured up to the fill time less L: speed (taker trades on Bybit in the second before), flow against us (taker volume in the 10 s before, against our side), Binance's lead (the move of Binance's last price in the 100 ms before, signed against our order). The 10-s markout by fifth of each signal (fifths over all fills), and the share of fills and of the loss in the top fifth. If a signal separates the fills clearly, a quoter that cancels a side while that side's signal is in the top fifth (thresholds in sample) is run on the same days.
- **The designs combined** (guard with position control, guard with ping-pong): reported in sample and out of sample, not tested, since the combination is chosen after seeing the parts.
- **10 October.** Every design through 20:50 - 22:50 UTC, with and without a kill switch (no quotes for 30 s after the mid moves 10 bp or more within 1 s), as in Lecture 21 (§5).
- **What it takes.** For each design, the break-even maker fee, and the result after the fee for the fee tiers of Bybit's published table.
- **Tactical hours** (quote only in hours that paid before, walk-forward): an exercise, since Lecture 23 found that the hour of the day says little out of sample.

## Changed on 2026-11-09, before any result: ping-pong as a family (H4)

**Why.** Ping-pong is a family of rules, not one rule; a single version would test our choice of implementation rather than the idea. H4 is restructured as a grid fixed here, one variant chosen in sample, one test out of sample.

- **Entry**, when a side is on: at the best price, or 1 tick behind it.
- **Exit**, one closing order per fill: (a) at the best price on its side, re-posted at every book update; (b) a target 1 tick from the entry price, left resting; (b') the same at 11 ticks (about 1 bp); (c) a target at 11 ticks with a stop: closed as a taker when the price is 11 ticks against the entry, or after 60 s. A closing order whose price can trade at once on arrival is filled there as a taker.
- **Switch-off**, how many fills on one side before that side stops quoting: n in {1, 2, 3, 5} open lots on that side. n = 1 is pure ping-pong; larger n is Lecture 17's paired grid at the best price. The side quotes again as soon as fewer than n of its lots are open.
- **Re-arm** at once (main); a cooldown of 1 s after each fill is reported for the chosen variant.

That is 2 × 4 × 4 = 32 variants. **The chosen variant** is the one with the highest result before the fee on the in-sample days (20 September - 9 October), L = 50 ms, Q2 with a = 1. **H4 (replaces the hypothesis above):** the chosen variant's result before the fee is higher than the baseline's, out of sample; one p-value, in the same correction as H1 to H3. **Reported:** all 32 variants out of sample, so that a result holding only at one implementation shows; the guard of H1 on entry only and on entry and exit, for the chosen variant; round trips an hour, gain per round trip, time held, worst move while held, positions open at the end of each day. The earlier main variant, entry at the best, exit (a), n = 1, is one of the 32.

*Changed again on 2026-11-09, before any result.* The switch-off can also be set by the price, not the count. **Switch-off by excursion:** a side stops quoting while the mid is x bp or more against the average entry price of that side's open lots (below it for open buys), x in {2, 5, 10} bp, and quotes again once the mid is back within x; the count is then limited only by the position limit (10 lots). The switch-off grid is now n in {1, 2, 3, 5} fills or x in {2, 5, 10} bp: seven rules, so 2 × 4 × 7 = 56 variants. The choice in sample, the single test out of sample and the reporting of all variants are as above.

## Changed on 2026-11-09, while building the engine, before any out-of-sample data was used

Found on one in-sample hour (1 October, 10:00 - 11:00 UTC) and in the units, before any design was run beyond it:

- **Ticks and basis points.** One tick is 0.1 USDT, about 0.009 bp at 110,000 USDT, so 1 bp is about 110 ticks, not 11 as the wording of 2026-11-03 said. Every "11 ticks (about 1 bp)" above means 1 bp: 110 ticks (the day's ticks per bp are computed from its middle price and rounded to 110 for the grids).
- **The Binance gap drifts.** Binance's last price less Bybit's mid moves slowly between about −1.5 and +1.4 bp from hour to hour on 1 October (the two perpetuals' prices differ by a varying amount), so the raw gap mostly measures that difference, not a stale quote. H1's gap is therefore taken net of its average over the 60 whole seconds before the decision; a jump on Binance shows in full, the slow difference does not.
- **H2's half-spread.** h = max(half a tick, c × σ), not one tick. *Corrected the same day, on the in-sample timing day (1 October):* even with κ = 0 and c = 0 the design is not the baseline, because the quotes are rounded away from the microprice: when the microprice leans towards one side, the other side's quote steps one tick back. The grid's corner κ = 0, c = 0 is therefore the baseline plus the microprice's lean, and the baseline stays the comparison.
- **How the engine decides.** Every design, the baseline included, prices its orders with the book known at the decision, not at the arrival L later (Lecture 21's quoter took the best price standing at arrival); maker orders are post-only (rejected if they would trade on arrival); with the position limit, a side stops quoting at 10 lots. The baseline is run again in this engine, so all designs are compared on the same rules; its result will differ from Lecture 21's.

## Changed on 2026-11-09, before any run beyond the timing day: shorter runs

All 85 variants take about 28 minutes per day of data, so the whole sample would take about a day of computing. The runs are cut, fixed here before they start:

- **Choice in sample** (H2's κ and c, H4's variant): all variants on 6 in-sample days, 21, 24, 27 and 30 September, 3 and 6 October, each in four one-hour windows, 02:00, 08:00, 14:00 and 20:00 UTC; each window starts flat. The choice is the highest result before the fee over these 24 hours.
- **The tests out of sample** stay as fixed: the baseline, the guard at 2 bp, 1 tick behind, the chosen H2 and the chosen H4, on all 24 out-of-sample days, whole days.
- **All variants out of sample** (the robustness charts): 6 out-of-sample days, 13, 17, 21, 25 and 29 October and 2 November, in the same four windows.
- 1 October, run in full to time the engine, is not used for the choice.

## The choice in sample, made on 2026-11-10, before any out-of-sample run

On the 24 sampled in-sample hours (results/choice.json): **H2** κ = 5, c = 1 (−0.80 bp of the value traded before the fee, against −0.82 for the baseline; the grid spans −0.80 to −1.0); **H4** entry at the best, a target 1 bp from the entry with a stop 1 bp against or after 60 s, switch-off after 2 fills on a side (−0.33 bp, 37% of its fills taker exits; the 56 variants span −0.33 to −2.6, median −0.90). These two, with the baseline, the guard at 2 bp and 1 tick behind, are the five designs run on the 24 out-of-sample days.

## Corrected on 2026-11-10, after the out-of-sample tests: the scoring of the sampled hours

**The error.** The engine starts each block of sampled windows flat, but the score valued the position left open at the end of a block at the last mid of the day, as if it had been held until midnight. Whole days (the out-of-sample tests) are one block and are not affected; the sampled hours, and so the choice in sample, are. Found after the five designs had been run on the 24 out-of-sample days and all variants on the 6 sampled out-of-sample days, when a few designs with few fills showed largest positions of up to 40 lots against a limit of 10.

**The fix.** The position open at the end of each block is valued at the mid at that block's end (l24_engine.score, l24_engine.blocks). The saved fills were scored again; nothing was replayed. A whole day scored again gives the same numbers to the last digit.

**The choice under the fixed rule** (highest result before the fee over the 24 sampled in-sample hours; results/choice.json): **H2** κ = 5, c = 2 (−0.750 bp, against −0.799 for κ = 5, c = 1 and −0.812 for the baseline); **H4** entry at the best, target 1 bp with a stop 1 bp against or after 60 s, switch-off after **1** fill on a side (−0.3482 bp, against −0.3485 for 2 fills: a tie in practice). The rule is applied as written, although the sampled out-of-sample hours had been seen.

**What is tested.** The rule decides the variants, so H2 and H4 are tested on the corrected choices, run on the 24 out-of-sample days as the other three designs were. The tests already run on κ = 5, c = 1 and on the 2-fill switch-off are kept and reported as the choice made under the error.

## Corrected on 2026-11-11, after the out-of-sample tests and 10 October: the ledger of closing orders (H4 only)

**The error.** When a ping-pong stop closed a lot as a taker, the maker order that was closing the same lot was cancelled, but stays live for the latency (50 ms) and could still be filled; the fill entered the cash but not the ledger of open lots, which had already dropped the lot. The design then took itself to be flat while it was not, and went on entering. Found on 10 October, where ping-pong reached 40 lots against a limit of 10; on the 24 out-of-sample days 53% of the chosen variant's fills came while it held more than one lot (up to 20). The double fill itself is real (a cost of latency); only the ledger was wrong.

**The fix.** A closing fill for a lot already closed is an ordinary fill: netted against an open lot, else a new lot (l24_engine.State.add); stops and taker closes carry their fill price into the ledger. Only designs with closing orders are affected: all ping-pong variants. The baseline, the guard, behind the best and Avellaneda-Stoikov post entries only; their results, out of sample and on 10 October, stand.

**What is redone, in the order fixed on 2026-11-09.** The 56 ping-pong variants on the 24 sampled in-sample hours, and the choice by the same rule; the chosen variant on the 24 out-of-sample days (the H4 test, in the same Benjamini-Hochberg correction); the 56 variants on the sampled out-of-sample hours; the chosen variant on 10 October with and without the kill switch. Every H4 number computed before this date is void.

**The H4 choice under the fixed ledger, made on 2026-11-11 before the out-of-sample rerun** (results/sample_days_ledger): entry at the best, target 1 bp with a stop 1 bp against or after 60 s, switch-off after **2** fills on a side, pp_e0_c110_n2 (−0.348 bp before the fee over the 24 sampled in-sample hours, 37% of fills taker exits; switch-off after 1 fill −0.350, a tie in practice). The 56 variants span −1.06 to −0.35 bp, median −0.80; the target-plus-stop exit is best at both entries.

## Added on 2026-11-11, before the run: 10 October as a case study

10 October is one stretch of one day: a case study, described, not tested (no p-values, no correction). The question: which market-making design does better through the crash, and where does each lose its money? Window and engine as for the tested designs (20:30 - 23:00 UTC, the half-hour windows holding 20:50 - 22:50, flat at 20:30; L = 50 ms, Q2 with a = 1; the fixed ledger).

**Designs** (beyond the ten already run: the five tested designs with and without the kill switch):
- Kill switch on the baseline: trigger x in {5, 10, 20} bp within 1 s, off for {10, 30, 60} s (the 10 bp / 30 s setting already run): 8 more.
- Binance guard θ in {1, 5} bp (2 bp already run).
- Avellaneda-Stoikov κ = 5, c in {0, 1} (c = 2 already run): with and without the spread widening with σ.
- Ping-pong: exit at the best (a), switch-off after 2 fills; target 1 bp without a stop, after 2 fills; the chosen exit with switch-off after 1 fill.

**Expectations, written before the run:**
1. The kill switch reduces the baseline's loss at every setting; longer off-times help more, since the crash came in waves.
2. The guard helps more in the crash than on normal days, and more at θ = 1 than at 5 bp, since Binance led the moves.
3. Widening with σ helps Avellaneda-Stoikov, but less than the kill switch, since σ over the last 60 s lags the fall.
4. Ping-pong's stops keep its position small, but turn part of its loss into taker fees and stop slippage; the exit without a stop loses most, by holding positions into the fall.

**Reported for each design:** the result before and after fees; the split of the result into the part picked off (markout after 10 s), the part from positions held beyond 10 s, and fees; the same by phase of the crash. Phases from the mid alone, fixed before any design's result is looked at: before (20:30 to the first move of 10 bp within 1 s), the fall (to the low), the bottom (5 minutes around the low), the rebound (to the last new high before 5 minutes without one), after (to 23:00).

**What the replay cannot show:** delays and rate limits of the exchange's interface, auto-deleveraging, and makers withdrawing in ways the book does not reveal; the replay assumes our orders and data arrived as on a normal day.

## Added on 2026-11-11, before any hourly result was computed: the hour of the day (described, not tested)

The question (asked after the tests): does a market maker do better at some hours of the day, and if so, is it the hour or the volatility of the hour? Lecture 23 (§4, H13) found that hourly profiles of the taker styles did not repeat out of sample, and that volatility, not the time of day, sets the mix; the expectation here is the same. Our in-sample runs cover only four sampled hours a day, so no profile can be fixed in sample; this is a description on the 24 out-of-sample days, outside the Benjamini-Hochberg family.

- **Data.** The saved fills of the five tested designs on the 24 out-of-sample days (no new replay).
- **Measure, per design, day and hour (UTC).** The result before the fee: cash from the hour's fills plus the position valued at the mid at the hour's end, less the position at its start valued at the mid then, in bp of the value traded in the hour; the value traded; the hour's volatility, the square root of the sum of squared 1-minute changes of the log mid (as Lecture 23).
- **Does the profile repeat?** The rank correlation between the baseline's 24-hour profile on the first 12 days and on the last 12 days.
- **Hour or volatility?** The result by third of the hour's volatility, and within each hour of the day the difference between the most and least volatile third of its days.
- **Expectation.** The profile does not repeat (rank correlation not clearly above zero); volatile hours lose more per value traded than calm ones, at every hour of the day.

## Added on 2026-11-11, after the out-of-sample tests: a wider stop for ping-pong (described, not tested)

**Why.** Compared after fees (results/after_fees.json), the chosen ping-pong (target 1 bp, stop 1 bp or 60 s) closes most lots on its stop, as a taker: 37% of its value pays 5.5 bp, and after fees it loses 3.70 bp of the value traded on the sampled out-of-sample hours, against 2.86 bp for the exit at the best price. The stop and time limit follow Hummingbot's grid executor (Lecture 17), which closes with market orders. A wider stop is hit less often, so fewer lots pay the taker fee, but each of those loses more.

**Variants.** Target 1 bp (110 ticks); stop m in {1, 2, 3, 5, 10} bp against the entry; time limit T in {60 s, 300 s, none}; entry at the best, switch-off after 2 fills on a side: 14 new variants, plus H4's chosen one (1 bp, 60 s). Same engine, latency and sampled hours as the other 85 variants (6 in-sample and 6 out-of-sample days, four hours each), so all are compared on the same hours.

**Measures.** Before and after fees (2 bp maker, 5.5 bp taker), in bp of the value traded; the share of value through the stop; fills an hour; in sample and out of sample separately. **Expectation:** after fees, a wider stop does better up to a point, because the taker share falls; without a time limit, positions are held into moves and the result before the fee falls. No test: this grid is added after the out-of-sample results, so it is reported as a description, and the H4 test stays as run.

**Replaced the same day, before any run of it finished.** A stop of 1 bp sits inside one minute's noise (about 5 bp on the test days), so it is hit by noise, not by trends; a stop should leave room for noise and fire on a trend, and the question applies to every design, not only ping-pong. A stop at a fixed, predictable level can also be triggered on purpose (stop hunting), which the replay cannot show, since nobody in it reacts to our orders. The grid above is not run; instead, a stop on every open lot, as a wrapper on three designs (the baseline; Avellaneda-Stoikov κ = 5, c = 2; ping-pong with the exit at the best, switch-off after 2 fills), no time limit:
- **Width:** 5, 10 or 20 bp against the entry (fixed), or 2 or 3 times the 1-minute volatility of the hour before the entry (scaled, about 10 and 15 bp on a typical hour).
- **Trigger:** on a touch of the level by the mid, or only after the mid has stayed beyond it for 5 s (harder to set off with a brief spike).
That is 3 × 5 × 2 = 30 variants on the same sampled hours, compared after fees with the same designs without a stop. **What we look for:** a region of widths that helps on both the in-sample and the out-of-sample hours, not one best cell. **Mechanism:** the share of lots stopped; the loss per stopped lot; and what the mid does in the minute after a stop: if it keeps going, the stop caught a trend; if it comes back, the stop was set off by noise (or a hunt).
