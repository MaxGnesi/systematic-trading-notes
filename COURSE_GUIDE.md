# Course Guide: Roadmap, Style and Formula Conventions

The working reference for writing and revising these lecture notes. Read it before editing any lecture, so every lecture looks and reads the same.

## 0. The course structure (design, 2026-11-16)

The course teaches **the base layer of systematic research** first, then **a deep dive into high frequency**. The base layer is built once, in order: understand the data, build the base strategy (trend), add strategies that earn for different reasons (carry, value, with regimes as the alternative that failed), assemble the portfolio and set a realistic expectation. The deep dive then goes below the daily bar, where costs and short-horizon edges are decided, and points back to the portfolio's execution.

| Part | Lectures | Purpose | Leads to the next part because |
|---|---|---|---|
| I. Foundations | 1-4 | What is in the data; what different transformations of the same prices show; the research method | A strategy is only as good as its understanding of the data |
| II. Trend | 5-13 | The base strategy, built once: what trend captures, the machinery, comparing, filtering and sizing systems, the futures test, then trend at portfolio scale (markets, speeds, the baseline portfolio) | Trend alone is one source of return; the next question is what else earns, and when |
| III. Beyond trend | 14-15 | Two answers to trend's bad regimes: switching trend off (promising leads, none yet a rule), or holding strategies that earn for different reasons (carry adds; value needs fundamentals) | The parts are ready to be assembled |
| IV. The portfolio | 16-17 | The base layer assembled: trend and carry, tested on untouched years, judged as an addition to stocks and bonds; the realistic expectation; how to improve on a fixed base (16). Research with AI: what an AI assistant speeds up, where it fails silently, and the guardrails that kept this course honest, with the course's own record as the case study (17) | The base layer is complete; what remains is below the bar |
| V. Deep dive: high frequency | 18-24 | The tape (18-20) and the order book (21-23) on crypto, the one market with free tick and book data, then a live trend bot (24): clocks, the path, order flow, costs, queues, other traders, market making | Back to Part IV: the execution of a daily portfolio, and where finer granularity adds breadth |

**Renumbering (old → new).** 1-9 unchanged; 11 → 10 (Lecture 10 was merged into 11 and its number is freed); 25 → 11, 26 → 12, 27 → 13; 28 → 14, 29 → 15, 30 → 16; a new Lecture 17 (research with AI); 12-24 → 18-30. Folders and notebooks are renamed to the new numbers; **script file names keep their original numbers** (`l25.py`, `l28_filters.py`, ...) as internal code names, since they are imported across lectures and name local result folders.

**What changes in the text, beyond the numbers.**
- Part II's last three lectures (11-13) open as *trend at portfolio scale*, the natural continuation of Lectures 5-10, not as a restart after the high-frequency part.
- Lectures 14-16 lose their "after the high-frequency part" framing; forward references to execution point to Part V.
- **The pipeline is the map (2026-11-16, user).** Lecture 1 §2.1's five stages (data, signals, allocation, risk, execution, plus the feedback loop) locate every lecture: a stage line under each title, a stage table in Lecture 1, part openings naming their stages, and Lecture 16 assembling the portfolio stage by stage. Combining strategies is allocation and risk management, not a new signal.
- **Part V links back to the base layer (2026-11-16, user).** Each condensed Part V lecture ends with a short box, *Back to the base layer*, labelled food for thought: how its method could combine with what Lectures 1-16 built, without a worked example or a test. Examples: intraday trend as another arrow next to slow trend, diversifying into a faster horizon (breadth, Lecture 1 §5.4); reading the book to optimise execution, or as a kill switch that pauses a strategy when liquidity or flow turns against it; market making as an overlay on any strategy (earning the spread on its own rebalancing); microstructure as a source of new anomalies. Developing these is beyond this cycle of lectures; they are open research directions.
  *Format, fixed so the topic cannot grow:* one card per condensed lecture, four rows: **the idea** (one sentence); **what our results already say** (only numbers the lecture has shown, for or against); **what a test would need** (data, design, the first thing that could kill it); **status** (not tested in this course). About five lines, nothing new computed; at most six cards in Part V plus one collecting table in the capstone; anything deeper becomes an exercise. Grounding already in hand: intraday trend works at spans of days, not minutes (Lecture 20); the first warning of a tipping point is in the tail of costs (Lecture 22, a kill-switch candidate); a maker loses about 0.8 bp within the first second after a fill, so a market-making overlay is hard and passive rebalancing is the realistic version (Lecture 23); flow keeps almost all its impact (Lecture 19), the cost an anomaly must clear.
- **What Part V is for, practically (2026-11-16, user):** a first hands-on with tick and order-book data, to become familiar with analysing them; and a tool to check execution quality: compare each fill with the book and the tape at the moment of the order (slippage against the arrival price, implementation shortfall), so a live strategy can verify that its implementation trades as the backtest assumed.
- Part V opens as an advanced deep dive that builds on the base layer, and closes by pointing its execution lessons back to Lecture 16.
- Lecture 16 adds the cost link: the base layer judged with execution costs measured in Part V, not only a flat 5 bp.
- Each part opens with a short paragraph: what it asks, and how it leads to the next.
- **Research with AI, in two places** (user, 2026-11-16: leveraging AI is crucial for researchers today). Lecture 1 gains a short practical section, *working with an AI assistant in this course*: what to delegate and what not (the question, the expectation, the judgment), how to brief an assistant, and a guardrails checklist (plan fixed and dated first, every try logged, hand checks, data provenance, references checked at the source). Lecture 17 is the full lecture at the end of the base layer, a practical guide with the course's own record as the case study: what to delegate, how to brief, speed with discipline (cheap tries must still count), verification habits, where an assistant failed here (a silent data error, a confident wrong claim, invented reference details, first proposals the researcher corrected), and the workflow to copy.
- **Adapting on findings, with discipline** (user, 2026-11-16), a principle of both: adjusting a strategy because of what the research found is not a fault; it is how AI-assisted research is leveraged. The discipline is in how each change is judged: **cost against benefit** (complexity, one more try, turnover and trading cost, against a measured gain) and **robustness** (a plateau rather than a peak, other periods and markets, a mechanism). Lecture 15 is the worked example: changes kept (bonds across countries, value from fundamentals, the carry score) and changes dropped (the best grid rows combined, the value tilt, the hedge), each with its evidence.
- The README states how the notes were made (written with an AI assistant, under the author's direction and review).
- **What Part V is** (user, 2026-11-16): high frequency on bitcoin sets the stage for the analysis one should also do on traditional markets (clocks, the path, order flow, queues, costs); crypto is used because it is the one market with free tick and order-book data at that depth. Part V is an example and the beginning of a direction, not a complete treatment; its opening says so.
- **Part V condensed** (user, 2026-11-16: thirteen lectures on one market's high frequency stretch the course too much). After the renumbering, Part V becomes about six lectures merged by theme: the tape and its clocks (18-19); the path, order flow and costs (20-21); two strategies on the tape (22-23); the order book (24-26); replaying a market that reacts (27-28); who trades, and making markets (29-30). The full current lectures stay in the repository as an extended version, linked from each condensed lecture. Written one condensed lecture at a time, as its own step after the restructure; the course then has about 23 lectures.
- **Part V's capstone: a trend bot, live** (user, 2026-11-16, replacing the parked note). It is Lecture 24, the last of the course, built together at the end (user, 2026-11-16). Market making stays in the condensed Part V as *understanding the other side* (who provides liquidity, why your costs are what they are), merged with trading styles; the capstone runs the base layer's trend rule automatically, from backtest to production (data feeds, scheduling, order handling with Part V's execution lessons, monitoring, failures, live against backtest), on an exchange testnet or paper trading (free), a small cloud server optional.

## 1. Roadmap

The course follows one pipeline throughout (data → signal → position → evaluation). What changes from part to part is **what counts as one observation**: a daily bar, a trade or quote, a probability. Each part opens with a short "what is the data here?" lecture and then goes straight to models. Each strategy lecture ends with a short *How we judge it* section that flags the evaluation problems specific to that data and points forward to the portfolio lectures (11-16).

| Part | # | Lecture | Core idea | Notebooks / data | Status |
|---|---|---|---|---|---|
| I. Foundations | 1 | Introduction to Systematic Trading | The pipeline; bias moves into research; strategy families as examples | — | Done |
| | 2 | OHLCV and Price Smoothing | A bar is compression; averaging is filtering; compare at equal memory | 11 (QQQ) | Done |
| | 3 | Same Bars, Different Questions: Volatility, Flow, Correlation and Tails | Same data, different transformations | 12 (SPY, QQQ, GLD, AGG) | Done |
| | 4 | Tracking Hidden States: the Kalman Filter | Top-down filtering: model the hidden level, slope and acceleration and update them bar by bar; Q and R; adaptive noise; extended and unscented filters | 13 (SPY, QQQ, GLD, AGG) | Written; Kalman material still to be removed from Lecture 2 |
| II. Trend | 5 | What Trend Following Captures | Drift and timing; what a market offers (drift, frictions, cascades, maturity, intervention); what to capture | 05 (16 ETFs) | Done |
| | 6 | Trend Following: Map and Machinery | Three families, five design choices, time series or cross-sectional; signal to forecast to position; eleven model cards | 06 (16 ETFs, QQQ) | Done |
| | 7 | Comparing Trend Systems | Equal speed, what a system adds, trades and sides, Omega and drawdowns, is it real, will it last | 07 (16 ETFs) | Done |
| | 8 | Filters and Overlays | Filter curves, attachment, random-filter yardstick, out of sample, calendar events | 08 (16 ETFs, FRED) | Done |
| | 9 | Sizing Trend Systems | Risk per asset, total risk over time, how much to trade; sizing uses only risk and cost information | 09 (16 ETFs) | Done |
| | 10 | Three Trend Systems, End to End (capstone) | Futures from Kaggle, rolls and back-adjustment, EWMAC, breakout, cross-sectional momentum, comparison, evaluation, filters, portfolio, out of sample | 11 (12 futures, 2 Treasury funds) | Done |
| | 11 | Choosing the markets | 116 US-listed ETFs, synchronous weekly closes; correlation, factors and noise; trend phases and trend strength; slots per class from the factor count; a score of representativeness, diversification and liquidity, ranked top to bottom, out of sample; a roadmap for growing capital | 25 (116 ETFs, Yahoo, free, 2007–2026) | Written |
| | 12 | Trend speeds that work across the board | Overfitting in two kinds; 36 streams (three rules, twelve prime speeds) on returns over cash; random halves of years and markets, each class the same vote; hold every speed passing in 20% of splits; per class against one set, out of sample | As Lecture 11, plus the 3-month bill rate (FRED, free) | Written |
| | 13 | The baseline trend portfolio | Equal risk at every level: blending the speeds (overlap by speed ratio, equal weights against correlation-, cost- and Sharpe-based weights, timing the speeds), markets and classes (capital against risk shares), scaling the total (volatility target against constant leverage); a take-profit per speed as an option; crisis speeds and stress scenarios; the yardstick every later lecture must beat | As Lecture 12; capstone futures 2000-2022 as an independent check | Written |
| III. Beyond trend | 14 | Regime filters: when to hold trend | Regime information as a **switch**: how to compare filtered trend with always-in (all days and while on, the square-root link, equal risk, random switching, alpha); macro filters (growth, inflation, the Fed; data as first published, the price of look-ahead) and market-state filters (volatility, correlation across markets, turning points, yield curve, dollar) turn the baseline trend portfolio off when the regime stands still; none passes the test fixed in advance; graded evidence, the strongest pattern against the plan (trend weaker after large dollar moves, repeated on 1990-2005); exploration of why (level and direction, quadrants, a check on 1990-2005); commodity curves as a per-class example | ETFs, capstone futures, FRED, Philadelphia Fed real-time data, free long series for 1990-2005 | Written |
| | 15 | Carry and value | The other two cross-asset styles next to trend (Asness, Moskowitz and Pedersen 2013; Koijen et al. 2018), rebuilt from free data across currencies, commodities, government bonds and equity indices of nine to fifteen countries, and checked against AQR's published factors (agreement 0.46-0.79; the check exposed two design flaws); carry from rate gaps, curves, term spreads and yields (the S&P's earnings yield), level and change, weighted by a score: 0.57 alone, trend 0.67 → 0.86 together, beats 1,000 random strategies, deflated Sharpe 0.90 after counting 21 tries, a crash-risk price in the tail, weak in 2013-2026, most of its profit where it agreed with trend; value: the price proxy lost, value from fundamentals (real yields, PPP, the yield gap, inventories) earned a little; refinements that did not add; evidence weighed, not passed | Capstone futures period; FRED, OECD, BIS, World Bank, central banks' yields, Shiller, EIA, USDA; MSCI country ETFs; AQR Data Library (a check) | Written |
| IV. The portfolio | 16 | The final portfolio | Trend and carry at equal risk on fixed rules, tested on untouched years (1990-2005: 1.11, all three expectations held, beats 1,000 random strategies) and judged as an addition to 60/40 (a 20-30% risk share lifts its Sharpe ratio by a quarter to a half); costs (carry's edge mostly gone at 20 bp), crashes and the period; the realistic number, about 0.6-0.7, comparable to long-only with near-zero correlation; where higher Sharpe ratios come from, and improving on a fixed base layer; closes the base layer | Lecture 14's 1990-2005 portfolio, Lecture 15's groups extended back (FRED, OECD, central banks, Shiller), capstone futures | Written |
| | 17 | Research with AI | What to delegate, the brief, the lock, verification habits; an audit of the course's own record: 18 errors reached a result, figure or text, all silent; the four that changed a rule or verdict were found after results and before publishing, three by the author's review | Plan files and git history of Lectures 1-16 (results/audit.csv) | Done |
| V. Deep dive: high frequency | 18 | The Tape and Its Clocks | The record of every trade and how to get, check and describe it; how trades form prices; what a candle loses; bars on the market's clocks (activity, information, price); imbalance bars made stable; seasonality: when, not which way | From E18, E19 | Draft |
| | 19 | Path, Flow and Costs | The path inside a bar, realised volatility and stop fills; order flow, its impact and what it costs; capacity | From E20, E21 | Draft |
| | 20 | Two Strategies on the Tape | A trend rule on three clocks and an intraday grid: what each takes from the tape, and what each earns after costs | From E22, E23 | Draft |
| | 21 | The Order Book | What the book shows and how to rebuild it; statistics of the book and of the flow: imbalance, microprice, queues, impact, the book's clock | From E24, E25, E26 | Planned |
| | 22 | Replay and a Market That Reacts | Our own orders in the recorded market: fill rules, queue position, latency, adverse fills; how the market answers our order, and the tipping point | From E27, E28 | Planned |
| | 23 | Trading Styles and Market Making | Who else trades, read from public data; market making on one venue as a family of choices, and what it takes to break even | From E29, E30 | Planned |
| | 24 | Capstone: A Live Trend Bot | The base layer's trend rule run automatically from backtest to production on a free testnet or paper account; checking live fills against the tape and the backtest. Built together at the end of the course | Live testnet or paper account | Planned (built together at the end) |
| Extended | E18 | Tick data: the tape | Trade prints against OHLCV; the aggressor flag as true order flow; inspection; activity, price formation, what a candle loses | 12 (BTCUSDT perpetual, Binance archive, 2021–2026) | Done |
| | E19 | When the market trades: clocks and seasonality | Bars on the market's clock (tick, volume, dollar, imbalance, range, CUSUM); are returns closer to normal; the time of day, the week, round clock times, scheduled events | Binance (Lecture 18's tape) | Done |
| | E20 | How the price moves: volatility and the path | The path inside a bar (order, distance travelled, two regimes, crossings, excursions, stop fills); realised variance, jumps, each measure's interval, forecasting with honest yardsticks; risk on any clock, a duration measure | Binance | Done |
| | E21 | Who trades and what it costs: order flow, costs and capacity | One-sided flow and its reversal; sweeps and absorption; cascades (fuel and spark, risk clusters); fees, spread, impact and adverse selection; resting orders, misses, cut-off and re-posting; square-root impact, funding, capacity | Binance trades, best bid/ask (May 2023–March 2024), open interest, funding | Done |
| | E22 | Example 1: a trend rule on the tape, on three clocks | Decision, information and execution clocks; funding and the pure premium; the trend rule recalibrated on BTCUSDT; trend measures from dollar bars; risk in two parts, sizing by forecast risk; the patient entry; perpetual or spot; legs, capacity; the paired grid as bridge | Binance trades, dollar bars, premium index, funding, spot daily | Done |
| | E23 | Example 2: an intraday grid (capstone) | How a paired grid earns (round trips and inventory); on a price with no pattern it earns minus its gap; runs as jumps spread over minutes; five years of the tape against the same minutes shuffled; size profiles, width, exits and refresh; rules known in advance with the Benjamini–Hochberg correction; next to the trend rule; where grids pay (costs, rebates, strategies with an edge of their own) | 17 (BTCUSDT perpetual, Binance) | Done |
| | E24 | The order book | What an order book is; L1, L2 and L3; why book and trades are both needed; getting the data; reconstructing the book and checking it; what it shows: spread, depth, impact, refill, cancellations | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades | Done |
| | E25 | Statistics of the book: levels | The state at a moment: book imbalance, the microprice, queue dynamics, markouts of passive fills; liquidity before and in the 10 October cascade | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades | Done |
| | E26 | Statistics of the flow: deltas | Changes over an interval: order-flow imbalance, toxicity (VPIN and its critique), Hawkes processes, impact per unit of flow, lead and lag between venues; timing the news and the market's reaction | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades | Done |
| | E27 | Replaying the exchange | Our own orders in the recorded market, which does not react to them: the latency gap, queue position from aggregated books, adverse fills, order sizes and where the replay breaks; how conservative Lecture 23's fill rule was | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades | Done |
| | E28 | A market that reacts | How players behave alone and together, in calm markets, near a tipping point and in a cascade; a laboratory market of traders with known rules; a hybrid replay (the recorded book plus the measured reaction: impact, refill, triggered trading), tested out of sample; what it means for an algorithm and how to test one in calm and fast markets | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades; a simulated market | Done |
| | E29 | Trading styles | Footprints of slicers, trend followers, snipers and makers in public data; shares over time and circumstances; tested first where the answer is known | Bybit BTCUSDT perpetual, as Lecture 28; the simulated market of Lecture 28 | Done |
| | E30 | Market making on one venue | Avellaneda–Stoikov with extras, the grid at the best price and ping-pong quoting, steered by the signals of Lectures 25–26, in the replay and the simulation; every result split into what earned and what cost | Bybit BTCUSDT perpetual: L2 book (200 levels, 100 ms) and trades, 20 Sep – 3 Nov 2025 (the 10 October cascade); Binance trades | Done |
| | — | Cross-exchange market making | Quoting on Bybit and hedging on Binance | — | Not covered: the free archives do not hold both venues' books for our period ([order-book roadmap](lectures/ORDER_BOOK_ROADMAP.md)) |
| — | — | Allocation methods; constraints, capacity and trading | 1/N, inverse volatility, HRP, NCO; risk bands, caps, capacity, no-trade bands | — | Folded into Lecture 16 in brief (decided 15 November 2026): the course ends with the final portfolio |
| — | — | Prediction markets (Polymarket) | A price is a probability; calibration, Kelly on a bounded payoff | — | Not covered: replaced by the portfolio part (decided 13 November 2026) |

Threads to keep visible across parts:

- **Sizing comes back three times:** volatility targeting (Part II), inventory and spread limits (Part V), and the portfolio's weights and constraints (Lectures 11-16), which combine them.
- **The portfolio part keeps one workflow** (Lecture 11, §1): markets from market data only, weights from the risk of trend-positioned returns only, strategy profits only to evaluate, out of sample; any change after evaluation is dated and judged again.
- **Lecture 3 sets up Part V:** discrete sampling and bid-ask bounce (Lecture 3, §4.4) are the hook for "what is inside the bar".
- **Lecture 22 mirrors Lecture 3:** same data with different transformations, versus the same strategy on different data.
- **Two kinds of trend signal:** a positive-weight moving average always lags below price in a steady rise, while the Kalman level + slope extrapolates and can sit above price while the market still rises (QQQ illustration: above price on 43% of up-market days versus 23% for EMA(20); signals agree on 68% of days; naive rule returns correlate 0.37, one asset, one setting). In the three-state filter, acceleration also moves the level (forecast = level + slope + ½·acceleration), so it changes where the filter sits relative to price. Three signal sources to compare, each from a different mechanism: position (price versus the level of an EMA, the level + slope filter and the three-state filter), slope, and acceleration (early warning of regime change). Each state carries its own signal: position (price versus level), slope (direction), acceleration (strengthening or fading). Prototype on QQQ 1999–2026, models matched to EMA(20) on variance reduction: signals from the same state agree 78–91% (position) and 89% (slope), signals from different states only 45–75%, i.e. three distinct signal families (agreement, not performance). Lecture 4 explains the mechanisms; Part II tested it. On daily futures the Kalman slope trades like EWMAC at equal speed (daily returns correlate 0.93–0.95) and earns less, so Lecture 10 treats it as a variant of EWMAC (Lecture 4, §3: in steady state it is a linear filter).
- **The research checklist** (Lecture 1, §1.2) is applied in every *How we judge it* section.

Notebook numbers above were assigned from file names; check each notebook's contents before writing its lecture.

The order-book lectures' plot, for readers: [lectures/extended/ORDER_BOOK_ROADMAP.md](lectures/extended/ORDER_BOOK_ROADMAP.md). Update it when a Part V lecture is finished.

### 1.1 How Parts II and III are separated

**OHLCV is a summary format, not a type of bar.** Every bar has an open, high, low, close and volume, whatever decides when it ends. The parts differ in the **sampling rule**:

- **Part II: bars that close on the clock.** Daily, weekly or monthly OHLCV, the data available for decades. Daily is the main case; everything holds for weekly or monthly bars too.
- **Part V: changing the rule, or dropping bars.** Bars that close after a number of trades, an amount of volume or dollars, or an order-flow imbalance (still OHLCV, on a different clock); or the raw events themselves.

Strategy family and data frequency are separate choices: trend and stat arb run on daily bars, minute bars or alternative bars. The dividing line in Part V is whether a strategy needs **aggregated bars** (Lectures 19 and 22) or **individual events and the path between them** (Lectures 20, 21 and 23).

### 1.1a Before starting Part V

Part V is a step up: the data are billions of trades instead of a few thousand bars, and the statistics and the literature are those of market microstructure. What a reader needs:

| Need | Why | Where |
|---|---|---|
| Lectures 2 and 3 | What a bar compresses; order flow, volatility estimators and their biases, which Part V measures against the tape | Lecture 3, §4 and §7 |
| Lecture 7 | Comparing systems at equal speed, used again in Lecture 20 | Lecture 7 |
| Polars basics | Reading data larger than memory: lazy queries, streaming, chunks | Lecture 18, Appendix A |
| A computer with about 8 GB of free memory and 25 GB of disk | Five years of one market; every stage works in chunks and waits for free memory | Lecture 18, Appendix A.2 |

Each Part V lecture opens with a short *What to take away* box, and marks passages that can be skipped on a first reading.

### 1.1b Six uses of the tape: the spine of Part V

Part V is organised around what the tape adds to bars. Lectures 19 to 21 each cover two of the six uses; Lectures 22 and 23 apply them to two strategies, trend and an intraday grid. Each lecture names, in its first lines, which uses it covers, and each method lecture ends with *For the two examples*: what the trend rule and the grid take from it.

| The tape adds… | Used for | Strategy type | Lecture |
|---|---|---|---|
| 1. A clock: when trading happens | Bars on other clocks; signals that speed up with the market | Trend and any bar-based rule | 13 |
| 2. The path between bars | Which order filled first; stop or target first; the worst and best point in a trade | Mean reversion, grids, any rule with stops | 14 |
| 3. Volatility, measured precisely | Realised variance, jumps, forecasts; sizing; grid spacing; stop distances | All strategies | 14 |
| 4. Seasonality | When to trade: deep and thin hours, crowded round times, scheduled events (funding, data releases, expiries) | Execution of every strategy; timing of entries | 13 |
| 5. Order flow: who is pressing | Imbalance and its persistence; absorption; liquidation cascades; as a signal, or as a filter (stop a grid when one-sided selling keeps hitting it) | Short-term reversion; a regime switch for grids | 15 |
| 6. Costs and capacity | Spread on one's own side, slippage, impact growing with size, fees and funding; how large a strategy can get before costs eat it | Every strategy; deciding the trade size | 15 |

For a **trend system**, held for days, the tape gives a different clock and realistic costs (Lecture 20). For **mean reversion and the intraday grid**, held for minutes or hours, the **path** decides, and makes such strategies possible to test at all (Lecture 23). The same reference days recur in every lecture: the Fed decision of 21 September 2022, the quietest day (7 January 2023) and the flash crash of 17 August 2023.

### 1.2 Backtesting on bars that are not clock-time (for Lectures 22 and 23)

The strategy logic carries over to any bars, since each still has OHLCV. The backtest machinery changes in four places:

1. **When the bar is known to be finished.** A volume bar closes at the trade that crosses the threshold, at an irregular time; signals may use only closed bars, and the trade comes after that moment.
2. **The trade price.** Filling at the close of the signal bar is optimistic; use the next trade or quote after the bar closes, plus the spread. This needs the underlying ticks or quotes.
3. **Asynchronous assets.** Different assets' volume bars close at different moments; baskets and pairs need a common clock (clock-time snapshots or an event-driven backtest).
4. **P&L and risk in clock time.** Returns, volatility and drawdowns are reported per day, so positions are revalued at common times.

These four points form the *How we judge it* part of Lecture 22.

### 1.2a Risk measures on tick data (for Lecture 20)

Lecture 3, §11 promises that Part V returns to risk measures beyond clock-time bars. Two routes to cover:

- **Same measures on other bars**, with the three caveats from Lecture 3 §11: per-day and annualised figures assume equal time spans; correlation needs a common clock; returns in trade or volume time are closer to normal (Clark, 1973; Ané and Geman, 2000; contested by Murphy and Izzeldin, 2005).
- **Dedicated high-frequency estimators:** realised variance and its noise-robust versions (two-scale estimators, realised kernels), bipower variation for jumps, realised skewness and kurtosis, and correlation for asynchronous trading (the Epps effect; Hayashi–Yoshida). Candidate references, to verify before citing: Andersen, Bollerslev, Diebold and Labys (2003); Barndorff-Nielsen and Shephard (2004); Zhang, Mykland and Aït-Sahalia (2005); Barndorff-Nielsen, Hansen, Lunde and Shephard (2008); Amaya, Christoffersen, Jacobs and Vasquez (2015); Epps (1979); Hayashi and Yoshida (2005).

### 1.3 Folder and tab layout

- **GitHub:** lecture folders stay **flat** under `lectures/`, numbered globally (`01-…` to `15-…`), so links survive changes to the outline. The part is shown as a column in the README and in the roadmap above, not in the folder path.
- **Doc:** each part is a parent tab ("Part I: Foundations", "Part II: Clock-time bars: trend and relative value", …) holding a short paragraph on what the part covers and how it leads into the next, with its lectures as sub-tabs.

### 1.4 Lecture 4 plan (Kalman filter): design choices, charts, references

Status: written (doc and GitHub), companion notebook 04_tracking_hidden_states. Next: remove the Kalman material from Lecture 2 and re-run notebook 02 without it.

**Purpose of a trend filter.** Find structural, long-horizon trends that are robust to daily noise. No filter is best: each captures different behaviour, so filters are profiled (what each captures, in which market conditions, at what cost), not ranked. Predicting tomorrow's price is not the goal and one-step forecast error is not used.

**Models.** Local level (= EMA, the bridge from Lecture 2); local linear trend (level + slope, diagonal Q; the core); acceleration as a candidate early warning of regime change, judged on lead time versus false alarms. EKF/UKF in depth on hidden volatility from daily ranges ("transform first, use the UKF only when you cannot").

**Design versus tuning.** Design (which states) decides, for every setting, which motion is followed with no lasting gap (level only: flat; + slope: steady trend; + acceleration: parabolic) and whether jumps are overshot (positive weights never; any negative weight always). Tuning (the ratio of Q to R) only sets speed. Verified numerically at two settings; the table goes in Lecture 4 §5. No design is best; each is a bet about what the market is doing. Overshoot makes slope designs signal exits without a price fall (order: position, acceleration, slope): good at a real top, a false exit inside a continuing trend; in prototype tests only the level + slope model's slope signal held a continuing trend yet exited once the trend stopped.

**Extensions to evaluate, not assume:** a robust update for fat-tailed surprises; R per bar from the bar's range; a damped slope. Single-asset, single-setting prototype results on QQQ are preliminary only.

**Profiling framework (Lecture 4 §9 and its notebook).** Market conditions defined mechanically, across SPY, QQQ, GLD, AGG (and more) and a grid of settings; for each filter and signal family, describe its behaviour in each condition:

- Choppy, trendless (low efficiency ratio): how often it flips, how much it chases noise.
- Steady trend (high efficiency ratio): how far it lags, how stable its signal stays.
- Parabolic or accelerating move (rising slope, positive acceleration): whether it keeps up.
- Regime change (turning points defined in advance, e.g. 15–20% moves from a high or low): how early it turns, how often it warns falsely.
- Persistence: relation of each signal to returns over the next one to six months.

The result is a pros-and-cons profile per filter, not a winner. Whether combining filters with different profiles improves a trend system is tested in Part II, as complete strategies.

**Charts (appendix C, each linked from the text):**

| Chart | Content | Section |
|---|---|---|
| C.1 | Predict, compare, correct on the toy series | §1–2 |
| C.2 | Gain and uncertainty settling; same q/R ratio at two scales gives identical levels, wider bands | §2, §5 |
| C.3 | Weights on past prices: level-only filter = EMA; level + slope with negative weights | §2–3 |
| C.4 | A price jump: diagonal versus derived Q | §3 |
| C.5 | Three models matched on memory (level only, level + slope, level + slope + acceleration): position, slope and acceleration plotted separately, with one signal per state, QQQ 2021–2023 (prototype exists) | §4, §10 |
| C.6 | The dials: four noise settings shifting emphasis between level, slope and acceleration, QQQ 2020 (prototype exists); q/R against smoothness and tracking | §5 |
| C.7 | Warm-up: starting error with a diffuse versus a confident start | §6 |
| C.8 | The extensions (robust update, range-based R, damped slope) compared under the §9 criteria | §7 |
| C.9 | Normalised surprises against a normal curve; standard versus robust update on a spike | §7 |
| C.10 | Hidden volatility from daily ranges: linear filter on log range, EKF and UKF | §8 |
| C.11 | Case study: the 2000 top (parabolic rise, then violent counter-trend rallies to the October 2002 low); three designs, states and signals; check the three-state warm-up first (QQQ data start 10 March 1999) | §9 |
| C.12 | Case study: the 2020 V-shaped crash and recovery; three designs, states and signals | §9 |
| C.13 | A time-varying hedge ratio | §9 |

**References: status before citing.**

| Reference | Verified | Still to check |
|---|---|---|
| Alizadeh, Brandt and Diebold (2002), *Journal of Finance* 57(3), 1047–1091 | Log range approximately Gaussian, robust to microstructure noise; Gaussian quasi-ML for latent volatility | The exact state-space form in the estimation section |
| Chan (2013), *Algorithmic Trading: Winning Strategies and Their Rationale* | Kalman-filter hedge ratio on EWA/EWC | Chapter number (cite without it until checked); a replication found much weaker results (Sharpe 0.65 vs 2.4, different period) |
| Kalman (1960); Julier and Uhlmann (unscented filter); adaptive and robust filtering sources | — | All, before §1, §7 and §8 are written |

## 2. Where things live

| What | Where |
|---|---|
| Live, editable lectures | Claude Doc "Systematic Trading: Lecture Notes (MSc)", one tab per lecture: https://claude.ai/code/artifact/8533e7c8-f173-421f-9611-74c1d36f65fc |
| Published lectures | This repo: `lectures/NN-slug/lecture.md`, with the companion notebook and `figures/` in the same folder |
| Shared code | `trading_models/` at the repo root (installed with `pip install -e .`) |
| Price data | `data/raw/`, fetched on first run, never committed |
| Private research project | Local `New Trading Models/` (notebooks in `notebooks/`, lecture copies in `lectures/` linking to `../../notebooks/`) |

Every change goes to **both** the doc and the repo's `lecture.md`. Doc appendix links point to files on `master`.

## 3. Lecture structure

Every lecture uses the same skeleton:

1. **Title:** `# Lecture N: Short Descriptive Title`. Short, names the topics in plain words. A colon subtitle only in the README when the title alone is too thin.
2. **Byline:** `*Systematic Trading: Lecture Notes (MSc) · <date> · Max Gnesi*` (doc: date chip · author mention).
3. **Lead paragraph:** one or two sentences saying what the lecture covers and on which data, with a link to the companion notebook.
4. **Numbered sections** (`## 1.`, `### 1.1`). The first sentence of each section states its point or result.
5. **Worked examples in two steps:** a small toy example computed by hand, then the same method on a real date from the notebook, with the hand result matching the library value.
6. **Intuition paragraphs** start with a bold label: `**Example: driving on ice.**` One per major concept at most.
7. **A side-by-side comparison table** near the end (method × memory, inputs, what breaks it, common mistake).
8. **Summary, exercises and reading:**
   - `### N.1 Takeaways` as a numbered list.
   - `### N.2 Exercises` as a checklist (`- [ ]`): mix proofs, reproductions and "construct a case where it breaks".
   - `### N.3 Reading list`, ending with *References are given from memory and should be checked against the originals before circulation.*
9. **Appendix: charts:** PNGs from the notebook, each with a one-to-three-sentence caption, plus links to the notebook and lecture folder. Charts are lettered by lecture (Lecture 2: A.1…, Lecture 3: B.1…, Lecture 4: C.1…) and every chart is linked from the sentence that uses it ("chart C.4"). Three or four charts suit a lecture of familiar ideas; harder lectures use more, one or two per section (Lecture 4 plans thirteen).

Headings must match what follows them. A heading that promises "three" of something must be followed by three, and must not clash with nearby tables or lists.

## 4. Writing style

- Plain, specific, direct. Sentences under about 25 words; paragraphs of at most three sentences.
- British spelling (normalised, behaviour, optimised), as in the existing lectures.
- Numbers with units and real dates ("16 March 2020", "a 4.3% fall", "27-bar window"). Prefer a table to a list of numbers in prose.
- Name methods neutrally. Describe discretionary trading without loaded words: "a person can read the same data differently over time or bring in extra information", not "state of mind".
- Define a term the first time it is used; reuse the same term afterwards (e.g. *rolling*, *expanding*, *cumulative* memory).
- Cross-reference with section numbers: "Lecture 2, §6.3".
- No hype, no "key takeaways" boxes beyond the summary (except the short *What to take away* box that opens each Part V lecture, §1.1a), no repetition of a table's numbers in prose.
- **Cite at the point of the claim.** Put the reference in the sentence that uses it, e.g. "(Durbin and Koopman, 2012, ch. 5)", with a chapter when known, so a reader interested in one point can go straight to the source. Every inline citation also appears in the reading list, with a note on what it is used for (e.g. "— starting a Kalman filter (§9.1)").
- **Say what is ours.** Results derived or measured for these notes are labelled as such: "the calculation is ours", "our measurement for these notes". Such numbers must be reproducible in the companion notebook.
- **Justify specific examples.** When naming one tool, library, dataset or vendor out of many, say in a clause why that one (e.g. TA-Lib: the long-standing open-source reference implementation that documents the issue).
- **Name variables by meaning.** Prefer names a reader can connect to their role (*level*, *slope*, *surprise*, *q_level*) over bare letters; when a standard symbol is used, define it in words where it first appears.
- **Dose numeric examples.** Use a worked number where a concept is counterintuitive, muddy or easy to get wrong (e.g. "only the ratio q/R matters"); skip it where the formula already makes the point, since examples of the obvious tire the reader.
- **Give every variable a financial meaning.** In formulas, tables and matrices, explain each symbol in trading terms (level = the underlying price net of noise; q_level = genuine changes from news and revaluation; r_price = bid-ask bounce and temporary pressure; gain = the share of today's move believed). Prefer a step / calculation / financial-interpretation table over a block of equations side by side.
- **Tone.** Formal and precise, as in Lectures 2 and 3; analogies are kept short and stated soberly. Formal does not mean stiff: sentences flow, one idea each, with clear transitions; a plain word or short label ("dial for gaps", "trend projection") is used sporadically where it genuinely helps the reader picture an idea, never for its own sake.
- **Results like a paper.** Define every design and reading once, with short labels used consistently afterwards; define each experiment (data, setting, metric) before its results; number tables with captions that say what is measured; follow each table with one or two sentences on what to take from it.
- **No constant columns.** If every row of a table column has the same value, drop the column and state the fact once, with the reason.

## 5. Formula conventions

Formulas are written differently in the doc and on GitHub, because the two renderers differ. Both must look consistent across all lectures.

### 5.1 In the doc

| Use | Write |
|---|---|
| Display formula | A ```` ```latex ```` code block on its own line |
| Inline symbol or short expression | Plain text with Unicode sub/superscripts: pₜ, wₜ₋₁, mₖ, EMA₁₃, ATR₇, σ², x̄, (x − x̄)ᵏ, 10⁻⁴ |
| Subscript with no Unicode letter (b, c, d, f, g, q, w, y, capitals) | A readable fallback, used consistently: α(fast), α(slow), M(T), W(T), σ²(o), σ²(RS), σ(Δp); or words: "buy volume", "Return of A" |
| Long inline expression (fractions, sums with limits) | Move it into a display block |
| Operators | × not x, − (minus) not -, √, Σ, ∈, →, ≤ |

Inline TeX does not render in the doc: never leave `_` or `^` notation in running text.

### 5.2 On GitHub (lecture.md)

| Use | Write |
|---|---|
| Display formula | A ```` ```math ```` fenced block. Never `$$ … $$`, because Markdown eats backslashes such as `\!` and `\,` |
| Inline symbol or expression | ``$`…`$`` (dollar-backtick), in prose and in table cells: ``$`w_t`$``, ``$`\sigma_o^2`$``. The backticks stop Markdown from reading underscores as italics before the maths is parsed; plain `$…$` breaks on lines with several subscripts |
| Multi-letter names used as variables | `\mathrm{}`: `$\mathrm{ATR}_t$`, `$\mathrm{ER}_t$`, `$\mathrm{EMA}_{13}$`. As plain words in prose ("ATR keeps rising", "SMA(20)") they stay plain text |
| Absolute value in a table | `\lvert … \rvert`, never a raw `|` |
| Money | "USD 50,000", never a literal `$` |

Never use `\operatorname` (GitHub rejects it): write `\mathrm{sign}`. Avoid `\!`. Short purely numeric hand calculations ("513.1 / 5 = 102.62") may stay plain text; anything mixing symbols and numbers is math.

### 5.3 Shared notation

| Quantity | Symbol |
|---|---|
| Price, return, weight, signal | p, r, w, s; time subscript t; asset subscript i |
| Window length | N (rolling window), n (Wilder period or sample size) |
| Volatility, target volatility | σ, σ* |
| Smoothing constant | α = 2/(N+1) for EMA; α = 1/n for Wilder |
| Kalman (Lecture 4) | Named by meaning: states *level*, *slope*, *acceleration*; *q_level*, *q_slope*, *q_acceleration* (how much each may change per bar, the diagonal of Q); *r_price* (price noise, R); *uncertainty* (P); *gain* (K); *surprise* (price minus forecast). Symbols ℓ, τ only alongside the names |
| Moments | g₁, g₂ plain; G₁, G₂ bias-adjusted |

## 6. Figures and notebooks

- Notebooks are executed before committing. In the repo, Plotly outputs are replaced by the saved PNGs so charts render on GitHub.
- Each notebook writes its figures to its own lecture's `figures/` folder (`ROOT / "lectures" / "NN-slug" / "figures"`). Only PNGs are committed.
- Every formula in a lecture that has real-data numbers is checked in the notebook against the library on a real date.

## 7. Workflow and final checklist

Changes go on a branch, through a pull request, then are merged to `master`.

Before finishing any lecture edit:

- [ ] The same change is made in the doc and in `lecture.md`.
- [ ] Inline formulas follow §5 (doc: no `_`/`^` in text; GitHub: `$…$`, no `\operatorname`, no `$$`, no literal `$`).
- [ ] Headings match the content right below them.
- [ ] Title, byline, section numbering and summary block follow §3.
- [ ] Cross-links and doc appendix links point to the current folder names.
- [ ] New references are added to the reading list and flagged for checking.
