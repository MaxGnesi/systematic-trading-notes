# Lecture 8: hypotheses and results record

This record holds the tests of Lecture 8 run with scripts; the other examples of the lecture are computed in its notebook.

## Taking profits (§4.8), moved from Lecture 13, 2026-11-16

*Moved from Lecture 13's record on 2026-11-16, unchanged, when the topic moved to this lecture (the user: Lecture 13 is only portfolio construction). The scripts paths in it are the old ones: `l27_crisis.py` is now `scripts/l26_crisis.py`, `l27_timing.py` `scripts/l26_timing.py`, `l27_takeprofit.py` Lecture 8's `scripts/takeprofit.py`.*

### Take-profit per speed, fixed 2026-11-14 before any result (the user)

- **Rule:** for each stream, the open gain since its signal last changed (sum of sign x daily return), in units of that speed's risk (six-month daily volatility at entry x square root of the speed); above k units the stream goes flat until its signal changes. Positions otherwise as in Lecture 12 (10% / volatility, a tenth of the way each day, 5 bp).
- **Grid:** k = 2, 3, 4, 5 and none. Only within Lecture 12's held set.
- **Judged:** ETFs out of sample 2013-2026 with the rule's structure; capstone futures 2003-2022 (Lecture 12's end-2025 held set). Sharpe ratio after costs, worst drawdown, the 12 worst months of the plain version, skew of monthly returns, and the return in each crisis episode inside each period.
- **Expectations:** (1) it helps in the quick crashes that follow run-ups; (2) it lowers Sharpe ratio and skew overall, because it cuts the large winners; (3) slightly lower Sharpe at k = 2-3, about unchanged at 5.
- **Exercise, not tested:** halve the position instead of exiting.
- **Added 2026-11-14 before any result (the user): re-entry after a pullback of one unit.** After a take-profit, the stream re-enters when the price has pulled back one unit from its best level since the exit; the re-entry is a new trade (gain reset, next take-profit after another k units). Reported next to exit-until-the-signal-changes.

**Take-profit, result (2026-11-14, on the saved data).** Breakout on closes in all versions, so the plain ETF version earns 0.465 here (0.486 with highs and lows).

| | none | k=2 | k=3 | k=4 | k=5 | k=3, re-entry | k=5, re-entry |
|---|---|---|---|---|---|---|---|
| ETFs: Sharpe | 0.465 | 0.370 | 0.417 | 0.464 | 0.477 | 0.414 | 0.467 |
| ETFs: volatility | 10.7% | 7.7% | 9.0% | 9.5% | 9.9% | 9.7% | 10.3% |
| ETFs: drawdown / volatility | 2.12 | 2.25 | 2.06 | 1.99 | 2.00 | 2.18 | 2.14 |
| ETFs: skew, monthly | 0.24 | 0.32 | 0.38 | 0.41 | 0.38 | 0.13 | 0.27 |
| Futures: Sharpe | 0.466 | 0.422 | 0.454 | 0.491 | 0.494 | 0.461 | 0.477 |
| Futures: drawdown / volatility | 2.45 | 3.21 | 2.78 | 2.52 | 2.44 | 2.67 | 2.46 |
| Futures: 12 worst months / volatility | 6.23 | 5.05 | 5.55 | 5.76 | 5.96 | 5.98 | 6.15 |
| Futures: skew, monthly | 0.22 | 0.51 | 0.45 | 0.41 | 0.36 | 0.28 | 0.26 |

Reading: at k = 4-5 the Sharpe ratio is unchanged or slightly higher on both datasets (bands not yet computed), skew rises, and most of the smaller raw drawdowns comes from carrying less risk; per unit of risk the gain is small (ETFs) to modest in the worst months (futures). Quick crashes lose less (ETFs 2020: -13.8% to -10.7% at k=4), long bear markets give some back (ETFs 2022: +26% to +18%). Re-entry after a one-unit pullback does not improve on exiting until the signal changes. Expectation 1 met mildly; 2 not met (skew rises); 3 partly (lower at k=2-3, unchanged or higher at 4-5). Nine variants tested.

**Take-profit, bands (2026-11-14).** Sharpe ratio difference against no take-profit, 90% band, block bootstrap over months: ETFs k=3 -0.05 (-0.17 to +0.07), k=4 -0.00 (-0.09 to +0.09), k=5 +0.01 (-0.06 to +0.08); futures k=3 -0.01 (-0.10 to +0.08), k=4 +0.02 (-0.04 to +0.09), k=5 +0.03 (-0.01 to +0.07). No difference is distinguishable from zero: the take-profit is an option with known trade-offs (higher skew, smaller losses in quick crashes, less in long bear markets), not an improvement in return.
