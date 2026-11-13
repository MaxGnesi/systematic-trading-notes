# Lecture 26: Trend Speeds That Work Across the Board

*Systematic Trading: Lecture Notes (MSc) · draft, Nov 13, 2026 · Max Gnesi*

Lecture 25 chose the markets without looking at any strategy's results. This lecture takes the next step of the portfolio part's workflow: it chooses the **speeds** of the trend rules that will trade them. It is the one step that may look at how a strategy performed, so it is also where a portfolio is most easily fitted to the accidents of the past. The question is how to choose speeds that work across the board, on all asset classes and their markets, and how much the choice is worth once it is judged on years it never saw. The plan was fixed before any result was computed, and every change made after seeing results is dated and labelled ([results/hypotheses.md](results/hypotheses.md)).

## 1. Speeds that work across the board

The lecture's result fits in one chart.

![Trend speeds across the board](figures/26_key.png)
<sub><b>How to read the figure.</b> <b>Axes.</b> Left: twelve trend speeds from two weeks to two years (x, trading days) against the share of 500 random halves of years and markets in which each speed works on both halves (y), one line per trend rule, at the end-2025 review. Shaded: 61 to 179 days; dotted: the bar of 20% above which a speed is held. Right: Sharpe ratio after costs, out of sample 2013-2026 (x), per asset class and in total (y), for the rule (black diamonds), speeds chosen separately for each class (orange) and all 36 streams held equally (grey squares). Excess returns over cash, 5 bp per trade; our calculation.</sub>

Speeds of two to five weeks almost never pass: they trade too often for what they earn. Speeds of three to nine months (61 to 179 days) pass in most random halves, for all three rules. Beyond a year the pass share falls but does not vanish, and the rule keeps a stake there. Chosen each year on past data only, the speeds that pass did better the following years than holding all 36 (Sharpe ratio 0.49 against 0.32 over 2013-2026), mostly by leaving out the fast speeds; choosing separately for each asset class did not do better than one set for all (0.46).

| § | Step | Question |
|---|---|---|
| 2 | Overfitting, carefully | What can be guarded against in advance, and what cannot? |
| 3 | The streams | Which rules, which speeds, which returns and costs? |
| 4 | The rule | How do random halves of years and markets choose speeds? |
| 5 | The areas | Which speeds pass, class by class, and do they stay? |
| 6 | Two examples | Markets that disagree; super-long speeds in US equity |
| 7 | Out of sample | Does the rule beat holding everything, or choosing per class? |

This lecture is step 2 of the workflow of Lecture 25 (§1): it uses strategy performance, but only in sample, to choose a region of speeds rather than a point, and it is judged out of sample.

## 2. Overfitting, carefully

"Overfitting" is easy to say and hard to define in advance. A choice is overfitted only if the future differs from the past in a way that makes it fail, and we do not know how the future will differ. Two different things hide behind the word, and only one of them can be measured beforehand.

| | What it is | Measurable in advance? | What we do about it |
|---|---|---|---|
| **Dependence on the sample** | The choice reflects the particular history we happened to see: one crash, one market's luck. An equally likely history would have given a different choice | Yes: rerun the choice on other slices of the same past and see whether it holds | Keep only what holds on most slices (§4) |
| **A future unlike the past** | The structure changes: interest-rate regimes, who trades, how crowded a speed is. Even a choice that is stable in the past can fail | No | Prefer choices with a mechanism; review every year; keep a stake in scenarios the past does not favour (§6); judge the result out of sample (§7) |

Seen this way, choosing the best speed for each market is the extreme case of the first kind: each choice rests on one market's history, the least evidence there is. One set of speeds for a whole asset class rests on all its markets, one set for all classes on all of them. The defences against the first kind follow from that:

| Defence | In this lecture |
|---|---|
| Few free choices, much evidence behind each | One set of speeds for all markets, each asset class with the same vote |
| Robust across markets | A speed must work across the markets of a random half, not on one market |
| Robust across periods | It must also work on random halves of the years |
| Regions, not points | Every speed that passes often enough is held, not the single best |
| Out of sample | Chosen each year on past data only, judged on the years after |

These are not new ideas. The classic studies of trend following apply one rule to every market: Moskowitz, Ooi and Pedersen (2012) use the same 12-month lookback for 58 futures, and Hurst, Ooi and Pedersen (2017) combine 1-, 3- and 12-month trends with equal weights across 67 markets since 1880. Choosing what is kept on many random halves of the data is the idea of stability selection (Meinshausen and Bühlmann, 2010), whose authors note that the result varies "surprisingly little" with the cut-off.

## 3. The streams

### 3.1 Speeds and rules

**Speeds.** Twelve horizons from two weeks to two years, each about 1.4 times (the square root of 2) the one before: 11, 17, 23, 31, 43, 61, 89, 127, 179, 251, 359 and 503 trading days. Each is a prime number. Two reasons:

- Rules that look back over a fixed window, such as a past return or a breakout, are blind to cycles of exactly their length and its fractions. Two windows of which one is a multiple of the other share those blind spots; two primes share none.
- Many traders use round lookbacks (20, 50, 100, 200 days) and calendar lengths (21, 63, 252). A rule on 197 or 251 days changes its position on different days than the crowd's, which matters for execution (Lecture 24 showed how predictable orders get picked off).

What makes two speeds different is mainly their ratio, not their divisibility: 59 and 61 are both prime and almost the same rule. So the grid is spaced by ratio first and made of primes second.

**Rules.** Three trend rules from Lecture 6, each taking a position of +1 (long) or −1 (short) at the close of each day, computed with `trading_models`:

| Rule | At speed h |
|---|---|
| EWMA crossover | Sign of the exponential average of the log price with span h/4 minus that with span h |
| Breakout | Long after a new h-day high, short after a new h-day low, flat after crossing back over the h/2-day channel (the Turtle rule) |
| Past return | Sign of the h-day return |

Three rules at twelve speeds give **36 streams** for each market.

### 3.2 Positions, returns and costs

| Step | Rule | Why |
|---|---|---|
| Position | The rule's sign times 10% divided by the market's yearly volatility over the past six months (an exponential average of squared daily returns, span 126 days) | Each market carries about the same risk (Lecture 9); six months matches positions held for months, where a short window would lever quiet markets up in calm spells (§7) |
| Trading | Each day, close a tenth of the gap between the position and its target (Lecture 9) | Cuts turnover without giving up the signal |
| Return | The position times the market's return **over cash**: the fund's total return less the 3-month Treasury bill rate | What a trend position adds, as a futures position earns |
| Cost | 5 bp of the value traded on every trade | Liquid funds trade at spreads of a fraction of a basis point; 5 bp allows for thinner funds and some impact (10 and 20 bp are reported) |

**Why returns over cash.** The funds' prices are total returns: interest, coupons and dividends are reinvested. A trend follower's positions are often levered (a calm bond fund is held at several times its value to reach a 10% volatility) and often short. Written for the whole account, with $`w_i`$ the position in fund $`i`$ and $`r_f`$ the cash rate:

```math
r_{\text{account}} = \sum_i w_i\,\mathrm{TR}_i + r_f\Big(1 - \sum_i w_i\Big) = r_f + \sum_i w_i\,(\mathrm{TR}_i - r_f)
```

Unused capital and the proceeds of short sales earn the cash rate; borrowed money for positions beyond the capital costs it. The account therefore earns the cash rate once, plus each position times its return over cash, and the second part is what separates one speed from another. Measured on total returns instead, a levered bond position collects interest on money it never paid for: at 89 days the government bond streams' Sharpe ratio is 0.60 on total returns and 0.28 over cash, credit's 0.52 and 0.34 (our calculation, all funds of the class with equal risk, 2007-2026). Real borrowing costs a little more than the bill rate and shorting a fund carries a fee; both bite only on leverage beyond the capital and are left to the lecture on constraints and costs.

**Example: why fast speeds fail.** On IEF (Treasuries of 7 to 10 years), the fastest EWMA crossover (11 days) earned a Sharpe ratio of 0.32 before costs over 2007-2026, as much as the slow speeds (0.30 at 89 days, 0.31 at 251); it traded so often that costs of 5 bp took 1.5% a year and left 0.08. The 89- and 251-day crossovers paid 0.5% and 0.2% a year and kept 0.25 and 0.29. The fast speeds' failure here is a matter of cost, not of an absence of trend (our calculation, returns over cash).
