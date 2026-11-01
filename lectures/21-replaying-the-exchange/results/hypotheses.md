# Lecture 21: hypotheses, fixed before the results

H1-H9 fixed 2026-11-01, after review, before any of their results were computed.

## The plan of the lecture

The question: what would have happened to *our* orders in the recorded market? A replay answers it by inserting hypothetical orders into
the recorded book and trades. The market does not react to them (non-reactive replay); its reaction is Lecture 22. The lecture first lays
out all the pieces of the puzzle intuitively, then builds the replay piece by piece on our data, then tests whether it tells the truth.

1. **The key chart.** One real moment: a bid at the best price followed under three replays (filled on touch, filled when its turn in the
   queue comes, filled when the price runs through it), and the price after the fill under each. Message: a naive replay hands us the good
   fills and hides the bad ones.
2. **The pieces of the puzzle, intuitively**, one card each with an invented example: what a replay is; the latency gap (the book changes
   between what we saw and when our order arrives); the queue (what is ahead of us, and when we reach the front); adverse fills (the fills we
   get are the bad ones); our footprint (left out on purpose, Lecture 22); the families of models side by side (fill rules, queue models,
   fill probabilities, latency) and where each is used.
3. **The replay on our data, deep dive**: ordering trades (ms) against the book (100 ms); market orders walking the book after a latency;
   resting orders in the queue with the unknown cancellation split as a parameter; fills through the level against fills at it.
4. **Does the replay tell the truth?** The tests below, on the 45 days, by order size.
5. **10 October.** The replay in the cascade.
6. **Summary, exercises and reading.**

Literature read for the design: Albers, Cucuringu, Howison and Shestopaloff (2025), live market orders on Bybit; Albers et al.
(arXiv 2502.18625), live resting orders on Binance; Lalor and Swishchuk (arXiv 2409.12721) and DeLise (arXiv 2407.16527), adverse fills;
Rigtorp (2013), Databento, hftbacktest and NautilusTrader, queue position from aggregated books; Cartea, Jaimungal and
Sanchez-Betancourt (arXiv 1908.03281), latency.

## Sample and shared definitions

Sample: as Lectures 19 and 20. Bybit BTCUSDT perpetual, 20 Sep - 3 Nov 2025 (45 days): book (200 levels, 100 ms, clock cts) and trades (ms,
aggressor side). Split: in-sample = 20 Sep - 9 Oct (20 days); out-of-sample = 11 Oct - 3 Nov (24 days); 10 Oct alone. Uncertainty: bootstrap
over days (2,000 resamples) unless stated; one-sided p-values; Benjamini-Hochberg at 5% over the primary p-values of the tested hypotheses.

- **Event order.** Book updates at cts, trades at their ms. Between two book updates, trades at our price are applied first; the decrease of
  the level at the next update beyond those trades counts as cancellation.
- **Latency L.** An order decided at t becomes active at t + L, against the book and trades from t + L on. Grid: L in {10, 50, 100} ms.
- **Order sizes S.** {0.001 (Bybit's minimum), 0.01, 0.1, 1, 5} BTC.
- **The test resting order** (the design of Albers et al.'s live experiment on Binance): S at the best bid and S at the best ask; if the best
  price on its side moves away from it, cancelled and re-posted at the new best after L; after a fill, re-posted after L.
- **Fill rules.** Q0 (touch): filled as soon as a trade occurs at our price. Q1 (trade-through, Lecture 17's rule): filled only when a trade
  occurs beyond our price. Q2 (queue): we join behind the displayed size; trades at our price reduce the size ahead; a cancellation of size c
  at our level is split, a share p ahead of us, with p = x^a, x = ahead / (ahead + behind); a = 1 is a uniform split, larger a puts more of the
  cancellations behind us, a = infinity puts them all behind (the "risk-averse" model). Grid: a in {1, 2, 5, 20, infinity}. Trades at our price
  beyond the size ahead fill us, partly if needed. A trade beyond our price fills what is left.
- **Adverse fill.** A fill in an interval in which the best price on our side moved through our level; otherwise non-adverse.
- **Markout** of a fill: the mid h seconds after the fill minus the fill price, signed for our side, h in {1, 10} s, in bp; reported before and
  after Bybit's base maker fee (0.02%).
- **Taker test orders.** At t, a market order of size S walks the book standing at t + L; an IOC order at the best price seen at t fills what
  stands at that price at t + L.

## Hypotheses

- **H1 (naive fill rules flatter).** For the test resting order of 0.001 BTC, Q2 with a = 1, L = 50 ms, out of sample: the 1-s markout per fill
  is higher under Q0 than under Q2, and higher under Q2 than under Q1. Primary test: markout(Q0) - markout(Q2) > 0.
- **H2 (trade-through fills are the bad ones).** Under Q2 (a = 1, L = 50 ms, 0.001 BTC), out of sample: the 1-s markout of non-adverse fills
  is higher than that of adverse fills.
- **H3 (the unknown cancellation split does not decide the answer).** Plateau check, reported not tested: across a in {1, 2, 5, 20, infinity}
  and L in {10, 50, 100} ms, the fill rate falls as a rises, and the sign of the mean 10-s markout after the maker fee is the same at every grid
  point. A result that changes sign inside the grid is reported as undetermined by our data.
- **H4 (the replay is no kinder than reality).** The 1-s markout of the replay's fills (Q2, a = 1, 0.001 BTC) is not more than 0.1 bp better
  than that of real resting orders filled at the best by real taker orders below 0.01 BTC (Lecture 19's markouts), out of sample
  (non-inferiority, bootstrap over days).
- **H5 (the clock).** Under Q2, fills in the first 10 s of minutes :00 and :30 have a lower 1-s markout than fills at other times
  (Lecture 19 §3.7, open question).
- **H6 (10 October).** In the cascade (20:50-22:50 UTC), the share of adverse fills and the loss per fill of the test order exceed the
  largest value of the same window on any other day.
- **H7 (where the replay breaks for market orders).** For real taker orders, the gap between the average price they actually paid and the price
  predicted by walking the last book before them grows with size: gap(orders of 5 BTC or more) - gap(orders below 0.01 BTC) > 0, out of sample.
- **H8 (the market reacts to large resting size).** After size of at least x of the best queue is added at the best in one book update, the
  mid over the next 1 s and 10 s moves away from the addition more than at matched moments without such an addition (same side, same decile of
  the imbalance at the best, same hour of the day, same day), and more so the larger the addition; x in {25%, 100%, 400%}, primary x = 100%.
  The smallest x at which the effect appears sets the validity of the replay for resting orders: sizes above it are reported but flagged.
  Additions removed again within 1 s (spoof-like) are reported apart.
- **H9 (how conservative Lecture 17's rule was).** For resting orders 10 bp from the mid (Lecture 17's smallest step), Q2 (a = 1) fills more
  often than Q1, and the fills that Q1 misses have a 10-s markout at least as high as Q1's fills: the rule undercounted the better fills.

Descriptive, not tested:
- **Latency for takers** (Albers et al. 2025, replicated in the replay as a demonstration of the mechanism): IOC orders at the best fail more
  often when the later return is positive, and more in volatile hours. In a replay the outcome follows from the recorded book by
  construction, so this shows the mechanism, not the truth.
- **Effective latency:** the L at which walking the book reproduces the prices of real large taker orders best.
- Every result by size S, with sizes above the validity of H8 flagged.
