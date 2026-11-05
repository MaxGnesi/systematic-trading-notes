# Lecture 22: hypotheses, fixed before the results

H1-H15 fixed 2026-11-05, after review, before any of their results were computed.

## The plan of the lecture

The question: what if the market responds to our order? Lecture 21 replayed the record as if our orders were invisible, and flagged its resting results from 0.1 BTC up. This lecture keeps the recorded market as the background and adds the measured reaction on top, one layer at a time, then tests whether the result predicts what real large orders did. It is a **hybrid replay**, not a simulated market: a simulator's background has to generate everything itself, including patterns we may not know to put in.

1. **The key chart.** One real market order of about 5 BTC beside a moment that had none, where the same order is injected: the book and the mid as the plain replay reports them, as the hybrid replay reports them, and what happened after the real order. Message: a plain replay lets the price forget our order at once, and restores what we took.
2. **The pieces, one card each on invented data:** depletion (what we took is gone); refill (how it comes back); impact that fades; triggered trading; the reaction to resting size. Then **who gets simulated**, a card of its own: the traders a simulated market is built from (noise, value, momentum, market maker, high-frequency; snipers and scalpers), how each one's rule is written, whether the type has ever been measured, and what our data can show of it. Then the families of models side by side: plain replay, hybrid replay, event propagators, queue-reactive and agent-based simulation, generative models, and where each is used.
3. **The layers on our data:** each measured on real orders in sample, by size and by size relative to the queue.
4. **Does the hybrid replay tell the truth?** H1 to H9.
5. **How to read a market.** The method, built on H10 to H19: what is at work, in what shares, at what times and levels, does one style set off another, and is a reading worth anything?
6. **10 October.** Do layers calibrated on calm days hold in the cascade, and did the mix of styles change in it?
7. **Summary, exercises and reading.** What the footprint does to Lecture 21's flag; what remains for live orders.

## Literature read for the design

Notes with read status: session notes, `l22_literature_notes.md`; every number quoted in the lecture is to be checked against the source first.

- **Has this been done?** We found no paper that puts calibrated depletion, refill, fading impact, triggers and resting-size reaction on a recorded book. Nearest: Karpe et al. (2020, arXiv 2006.05574), replay plus reactive agents, no impact validation; Lu and Abergel (2018, arXiv 1806.05101), replay plus fictitious orders, passive impact left out; Noble, Rosenbaum and Souilmi (2026, arXiv 2603.24137), a fading-impact layer on a queue-reactive simulator.
- **How to validate.** Mostly impact shape against published values. The template used here is Linna et al. (2026, arXiv 2609.16930): injected scenarios against naturally occurring matched events, since agreement with a simulator shows only "consistency with their encoded dynamics".
- **Reaction layers can be exploited.** Coletta et al. (2023, arXiv 2306.12806): in a generative simulator a large bid with a small ask, one tick off the touch, earns a round-trip profit by pushing the imbalance. Hence H8.
- **Replay already has an impact, of a wrong kind.** Coletta et al. (2023) and Balch et al. (2019, arXiv 1906.12010): levels are not restored, then the record pulls the mid back.
- **Scale.** Square root over about two decades, close to linear at the smallest participation (Bucci et al., 2019, arXiv 1811.05230; Zarinelli et al., 2015). On bitcoin, δ about 0.5 (Donier and Bonart, 2015). A static book overstates impact four times (Weber and Rosenow, 2005).
- **Limits of our data.** Event propagators (Eisler et al., 2012; Taranto et al., 2018) need signs and types of single events; a 100 ms book merges them, so they are not estimated here. Taranto et al. state that such models do not react to past events, so they could not supply a reaction layer in any case.
- **Who gets simulated.** Simulators build from zero-intelligence or noise traders, value traders, momentum traders, market makers and high-frequency agents (e.g. a reference ABIDES configuration, from its code: 1,000 noise, 102 value, 12 momentum, 2 adaptive market makers). A sniper is a role, not a type: in Budish, Cramton and Shim's draft, firms choose between providing liquidity and sniping stale quotes and are indifferent. We found no scalper agent and no standard definition. Types are measured only where accounts are visible, and as classes of inventory or aggressiveness, not strategies (Kirilenko et al., 2017); we found no measured trend-following class. Platt and Gebbie (2018): two of six parameters converge and "the behaviors of different agent classes cannot be robustly resolved through calibration", on one stock over five days. We found no validation of agent rules against identified traders, and no classification of traders from public book and trade data alone. Sniping races cannot be seen in book data, since the losers do not show (Aquilina, Budish and O'Neill, 2022). "Not found" reflects our searches only.
- **Resting size.** No live experiment measuring the reaction to resting size was found, in crypto or elsewhere; Hautsch and Huang (2012) and Eisler et al. give aggregate estimates on equities. A live test that places and cancels large visible orders would raise spoofing concerns and is not proposed.

## Sample and shared definitions

Sample as Lectures 19 to 21: Bybit BTCUSDT perpetual, 20 Sep - 3 Nov 2025 (45 days). In sample: 20 Sep - 9 Oct, every curve and slope estimated here only. Out of sample: 11 Oct - 3 Nov. 10 Oct alone. Bootstrap over days (2,000 resamples), one-sided p-values, Benjamini-Hochberg at 5% over the primary p-values.

- **A real order:** trades with the same millisecond and side (Lecture 19). Classes by size S: 0.01-0.1, 0.1-1, 1-5, 5-20, 20 BTC or more. **Relative size** x = S / size at the best on its side at the last update.
- **Response** R(τ): the move of the mid from the last update before the order to τ later, signed for the order, in bp; τ in {0.1, 1, 10, 60, 300} s. **Net** of matched controls: random moments, one per 10 s, same side, hour, day, decile of the imbalance at the best and tercile of the mid's move over the last second, since takers tend to act just after a move (Lecture 21, H7).
- **Costs** before fees, in bp of the mid at the decision, latency L = 50 ms as in Lecture 21.

## The hybrid replay

Layers, each estimated in sample and added to the replay of Lecture 21:

| Layer | What it does | Comes from |
|---|---|---|
| A. Depletion | What our order takes is removed from the recorded book; our own later orders do not find it again | Bookkeeping |
| B. Refill | What was taken returns at fixed prices along a measured curve | H1 |
| C. Impact | The whole book is shifted by R(τ) for our size, net of controls | H2, H3, H5 |
| D. Triggered trading | Extra taker size on our side arrives along a measured curve; it can fill our later resting orders. It does **not** move the price again | H4 |
| E. Reaction to resting size | The curve of Lecture 21's H8 applied to our resting size, if it passes H8 here | H8 |

**No double counting.** The measured R(τ) already contains the price effect of the orders that follow. So C carries the whole price effect, and D changes only who trades against us. Layers are switched on one at a time, and the cost of an order is reported as a waterfall.

**Assumptions to state.** The effects add on top of the record. The record's later traders act as they did, though some would have acted otherwise. Reactions are measured on other traders' orders, not ours.

## Hypotheses

H1 to H9 test the hybrid replay; H10 to H15 are the styles. The correction runs over one p-value each for H1 to H7, H9 (actual over predicted), H10, H11, H12 and H15, and three each for H13 and H14. H8 is a condition on layer E and stands outside it.

- **H1 (refill at fixed prices).** After real orders of 1 BTC or more, depth is back more slowly at the prices taken than around the new mid: the share of orders with 90% of the depth back within 1 s, around the new mid (Lecture 18, §5.5) minus at the fixed prices, is above zero, out of sample.
- **H2 (impact is concave in size).** The exponent δ in net R(10 s) = c S^δ, fitted over the classes out of sample, is below 1. Reported beside it: the local exponent between the two smallest classes, against the literature's near-linear small-size regime.
- **H3 (the push fades).** For orders of 5 BTC or more: net R(300 s) < net R(60 s), out of sample. Lecture 20 found each order's own impact fading while the flow behind it carried the price on; this asks whether that holds for large orders, in clock time.
- **H4 (large orders draw more trading).** The excess same-side taker size in the next second, net of the controls, is larger after orders of 5-20 BTC than after orders of 0.1-1 BTC, out of sample. Reported: the excess relative to S, by class and at 1 and 10 s.
- **H5 (size relative to the queue is the better scale).** Fitted in sample, R(10 s) = c x^δ predicts out-of-sample responses of orders of 0.1 BTC or more with a lower mean squared error than R(10 s) = c S^δ. Reason: the size at the best halved after 10 October (Lecture 20), so a model in BTC should fall behind and one relative to the queue should not.
- **H6 (the hybrid replay beats the plain one on real orders).** For real orders of 1 BTC or more, out of sample, the hybrid's predicted path has a lower mean squared error at 10 s than the plain replay's, which predicts no response. Also reported, after Linna et al.: orders injected at matched moments without a large order, against natural orders in the same state cell (size, queue, spread, imbalance): rank correlation and sign agreement across cells; and predicted over actual response by class.
- **H7 (runs of orders).** For real runs of same-side orders adding up to 5 BTC or more within 10 s, with no large opposite order, out of sample: the hybrid replay's error in the average price of the run is smaller in absolute terms than the plain replay's walking of the book at the run's start. We have no trader identities, so a run stands in for one trader's sliced order; Maitrier et al. (2025, arXiv 2502.16246) report that synthetic metaorders obey the same impact law.
- **H8 (no free profit, a condition on layer E).** With layer E on and at zero fee, a round trip that posts a resting bid of x = 100%, sells at the ask at minimum size and cancels the bid must not earn more than the same round trip without the bid. If it does, E is not a cause we can use: it is left out of the hybrid replay, and its effect on results is reported only as a band, E on against E off. We expect this to be a real risk: Lecture 21's H8 measured an association, net +0.25 bp after one second, not proof of cause.
- **H9 (10 October).** In the cascade window, 20:50-22:50 UTC, actual over predicted response of orders of 1 BTC or more, with curves from the calm days, exceeds that of the same window on any other day (rank among the 45). In the model in x, the ratio is closer to 1 than in the model in S.

- **H10 (a sniper's footprint, and why it matters for our layers).** Orders sent within 100 ms after a move of Binance's price of 2 bp or more, in the same direction, have a larger net R(10 s) than other orders of the same size class, out of sample. Such orders are informed about a price that has already moved elsewhere, and ours would not be. If H10 holds, the impact layer is calibrated without them, and the difference is reported. Races themselves cannot be seen: the losers leave no trace.
- **H11 (a trend follower's footprint).** In the 60 s after the mid crosses its 50-minute average from below (above), signed taker flow is more on the side of the crossing than at matched moments without a crossing (same hour, same day, same tercile of the mid's move over the last 60 s), out of sample. 20-minute against 50-minute averages reported beside it. A simple rule, which a real trend follower need not use, so a failure says only that this footprint is absent.
- **H12 (a sliced order's footprint).** The share of taker size in runs of five or more orders of one exact size on one side, with near-regular gaps (coefficient of variation below 0.2), is larger than in the same day with the order of sizes shuffled within 5-minute blocks, out of sample.

- **Style shares, used by H13 to H15.** Each taker order goes to one footprint, in this order: sliced (H12), sniper-like (H10), large (1 BTC or more), other. The trend-like share cannot be given order by order, so it is the excess of H11 over its matched controls. All shares are of taker size, and are shares of footprints, not of traders.
- **H13 (do styles come at expected times?).** For the sliced, sniper-like and trend-like shares: the profile over the 24 hours in sample has a positive rank correlation with the profile out of sample. Reported: the shares day by day over the 45 days, in sample against out of sample, so that a change of style shows.
- **H14 (in what circumstances?).** Between the most and the least volatile third of hours (thirds fixed in sample), within the same hour of the day: the sniper-like and trend-like shares are higher, the sliced share is lower, out of sample. Reason: a move on Binance and a crossing of an average are both likelier in volatile hours, and someone working a large order may wait. Reported: the same by depth at the best and by spread.
- **H15 (does one style set off another?).** A Hawkes process with one type per footprint, extending Lecture 20's: the sum of the effects of one type on another (the off-diagonal branching ratios) is larger than with the labels shuffled within 5-minute blocks, out of sample. Each pair is reported after correction. What this shows is one style following another, not cause: both can answer the same move, and the footprints are partly defined by past prices, which is what the shuffling and the simulation with a known trigger are there to bound.

**Reported, no test.**

- **The market maker's footprint:** the share of updates with three or more levels near the best changing on both sides at once, against the same with one side shifted in time (at the best price alone the measure is too crude: in the simulation a market maker with 38% of traded size barely shows); the same size added on both sides; the clock of the changes; the refilling chains of Lecture 19. A one-hour look at 1 October (in sample) prompted the shifted comparison.

- The waterfall of layers A to D for market orders of each size, at once and sliced, 10 slices over 1 s, 10 s and 60 s: does the footprint reverse a ranking that the plain replay reports?
- Lecture 21's resting order at 0.1, 1 and 5 BTC under the hybrid replay, with our size in the line, against the plain replay; the same with the layer curves scaled by 0.5, 1 and 2. A result that changes sign inside that range is reported as undetermined.
- **The size at which the footprint matters:** the smallest size at which hybrid minus plain exceeds 0.1 bp (the margin of Lecture 21's H4). This replaces or confirms Lecture 21's flag from 0.1 BTC up. Below the sizes we can measure, 0.001 and 0.01 BTC, any statement is an extrapolation and is labelled so.

## Added 2026-11-05, before any of their results: patterns that can be recognised as they start

**What prompted this, stated before any out-of-sample result.** A quick look at three in-sample days (24 September, 1 and 7 October) found same-size taker orders about 30.22 s apart, with gaps that vary by a few milliseconds: for example, sells of exactly 20 BTC ten times at 30.215 s. Pieces join up to round parents, e.g. 1.667 BTC × 40 and 1.666 BTC × 20 = 100 BTC in 30 minutes, and 0.834 BTC × 40 and 0.833 BTC × 80 = 100 BTC in one hour. Bybit documents a TWAP strategy order with a 30-second default interval and a minimum run of 5 minutes, which is 10 slices. This is consistent with that tool, and we cannot prove it; it also offers randomised sizes (±20%), which an exact-size search misses. Out-of-sample days have not been looked at.

**A run.** Taker orders on one side, of equal size within 0.01 BTC, with a gap within 1 s of 30.22 s (other regular gaps reported apart). It is **recognised** at its third order, when two equal gaps have been seen, using only what was known then.

- **H16 (a run can be recognised as it starts).** Out of sample, recognised runs of 1 BTC a slice or more: a next slice arrives within 100 ms of the predicted time more often than at the same delay after matched non-runs of the same size and side. Reported: the share with a next slice, the number of slices that remain, the false alarms, and the share of taker size in such runs, day by day and by hour.
- **H17 (does the market see it coming?).** The net response to a slice recognised as part of a run, the fourth or later, is smaller than to a single order of the same size and same relative size x at a moment with no run under way. Reason: flow that can be expected should move the price less than a surprise. Reported: whether the mid, the depth at the best on the side to be hit and other takers' flow change in the 1 s before a predicted slice, against the same second in matched moments. Also the path over a whole run and after its end: this is the real test case for layers C and D, so H7 is reported on these runs beside its own.
- **H18 (levels).** Depth standing at prices that are multiples of 1,000 USDT is larger than at the neighbouring non-round prices (3 to 10 ticks away either side), out of sample, within 1% of the mid; the same for multiples of 100 USDT, reported. Reason: Lecture 18 saw walls at 111,000 USDT, and Osler (2003) found customer orders in currencies clustered at round numbers (to be checked against the source). Reported: pulls and additions at those prices as the mid comes near, and whether the price stops at them more than at neighbouring prices.

**Times, already measured.** Lecture 18: pulls in 7% of updates after a quiet second, 79% after a move of more than 5 bp, and 1.4 times the day's average in the first seconds of a minute. Lecture 19: at the start of minutes :00 and :30 pulls burst and depth jumps to 1.15 times the hour's average. Section 5 uses them as market-maker activity by time and adds them to H13 and H14 as a fourth profile.

The correction runs over one p-value each for H16, H17, H18 and H19 as well.

## Added 2026-11-05: a method for reading a market

The aim of this part of the lecture is to teach a method for reading a market, usable on any market with a public book and trades, not a catalogue of patterns. Section 5 is built around it.

| Step | The question | What to look at | From |
|---|---|---|---|
| 1. The state | Is there anything to trade against, and which way does it lean? | Spread, depth, the imbalance at the best | Lectures 18, 19 |
| 2. The flow | Who is pushing, and how hard? | Order-flow imbalance, taker size, how much reacts to what | Lecture 20 |
| 3. The styles | What is at work now? | A run under way, sniper-like orders, trend-like flow, market makers pulling or refilling | H10 to H16 |
| 4. Clock and levels | What is about to come? | Time to the next :00 or :30, the next slice of a run, round prices nearby | Lecture 19, H13, H16, H18 |
| 5. The circumstances | Is this an ordinary hour? | Volatility and depth against their usual values, a cascading pattern | H14, Section 6 |
| 6. The read | What do we expect next, and what would prove us wrong? | One sentence, written before looking ahead, then checked | H19 |

Taught on three real moments, each read in full using only what was known then: a calm hour, a run under way, and the cascade of 10 October. Then the reader does it alone, as an exercise on another market.

- **H19 (is a reading worth anything?).** A read, the measures of steps 1 to 5 known at each moment, with a simple model fitted in sample, predicts the size of the mid's move and the 10-s markout of Lecture 21's resting order over the next minute with a lower mean squared error than volatility and the time of day alone, out of sample. The primary measure is the size of the move. If this fails, the method describes a market and forecasts nothing, and the lecture says so. Reported: which steps add anything, one at a time.

## The teaching simulation (§2, no results claimed)

A small simulated market written for this lecture, to show the mechanics. Invented data; it runs in seconds on a laptop, and nothing about the real market is concluded from it. No ABIDES and no comparison run.

- **The market:** one book with a tick and a matching queue (price, then time), an event loop, and a hidden fair value that moves as a random walk.
- **Noise traders:** market orders, limit orders and cancellations at fixed rates (zero intelligence).
- **Market maker:** quotes a ladder around the mid every refresh, leaning its quotes against its position.
- **Trend follower:** sends a market order when a fast average crosses a slow one.
- **Sniper:** sees the fair value first and trades when the mid is a set distance from it, holding a position until the other edge is reached. The threshold rule follows the band of Rabechini Amaral (2026, arXiv 2608.00885, theoretical, preliminary draft), whose trader leaves the book unmoved. The fair value gets occasional jumps, since without them nothing goes stale.
- **Scalper:** our own definition, since the literature has none: joins the best price, then closes at a small gain or a stop, staying nearly flat.
- **Our order:** the same order of ours, inserted at the same moment.

**Experiments.** (1) Add one type at a time: what happens to our order's cost and to the path after it? (2) Different mixes that look alike on the usual statistics, the point of Platt and Gebbie (2018). (3) **Styles with the truth known:** publish only what Bybit publishes, a book every 100 ms and trades with no identities, and ask whether the methods of H10 to H15 recover each style's true share, a mix that was changed on purpose during the run, and a trigger built in on purpose (the sniper's push setting off the trend follower, the market maker pulling after it). Where they fail on a simulation with the answer known, a result on real data means little.

**The footprint chart.** One panel per player, drawn from the simulation with each player's orders coloured, since there we know who did what: size at each price over time, with the trades on top. Beneath it, the same seconds as the public feed shows them, colours gone. Then, for each player, a real moment from Bybit with the same shape, labelled as looking alike, not as that player.

**What rests on what.** Each footprint in the lecture is labelled by its support. From the literature: the player types, and stale quotes as a cost to the maker. From exchange documents: Bybit's TWAP default of 30 s. Our own measures, not validated by any source we found: two-sided pulses, the clock of the changes, and every setting of the simulation. A test on a venue that shows accounts (Hyperliquid's fills carry wallets) is an open option, and has not been run.

**The aim is styles, not names.** The question is not who a trader is. It is how large each style's share is, how the shares change over time, when a style can be expected to come in, and whether one style sets off another. Only footprints of behaviour are measured, each labelled as such; a round trip or one trader's sliced order cannot be followed without accounts.

## Running it

Run time on a 16 GB laptop: orders are sampled by the book lookups of Lecture 21, one heavy job at a time. Before the full run, a busy window is timed and any cut to days or grids is recorded here before results are seen.

## Left out, and why

- **Other market makers pulling their quotes together, on news or anything else.** The recorded background does not change in a hybrid replay, so it cannot produce a withdrawal that the record does not hold. News is also hard to time on our data. Stepping back is taken up in Lecture 23 as a choice of our own quoter, on triggers we can observe: the time of day, volatility, and cascading patterns in the flow.
- **Live tests with large orders.** Large orders are discussed, since they change the book and that is why the replay breaks. They are measured only on other traders' orders in the record. Live validation stays at the minimum size (capstone).
