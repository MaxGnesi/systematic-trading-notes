# Lecture 19 §3: hypotheses, fixed before the 45-day results

H1-H5 fixed 2026-10-29; H6-H13 fixed 2026-10-30, before any of their results were computed.

Sample: Bybit BTCUSDT, 20 Sep - 3 Nov 2025 (45 days). Book clock: cts (matching engine); trades: their own ts (ms).
Split: in-sample = calm days before the cascade, 20 Sep - 9 Oct (20 days); out-of-sample = 11 Oct - 3 Nov (24 days); 10 Oct alone.
Uncertainty: bootstrap over days (2,000 resamples) unless stated; one-sided p-values. Multiple tests: Benjamini-Hochberg at 5% over
the primary p-value of every hypothesis H1-H13. Economic value (after costs) is not tested here (Lecture 23).

## Imbalance (data: l19_state, one row per book update)
Sampling as Gould & Bonart (2015): one point per interval between changes of the mid, the book state at a random update inside it,
kept if the spread is one tick there. Event: the next change of the mid, up or down.
I1 = (q_bid - q_ask) / (q_bid + q_ask); I5: same with the best 5 levels. Model: logistic P(up) = 1 / (1 + exp(-(x0 + x1 I))). Measure: AUC.

- H1 (direction): x1 > 0 in sample; out-of-sample AUC of I1 > 0.5.
- H2 (stability): x1 > 0 and AUC > 0.5 on each of the 45 days (sign test over days); spread of daily AUC.
- H3 (regime): AUC > 0.5 out of sample (11 Oct - 3 Nov) and on 10 Oct alone; reported against in-sample AUC.
- H4 (depth): AUC of (I1, I5) together > AUC of I1 alone, out of sample.
- H5 (mechanics): AUC is highest where the smaller of the two best queues is small: AUC(min queue < 0.1 BTC) - AUC(min queue > 1 BTC) > 0.
- Comparison: x1 and AUC against Gould & Bonart's large-tick Nasdaq stocks (x1 about 2-2.7, AUC 0.75-0.81).

## Gaming-resistant imbalance and spoof candidates (data: a second pass over the full book with the trades)
Weighted I5 over the best 5 levels of each side: weight exp(-k / lam) at k ticks behind the best; age filter: count only depth that has
rested at least tau seconds (age by FIFO replay: additions join the back, trades take from the front, cancellations from the back);
smoothing: exponentially weighted average of I5 over book updates with half-life hl seconds.
Grid, fixed now: lam in {0.5, 1, 1.5, 3, 5}; tau in {0.25, 0.5, 1, 2, 5} s (with lam = 1.5); hl in {0.2, 0.5, 1, 2, 5} s.

- H6 (no loss of power): out of sample, the AUC of each weighted, age-filtered or smoothed version is not more than 0.01 below the AUC of
  plain I5 (non-inferiority, day bootstrap). Verdict per family requires it at every grid point (a plateau), not at a chosen one.
- H7 (resistance): spoof candidate = an addition of at least Q BTC at 1-9 ticks behind the best, removed within T s with no trade at that
  price during its life. At the update the candidate arrives, |change of plain I5| > |change of the distance- and age-weighted I5|
  (lam = 1.5, tau = 1 s), on more days than not (sign test over days). Grid: Q in {2, 5, 10} BTC, T in {1, 2, 5} s. Counts per day reported.

## Microprice (data: l19_state)
In sample: g(I) = average change of the mid until the next mid change, and over 1 s and 10 s, by 20 bands of I1 (spread one tick).
Microprice = mid + g(I): a first-step, empirical version in the spirit of Stoikov (2018), not his limit estimator.
- H8: out of sample, the mean squared error of the microprice in forecasting the mid (after the next change; at +1 s; at +10 s) is below
  that of the mid and of the weighted mid, at all three horizons.

## Shape of the book (second pass)
Depth = size in the best 10 levels of both sides, sampled at the start of every minute.
- H9 (Naes-Skjeltorp): depth is negatively related to the absolute change of the mid over the next 5 minutes, controlling for the
  absolute change over the previous 5 minutes (partial rank correlation < 0 pooled; and on more days than not, sign test).

## Queues (second pass)
At the best bid and ask, each update: decrease split into traded (trades at that price in the interval) and cancelled (the rest).
Time to empty = queue size / (traded + cancelled - added) over the previous 1 s (infinite if not shrinking).
- H10 (cancellations dominate): cancelled > traded in the decreases of the best queues, on every day (sign test over days).
- H11 (queue race): adding log(time to empty of the bid / that of the ask) to I1 raises the out-of-sample AUC of the next mid move.
- Icebergs (descriptive, no test): levels taken to zero by trades and refilled at the same price by a similar size (within 20%) within
  1 s, at least 3 times in a row; counts per day.

## Markouts (data: trades + l19_state)
Fill = one taker order: trades with the same ms and side, size summed, price size-weighted. The resting (maker) side is opposite to the
taker. Markout per BTC for the maker: M(h) = s_maker (m(t+h) - p), m = mid of the last book state before the trade, h in {0, 0.1, 1, 10, 60} s.
Price impact at h = M(0) - M(h). Averages are size-weighted, in ticks.
- H12 (adverse selection): price impact > 0 at 1 s and 10 s, out of sample.
- H13 (size): price impact at 10 s is larger for larger taker orders: impact(> 1 BTC) - impact(< 0.01 BTC) > 0, out of sample.
