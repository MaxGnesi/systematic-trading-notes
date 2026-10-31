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

## Section 4: 10 October (fixed 2026-10-30, before any of these results were computed)
Start of the cascade, T0: the first minute of 10 Oct whose absolute change of the mid over one minute (minute starts, best 10 levels file)
is larger than the largest one-minute change on any of the 20 in-sample days. Pre-window: [T0 - 2 h, T0).
Reference: every non-overlapping 2-hour window of the other 44 days, aligned to the same clock phase as the pre-window (about 528 windows).
p = (1 + number of reference windows at least as extreme) / (1 + number of reference windows), one-sided. Benjamini-Hochberg at 5% over H14-H18
(H18 counted as two). Descriptive: each measure in 15-minute steps from T0 - 6 h to T0 + 3 h.

- H14 (refilling chains): the number of levels refilled 3+ times in a row (as in Section 3) in the pre-window is higher than in the reference.
- H15 (depth): the average depth in the best 10 levels of both sides in the pre-window is lower than in the reference.
- H16 (feed delay): the 99th percentile of Bybit's publish delay, ts - cts per book update, in the pre-window is higher than in the reference.
- H17 (imbalance through the cascade): the AUC of I1 for the next mid move is above 0.5 in each 15-minute step from T0 - 2 h to T0 + 2 h
  (16 steps; per step a Mann-Whitney test; primary p = the largest of the 16).
- H18a (Binance gap): the average absolute gap between Bybit's mid and Binance's last trade price (BTCUSDT perpetual, aggTrades, last trade
  at or before the Bybit update) in the pre-window is wider than in the reference.
- H18b (lean towards Binance): on 10 Oct, from T0 - 2 h to T0 + 2 h, the rank correlation between Bybit's I1 and the gap Binance minus Bybit
  is positive (bootstrap over 15-minute blocks).

## Section 3.7: does the book have a clock? (added 2026-10-31, after the results above, fixed before any of these were computed)
The design of Lecture 13 §7 (round times on the trades), applied to the book. Days: the 44 days other than 10 Oct (10 Oct reported apart).
Slots, one minute each, from the schedule: minute :00 with funding (00:00, 08:00, 16:00 UTC); minute :00 without funding; minute :30;
minutes :15 and :45; minute :59. Control: minutes :07, :17, :37 and :47, which nobody schedules.
Per second (state at the end of each second, from l19_state): spread wider than one tick (0/1); depth in the best 5 levels of both sides
(q_bid5 + q_ask5, BTC). Per book update (Lecture 18's pulls): a pull, 5 or more of the best 20 levels on one side losing size beyond trades.
Baseline of each occurrence: the same measure over the hour ending 5 minutes before the slot starts. Per day and slot: ratio = sum over the
slot's occurrences of the measure in the window / sum of their baselines (sums, so that rare events and zeros are handled); the same for the
control; d = ratio(slot) - ratio(control). Statistic: mean d over the 44 days; one-sided p from 2,000 bootstrap resamples of days.
Benjamini-Hochberg at 5% over the 22 tests below. Robustness, reported: the sign of d in sample (20 days) and out of sample (24 days).

- H19 (spread): the share of seconds with a spread wider than one tick is higher in the slot minute than in the control (5 tests, one per slot).
- H20a (depth): depth in the best 5 levels is lower in the slot minute than in the control (5 tests).
- H20b (pulling back early): depth in the best 5 levels is lower over the 10 seconds before the slot than over the 10 seconds before the
  control (5 tests).
- H21 (pulls): the share of book updates with a pull is higher in the slot minute than in the control. The within-minute clock of Lecture 18
  §5.5 is in both, so this asks for more than that clock (5 tests).
- H22 (link to the trades): the funding minute differs more than other minutes :00 do, where Lecture 13 found trading heaviest: d(funding :00) -
  d(other :00) > 0 for the spread and < 0 for depth (2 tests).
- Left out beforehand: refilling chains (§3.4), about 38 a day, too rare to compare minutes (about 3 expected in all funding minutes together);
  the book's update rate, which Bybit's 100 ms publication caps at about 10 a second all day.
- Descriptive: each measure second by second from 60 s before to 60 s after the slot start, as a ratio to its baseline, slot and control.

## H23: who refreshes at :00 and :30? (added 2026-10-31, after the results of H19-H22, fixed before computing it)
H19-H22 found pulls and depth jumping at the start of minutes :00 and :30. Two explanations: signals recomputed when 30-minute and hourly bars
close (a direction, following the last bar), or liquidity providers refreshing on a timer (no direction). At each start s of minute :00 or :30
(48 a day) and of the control minutes :07, :17, :37, :47 (96 a day), 44 days without 10 Oct: r = log return of the mid from s - 30 min to
s - 5 s (bp); (a) change in depth asymmetry, (q_bid5 - q_ask5) at the end of second s + 10 minus at the end of second s - 5 (BTC);
(b) net taker flow, taker buys minus sells (Bybit taker orders, BTC), over [s, s + 10 s). Per day: rank correlation of r with (a) and with (b)
over the day's occurrences, slot and control apart. Statistic: mean over days of corr(slot) - corr(control); one-sided bootstrap over days
(2,000). Benjamini-Hochberg at 5% over H23a and H23b.
- H23a (depth follows the bar): corr(r, change in depth asymmetry) is higher at :00/:30 than in the control.
- H23b (taker flow follows the bar): corr(r, net taker flow) is higher at :00/:30 than in the control.
Reading fixed now: both hold -> signals on bars drive the refresh; both fail with correlations near the control's -> a refresh without
direction, as by liquidity providers on a timer; mixed -> reported as such.
