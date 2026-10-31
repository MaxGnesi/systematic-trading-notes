# Lecture 20: hypotheses, fixed before the results

H1-H9 fixed 2026-10-31, before any of their results were computed. One hypothesis per question, chosen where the literature
disagrees or where Lecture 19 left a question open; everything else is reported as a measurement, not tested.

Sample: as Lecture 19. Bybit BTCUSDT perpetual, 20 Sep - 3 Nov 2025 (45 days): book (200 levels, 100 ms, clock cts) and trades (ms).
Binance BTCUSDT perpetual: aggregate trades (price, quantity, aggressor side, transaction time in ms), same days.
Split: in-sample = 20 Sep - 9 Oct (20 days); out-of-sample = 11 Oct - 3 Nov (24 days); 10 Oct alone.
Uncertainty: bootstrap over days (2,000 resamples) unless stated; one-sided p-values. Multiple tests: Benjamini-Hochberg at 5% over the
primary p-value of every hypothesis (parts a, b, c counted separately). Economic value after costs is not tested here (Lectures 23-24).

Shared definitions. Tick = $0.10; mid m in ticks. Taker order = trades with the same ms and side, size summed (Lecture 19).
Intervals: non-overlapping clock intervals of length D in {1 s, 10 s, 60 s}; intervals touching one of the three feed gaps are dropped.
Regressions are fitted on the in-sample days and scored out of sample (R2 = 1 - squared errors / squared deviations from the in-sample mean).

## Order-flow imbalance (Section 3.1; data: a new pass over the book, best 10 levels per update)
Per book update n at the best bid (b) and ask (a), with prices P and sizes q (Cont, Kukanov and Stoikov, 2014):
e_n = 1{Pb_n >= Pb_n-1} qb_n - 1{Pb_n <= Pb_n-1} qb_n-1 - 1{Pa_n <= Pa_n-1} qa_n + 1{Pa_n >= Pa_n-1} qa_n-1.
OFI(D) = sum of e_n over the interval. Trade imbalance TI(D) = taker buy size - taker sell size (BTC).
Model: change of the mid over the interval = a + b x + error, x = OFI or TI.

- H1 (book or trades): out-of-sample R2 of OFI > that of TI at D = 10 s. The literature disagrees: for 50 US stocks at 10 s OFI
  explained 65% of the variance and TI 32% (Cont, Kukanov and Stoikov, 2014); for the BitMEX bitcoin perpetual TI explained more
  (Silantyev, 2019).
- H2 (forecast): OFI over the previous interval forecasts the change of the mid over the next one: out-of-sample R2 > 0 at D = 10 s.
  Kolm, Turiel and Westray (2023) found order flow forecasts at short horizons; on our Binance tape (Lecture 15) one-sided flow
  forecast almost nothing at minutes.
- Reported, not tested: R2 at 1 s and 60 s; OFI from the best 10 levels (Xu, Gould and Howison, 2019; Cont, Cucuringu and Zhang, 2023);
  b against depth at the best, per half-hour window (Cont, Kukanov and Stoikov: b proportional to 1 / depth); Kyle's lambda (b with
  x = TI, ticks per BTC), which Section 4 uses.

## Impact over time (Section 3.2; data: taker orders + the book state just before each)
Sign e_i = +1 for a taker buy, -1 for a sell; trade time i counts taker orders. C(l) = autocorrelation of the signs at lag l.
Response R(l) = average of e_i (m_i+l - m_i), in ticks, m_i = mid just before order i. Propagator G(l): the bare impact of one order
l orders later, fitted by least squares from R and C on lags 1..1000 (Bouchaud, Gefen, Potters and Wyart, 2004).
This section explains a Lecture 19 result: the price kept moving against the maker for a minute after a fill.

- H3 (bare impact decays): G(500) < G(1) on more days than not (sign test). If it holds, the price keeps moving after a fill because
  the next orders tend to have the same sign, not because one order's impact grows.
- Reported, not tested: C(l) and its power-law exponent on lags 10..1000 (Lillo and Farmer, 2004, found about 0.6 on the London
  Stock Exchange).

## Toxicity: VPIN (Section 3.3; data: Bybit trades)
VPIN as Easley, López de Prado and O'Hara (2012): volume buckets of V = average daily volume of the in-sample days / 50; buy and sell
volume per bucket from the true aggressor side, which Bybit records; VPIN = average of |V_buy - V_sell| / V over the last 50 buckets.
Sampled at the start of every hour. Target: realised volatility of the mid over the next hour (sum of squared one-minute changes).

- H4 (beyond activity): partial rank correlation of VPIN with the next hour's realised volatility, controlling for the last hour's
  realised volatility and the last hour's volume, > 0 out of sample. Holds = VPIN adds information, as its authors claim; fails = in
  line with the critique of Andersen and Bondarenko (2014), who found its forecast subsumed by trading intensity.
- Reported, not tested: the plain rank correlation without controls; VPIN with bulk volume classification over one-minute bars, as
  the original.

## Self-excitation: Hawkes processes (Section 3.4; data: Bybit taker orders)
Intensity lam(t) = mu + sum over past events of phi(t - t_j); kernel phi = sum of exponentials with fixed decay times
{1 ms, 10 ms, 100 ms, 1 s, 10 s, 100 s} and non-negative weights (Bacry, Mastromatteo and Muzy, 2015); fitted by maximum likelihood
per hour with a constant mu, so that the daily pattern of activity is not read as excitation (Filimonov and Sornette, 2015).
Branching ratio n = sum of the weights = the share of events triggered by earlier events.

- H5 (not critical): n < 0.9 in more hours than not (sign test over hours, blocks of days for the bootstrap). The literature
  disagrees: on E-mini S&P 500 futures, Filimonov and Sornette (2012) found n rising from about 0.3 in 1998 to above 0.7 from 2007;
  Hardiman, Bercot and Bouchaud (2013), with a power-law kernel, close to 1; Filimonov and Sornette (2015) showed that outliers, the
  daily pattern and regime shifts bias n upwards.
- Reported, not tested: the distribution of n by hour; book pulls (Lecture 18, §5.5) with the same kernel from 100 ms upwards (at the
  book's 100 ms a reaction faster than one update cannot be told from a common trigger).

## Lead and lag between Bybit and Binance (Section 3.5)
Prices: Bybit last trade and Bybit mid (book, cts); Binance last trade. Cross-correlation of price changes by the Hayashi-Yoshida
estimator for non-synchronous data, at lags -1 s .. +1 s in 1 ms steps (Hoffmann, Rosenbaum and Yoshida, 2013); lead = lag of the
maximum; lead-lag ratio LLR = sum of squared correlations at positive lags / at negative lags (Huth and Abergel, 2014). Positive = Binance first.
Prior: the dominant perpetual venues led price discovery in bitcoin (Alexander and Heck, 2020); on our days Binance traded about 1.7-1.9
times Bybit's BTCUSDT volume (two days checked).
Caveat stated with every result: a constant offset between the two venues' clocks looks like a lead; a lead that changes with market
conditions cannot be a constant offset.

- H6 (Binance leads): lead > 0 on more days than not (sign test), and pooled LLR > 1 out of sample. Last trade on both venues (primary).
- H7 (the Lecture 19 puzzle): on calm days Bybit's I1 correlated negatively with the gap Binance last trade - Bybit mid (L19, H18b).
  Mechanism to test: the bounce of Binance's last trade between its bid and ask. With the Binance price replaced by the midpoint of its
  last taker buy and last taker sell within the past 1 s, the rank correlation is higher (less negative) on more days than not.
- Reported, not tested: the lead with Bybit's mid; a two-venue Hawkes process (which venue's orders trigger the other's).

## 10 October: flow before the news and before the fall (Section 4)
The news: the tariff post at 20:50:01.702 UTC, timed from its post ID and checked against the American Presidency Project's log
(Section 4.1 shows the method). T0 = 21:14 UTC (Lecture 19's rule).
Reference: every non-overlapping window of the same length on the other 44 days, aligned to the same clock phase.
p = (1 + number of reference windows at least as extreme) / (1 + number of reference windows), one-sided.
Disclosure: a first look at minute data (28 Oct, while building Lecture 18) saw no visible move before the post and two Binance sells of
at least $1M about 160 s before it. H8 is therefore not blind to that look; it is fixed now to judge it against the other days.

- H8 (selling before the post): net aggressive flow TI over the hour before the post, [19:50:01.7, 20:50:01.7), is lower (more net selling) than in the reference (about 1,050 windows): (a) Bybit, (b) Binance.
- H9 (fragility before the fall): over the two hours before the post, [18:50:01.7, 20:50:01.7), each of (a) VPIN (average),
  (b) Hawkes n (taker orders, fitted on the window), (c) Kyle's lambda (b of TI on 10 s intervals) is higher than in the reference
  (about 528 windows).
- Reported, not tested: OFI, large sells (at least $1M) and synchronised pulls (at least 5 of the best 20 levels on both sides shrink
  beyond trades in one update) in the hour before the post.
- Early-warning table (descriptive; rule fixed now): each indicator of Lecture 19 (depth in the best 10 levels, spread, refill chains,
  publish delay) and of this lecture (OFI, TI, VPIN, Hawkes n per 15 min, Kyle's lambda, pull rate, synchronised pulls) per minute;
  a flag = beyond the 99th percentile of the in-sample days' minutes (below the 1st for depth) for 5 minutes in a row.
  Lead time = post time - first flag on 10 Oct in the 6 hours before; false alarms = flags per day on the other 44 days.
  Framing: one event cannot separate informed trading from chance; no one is named or accused.
