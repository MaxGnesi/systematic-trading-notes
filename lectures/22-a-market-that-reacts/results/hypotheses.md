# Lecture 22: hypotheses, fixed before the results

DRAFT for review, 2026-11-05. No result of this lecture has been computed.

## The plan of the lecture

The question: what if the market responds to our order? Lecture 21 replayed the record as if our orders were invisible, and flagged its resting results from 0.1 BTC up. This lecture keeps the recorded market as the background and adds the measured reaction on top, one layer at a time, then tests whether the result predicts what real large orders did. It is a **hybrid replay**, not a simulated market: a simulator's background has to generate everything itself, including patterns we may not know to put in.

1. **The key chart.** One real market order of about 5 BTC beside a moment that had none, where the same order is injected: the book and the mid as the plain replay reports them, as the hybrid replay reports them, and what happened after the real order. Message: a plain replay lets the price forget our order at once, and restores what we took.
2. **The pieces, one card each on invented data:** depletion (what we took is gone); refill (how it comes back); impact that fades; triggered trading; the reaction to resting size. Then the families of models side by side: plain replay, hybrid replay, event propagators, queue-reactive and agent-based simulation, generative models, and where each is used.
3. **The layers on our data:** each measured on real orders in sample, by size and by size relative to the queue.
4. **Does the hybrid replay tell the truth?** The tests below.
5. **10 October.** Do layers calibrated on calm days hold in the cascade?
6. **Summary, exercises and reading.** What the footprint does to Lecture 21's flag; what remains for live orders.

## Literature read for the design

Notes with read status: session notes, `l22_literature_notes.md`; every number quoted in the lecture is to be checked against the source first.

- **Has this been done?** We found no paper that puts calibrated depletion, refill, fading impact, triggers and resting-size reaction on a recorded book. Nearest: Karpe et al. (2020, arXiv 2006.05574), replay plus reactive agents, no impact validation; Lu and Abergel (2018, arXiv 1806.05101), replay plus fictitious orders, passive impact left out; Noble, Rosenbaum and Souilmi (2026, arXiv 2603.24137), a fading-impact layer on a queue-reactive simulator.
- **How to validate.** Mostly impact shape against published values. The template used here is Linna et al. (2026, arXiv 2609.16930): injected scenarios against naturally occurring matched events, since agreement with a simulator shows only "consistency with their encoded dynamics".
- **Reaction layers can be exploited.** Coletta et al. (2023, arXiv 2306.12806): in a generative simulator a large bid with a small ask, one tick off the touch, earns a round-trip profit by pushing the imbalance. Hence H8.
- **Replay already has an impact, of a wrong kind.** Coletta et al. (2023) and Balch et al. (2019, arXiv 1906.12010): levels are not restored, then the record pulls the mid back.
- **Scale.** Square root over about two decades, close to linear at the smallest participation (Bucci et al., 2019, arXiv 1811.05230; Zarinelli et al., 2015). On bitcoin, δ about 0.5 (Donier and Bonart, 2015). A static book overstates impact four times (Weber and Rosenow, 2005).
- **Limits of our data.** Event propagators (Eisler et al., 2012; Taranto et al., 2018) need signs and types of single events; a 100 ms book merges them, so they are not estimated here. Taranto et al. state that such models do not react to past events, so they could not supply a reaction layer in any case.
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

## Hypotheses (draft)

- **H1 (refill at fixed prices).** After real orders of 1 BTC or more, depth is back more slowly at the prices taken than around the new mid: the share of orders with 90% of the depth back within 1 s, around the new mid (Lecture 18, §5.5) minus at the fixed prices, is above zero, out of sample.
- **H2 (impact is concave in size).** The exponent δ in net R(10 s) = c S^δ, fitted over the classes out of sample, is below 1. Reported beside it: the local exponent between the two smallest classes, against the literature's near-linear small-size regime.
- **H3 (the push fades).** For orders of 5 BTC or more: net R(300 s) < net R(60 s), out of sample. Lecture 20 found each order's own impact fading while the flow behind it carried the price on; this asks whether that holds for large orders, in clock time.
- **H4 (large orders draw more trading).** The excess same-side taker size in the next second, net of the controls, is larger after orders of 5-20 BTC than after orders of 0.1-1 BTC, out of sample. Reported: the excess relative to S, by class and at 1 and 10 s.
- **H5 (size relative to the queue is the better scale).** Fitted in sample, R(10 s) = c x^δ predicts out-of-sample responses of orders of 0.1 BTC or more with a lower mean squared error than R(10 s) = c S^δ. Reason: the size at the best halved after 10 October (Lecture 20), so a model in BTC should fall behind and one relative to the queue should not.
- **H6 (the hybrid replay beats the plain one on real orders).** For real orders of 1 BTC or more, out of sample, the hybrid's predicted path has a lower mean squared error at 10 s than the plain replay's, which predicts no response. Also reported, after Linna et al.: orders injected at matched moments without a large order, against natural orders in the same state cell (size, queue, spread, imbalance): rank correlation and sign agreement across cells; and predicted over actual response by class.
- **H7 (runs of orders).** For real runs of same-side orders adding up to 5 BTC or more within 10 s, with no large opposite order, out of sample: the hybrid replay's error in the average price of the run is smaller in absolute terms than the plain replay's walking of the book at the run's start. We have no trader identities, so a run stands in for one trader's sliced order; Maitrier et al. (2025, arXiv 2502.16246) report that synthetic metaorders obey the same impact law.
- **H8 (no free profit, a condition on layer E).** With layer E on and at zero fee, a round trip that posts a resting bid of x = 100%, sells at the ask at minimum size and cancels the bid must not earn more than the same round trip without the bid. If it does, E is not a cause we can use: it is left out of the hybrid replay, and its effect on results is reported only as a band, E on against E off. We expect this to be a real risk: Lecture 21's H8 measured an association, net +0.25 bp after one second, not proof of cause.
- **H9 (10 October).** In the cascade window, 20:50-22:50 UTC, actual over predicted response of orders of 1 BTC or more, with curves from the calm days, exceeds that of the same window on any other day (rank among the 45). In the model in x, the ratio is closer to 1 than in the model in S.

**Reported, no test.**

- The waterfall of layers A to D for market orders of each size, at once and sliced, 10 slices over 1 s, 10 s and 60 s: does the footprint reverse a ranking that the plain replay reports?
- Lecture 21's resting order at 0.1, 1 and 5 BTC under the hybrid replay, with our size in the line, against the plain replay; the same with the layer curves scaled by 0.5, 1 and 2. A result that changes sign inside that range is reported as undetermined.
- **The size at which the footprint matters:** the smallest size at which hybrid minus plain exceeds 0.1 bp (the margin of Lecture 21's H4). This replaces or confirms Lecture 21's flag from 0.1 BTC up. Below the sizes we can measure, 0.001 and 0.01 BTC, any statement is an extrapolation and is labelled so.

## Running it

Run time on a 16 GB laptop: orders are sampled by the book lookups of Lecture 21, one heavy job at a time. Before the full run, a busy window is timed and any cut to days or grids is recorded here before results are seen.

## Left out, and why

- **Other market makers pulling their quotes together, on news or anything else.** The recorded background does not change in a hybrid replay, so it cannot produce a withdrawal that the record does not hold. News is also hard to time on our data. Stepping back is taken up in Lecture 23 as a choice of our own quoter, on triggers we can observe: the time of day, volatility, and cascading patterns in the flow.
- **Live tests with large orders.** Large orders are discussed, since they change the book and that is why the replay breaks. They are measured only on other traders' orders in the record. Live validation stays at the minimum size (capstone).
