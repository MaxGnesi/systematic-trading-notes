# Lecture 6: Trend Following: the Map and the Machinery

*Systematic Trading: Lecture Notes (MSc) · Oct 18, 2026 · Max Gnesi*

The same market can be traded for different purposes: to collect its drift, to protect against its crashes, or both. Lecture 5 showed what a market makes available to a trend rule; this lecture shows that what a system captures is decided by its design, draws the map of trend rules, and builds the machinery that turns any rule into positions. *Draft: the map is written; the design choices and the machinery follow.*

## 1. The map: three families, two dimensions, four design choices

Trend models appear countless, but they come from three families with distinct literatures. A second dimension says whether an asset is compared with its own past or with other assets, and four design choices explain how members of the same family differ.

### 1.1 Three families of trend signals

| Family | How the signal is built | Members | Literature | Sees | Misses |
|---|---|---|---|---|---|
| **1. Linear filters** | A weighted average of past prices or returns | Moving averages and crossovers, MACD, time-series momentum, EWMAC, the Hodrick–Prescott filter, the Kalman filter once its gains have settled | Econometric trend filtering (Bruder et al., 2011; Levine and Pedersen, 2016) | A smooth, continuous reading of direction | Turning points arrive late; choppy markets cause whipsaws |
| **2. Price-extreme rules** | Running highs and lows: the signal changes when price crosses a level set by its own recent path | Filter rules, support and resistance, channel breakouts (Donchian, the Turtle rules), trailing stops | Technical analysis tested academically (Alexander, 1961; Brock, Lakonishok and LeBaron, 1992; Sullivan, Timmermann and White, 1999) | The moment price escapes its recent range, and how far it has come back from its peak | The signal is on or off, so noise near the level triggers false entries and stop-outs |
| **3. Nonlinear and model-based filters** | A statistical model of the trend that is not a fixed weighted average | L1 filtering, wavelets, nonparametric regression, regime switching, machine learning | Nonlinear filtering (Bruder et al., 2011); regime switching (Hamilton, 1989) | Breaks in the trend, changes of regime, the uncertainty of the estimate | Results depend on the model and its calibration; the more flexible the model, the greater the risk of overfitting |

Two links between the families matter later.

- **The Kalman filter sits on the boundary.** Bruder et al. show that, once its gains have settled, the Kalman filter is an exponential moving average, as Lecture 4 found for the level. Its level and slope therefore belong to the linear family; what it adds beyond that, the uncertainty and the surprises, is model-based.
- **Breakouts and stops share one building block.** A Donchian breakout enters when price reaches its highest high of the last $`N`$ bars; a chandelier stop exits when price falls a fixed multiple of ATR below that same high. One rule acts at the extreme, the other at a distance from it.

### 1.2 The second dimension: own past or other assets

Each family can be used in two ways. A **time-series** rule compares an asset with its own past and decides whether to be long or short that asset; a **cross-sectional** rule ranks assets against each other and decides which to prefer.

| | Time-series: each asset against its own past | Cross-sectional: assets ranked against each other |
|---|---|---|
| Linear filters | Time-series momentum, EWMAC per asset | Relative-strength momentum: buy past winners, sell past losers (Jegadeesh and Titman, 1993) |
| Price-extreme rules | A breakout or a stop per asset | Rank assets by their distance from the channel high |
| Nonlinear and model-based | A regime or a slope estimate per asset | Rank assets by estimated slope or by the strength of the evidence for a trend |

The two answer different questions. A time-series portfolio can be long everything in a broad rally and short everything in a crash, so its net exposure varies; a cross-sectional portfolio is long some assets and short others, usually with no net exposure. Goyal and Jegadeesh (2018) find that across international asset classes, cross-sectional strategies scaled the same way as time-series ones performed better. Lectures 7 and 8 build time-series systems asset by asset; cross-sectional rules come with the portfolio, in the last lecture of Part II.

### 1.3 Modifiers: filters, overlays and hybrids

Some tools do not produce a trend signal; they act on one.

- **Filters and overlays** decide whether a signal is traded: trend strength (ADX and the efficiency ratio of Lecture 3), the volatility regime, or a regime model.
- **Hybrids** combine the trend with another idea, such as entering on a pullback within an uptrend, using the stretch of Lecture 4.

A filter is a second signal. It removes some losing trades and also some winning ones, so it has to be tested like a signal, which Lecture 10 does.

### 1.4 Four design choices

Within each family, rules differ along four choices. Each option sees something and misses something.

| Choice | Option | Sees | Misses |
|---|---|---|---|
| What the rule reads | Closes | Net moves, with the overnight gap | The path within each bar |
| | Highs and lows | Where price escaped its range | Sensitive to a single extreme print |
| | A model's estimate | The trend together with its uncertainty | Only as good as the model |
| Signal shape | Continuous | Position scales with the strength of the trend; small changes trade little | Rarely fully out of the market |
| | On or off | Simple and unambiguous | Trades the full position on noise near the threshold |
| What ends a trade | The signal reversing | Symmetric; no extra parameter | Gives back much of a gain before reversing |
| | A stop | Limits the giveback | Hit by noise; the result depends on the path |
| Horizon | Short | Turns early | More trades, more cost, more false signals |
| | Long | Fewer trades; more robust to noise | Late at turning points; larger giveback |

These choices, not the names of the rules, decide how two systems differ. Two rules that make the same four choices behave alike, whatever they are called; §1.5 measures how alike.

### 1.5 Why a few representatives suffice

*To follow, with the notebook:* every linear filter is a set of weights on past returns (Levine and Pedersen, 2016), illustrated by working a crossover into its weights by hand; then the measured overlap of the families' positions and returns on a common universe of assets.

### 1.6 Where each part of the map is taught

| Part of the map | Where |
|---|---|
| Linear filters and model-based estimates, as continuous forecasts | Lecture 7 |
| Price-extreme rules: breakouts and stops | Lecture 8 |
| Measuring performance | Lecture 9 |
| Modifiers: filters, overlays, regime models, hybrids | Lecture 10 |
| Cross-sectional rules and the trend portfolio | Lecture 11 |
| Trends on bars cut by price (point-and-figure, Renko) | Part III |
| Machine learning | After Part V, once honest testing is in place |

Lecture numbers after 6 are planned and may change as the roadmap is settled.

**Watch out for** comparing rules by name. A breakout and a crossover at the same horizon can be closer to each other than two crossovers at different horizons; compare the design choices, then measure.

## References (so far)

- Alexander, S. (1961). Price movements in speculative markets: trends or random walks. *Industrial Management Review* 2, 7–26. — filter rules (§1.1).
- Brock, W., Lakonishok, J. and LeBaron, B. (1992). Simple technical trading rules and the stochastic properties of stock returns. *Journal of Finance* 47(5), 1731–1764. — moving-average and trading-range-break rules (§1.1).
- Bruder, B., Dao, T.-L., Richard, J.-C. and Roncalli, T. (2011). *Trend Filtering Methods for Momentum Strategies.* Lyxor White Paper. — linear and nonlinear filtering, the Kalman filter as an exponential moving average (§1.1).
- Goyal, A. and Jegadeesh, N. (2018). Cross-sectional and time-series tests of return predictability: what is the difference? *Review of Financial Studies* 31(5), 1784–1824. — time-series against cross-sectional (§1.2).
- Hamilton, J. (1989). A new approach to the economic analysis of nonstationary time series and the business cycle. *Econometrica* 57(2), 357–384. — regime switching (§1.1).
- Jegadeesh, N. and Titman, S. (1993). Returns to buying winners and selling losers: implications for stock market efficiency. *Journal of Finance* 48(1), 65–91. — cross-sectional momentum (§1.2).
- Levine, A. and Pedersen, L.H. (2016). Which trend is your friend? *Financial Analysts Journal* 72(3), 51–66. — linear trend rules as equivalent representations (§1.1, §1.5).
- Sullivan, R., Timmermann, A. and White, H. (1999). Data-snooping, technical trading rule performance, and the bootstrap. *Journal of Finance* 54(5), 1647–1691. — technical rules tested with an adjustment for data snooping (§1.1).
