# Course Guide: Roadmap, Style and Formula Conventions

The working reference for writing and revising these lecture notes. Read it before editing any lecture, so every lecture looks and reads the same.

## 1. Roadmap

The course follows one pipeline throughout (data → signal → position → evaluation). What changes from part to part is **what counts as one observation**: a daily bar, a trade or quote, a probability. Each part opens with a short "what is the data here?" lecture and then goes straight to models. Each strategy lecture ends with a short *How we judge it* section that flags the evaluation problems specific to that data and points forward to Part V.

| Part | # | Lecture | Core idea | Notebooks / data | Status |
|---|---|---|---|---|---|
| I. Foundations | 1 | Introduction to Systematic Trading | The pipeline; bias moves into research; strategy families as examples | — | Done |
| | 2 | OHLCV and Moving Averages | A bar is compression; averaging is filtering; compare at equal memory | 11 (QQQ) | Done |
| | 3 | Same Bars, Different Questions: Volatility, Flow, Correlation and Tails | Same data, different transformations | 12 (SPY, QQQ, GLD, AGG) | Done |
| II. Clock-time bars: trend and relative value | 4 | Signal to position | Volatility targeting; scaling raw signals into sized positions | 09 | Planned |
| | 5 | Trend across asset classes | What works where, and who pays | 09, 10 | Planned |
| | 6 | Stat arb: from pairs to baskets | Relative value, hedge ratios, spreads; mirror image of trend | StatARB repo (check contents first) | Planned |
| III. From the tape to bars and back | 7 | The tape | Raw events: trades, quotes, order book updates; what a bar throws away | new | Planned |
| | 8 | Building bars from ticks | Time bars at any interval, plus tick, volume, dollar and imbalance bars (only possible with the ticks) | new | Planned |
| | 9 | Same strategies, intraday bars | Trend and stat arb on bars built in Lecture 8: still bar strategies, but costs, noise and the sampling rule change; backtesting on non-time bars (§1.2) | new | Planned |
| | 10 | Strategies that need the tape itself | Market making, queue position, cross-venue arbitrage, latency: the edge lives between the events a bar summarises | new | Planned |
| IV. Probabilities | 11 | Prediction markets | A price is a probability; bounded payoff; resolution | Polymarket | Planned |
| | 12 | Trading probabilities | Calibration, edge vs implied odds, Kelly sizing, domain models, news | Polymarket | Planned |
| V. Putting it together | 13 | Testing honestly across all three | Walk-forward, multiple testing, what a backtest can't say; the three data types side by side | 06 | Planned |
| | 14 | One portfolio of different strategies | Covariance and its noise, HRP, risk parity, combining strategies with different horizons and sizing rules | 02–05, 07, 08 | Planned |

Threads to keep visible across parts:

- **Sizing comes back three times:** volatility targeting (Part II), inventory and spread limits (Part III), Kelly on a bounded payoff (Part IV). Part V combines them.
- **Lecture 3 sets up Part III:** discrete sampling and bid-ask bounce (Lecture 3, §4.4) are the hook for "what is inside the bar".
- **Lecture 9 mirrors Lecture 3:** same data with different transformations, versus the same strategy on different data.
- **The research checklist** (Lecture 1, §1.2) is applied in every *How we judge it* section.

Notebook numbers above were assigned from file names; check each notebook's contents before writing its lecture.

### 1.1 How Parts II and III are separated

**OHLCV is a summary format, not a type of bar.** Every bar has an open, high, low, close and volume, whatever decides when it ends. The parts differ in the **sampling rule**:

- **Part II: bars that close on the clock.** Daily, weekly or monthly OHLCV, the data available for decades. Daily is the main case; everything holds for weekly or monthly bars too.
- **Part III: changing the rule, or dropping bars.** Bars that close after a number of trades, an amount of volume or dollars, or an order-flow imbalance (still OHLCV, on a different clock); or the raw events themselves.

Strategy family and data frequency are separate choices: trend and stat arb run on daily bars, minute bars or alternative bars. The dividing line in Part III is whether a strategy needs **aggregated bars** (Lectures 8–9) or **individual events** (Lecture 10). Lecture 9 says this in its opening: "these are bar strategies; the ticks only decide how the bars are cut."

### 1.2 Backtesting on bars that are not clock-time (for Lecture 9)

The strategy logic carries over to any bars, since each still has OHLCV. The backtest machinery changes in four places:

1. **When the bar is known to be finished.** A volume bar closes at the trade that crosses the threshold, at an irregular time; signals may use only closed bars, and the trade comes after that moment.
2. **The trade price.** Filling at the close of the signal bar is optimistic; use the next trade or quote after the bar closes, plus the spread. This needs the underlying ticks or quotes.
3. **Asynchronous assets.** Different assets' volume bars close at different moments; baskets and pairs need a common clock (clock-time snapshots or an event-driven backtest).
4. **P&L and risk in clock time.** Returns, volatility and drawdowns are reported per day, so positions are revalued at common times.

These four points form Lecture 9's *How we judge it* section.

### 1.2a Risk measures on tick data (for Lectures 8–9)

Lecture 3, §11 promises that Part III returns to risk measures beyond clock-time bars. Two routes to cover:

- **Same measures on other bars**, with the three caveats from Lecture 3 §11: per-day and annualised figures assume equal time spans; correlation needs a common clock; returns in trade or volume time are closer to normal (Clark, 1973; Ané and Geman, 2000; contested by Murphy and Izzeldin, 2005).
- **Dedicated high-frequency estimators:** realised variance and its noise-robust versions (two-scale estimators, realised kernels), bipower variation for jumps, realised skewness and kurtosis, and correlation for asynchronous trading (the Epps effect; Hayashi–Yoshida). Candidate references, to verify before citing: Andersen, Bollerslev, Diebold and Labys (2003); Barndorff-Nielsen and Shephard (2004); Zhang, Mykland and Aït-Sahalia (2005); Barndorff-Nielsen, Hansen, Lunde and Shephard (2008); Amaya, Christoffersen, Jacobs and Vasquez (2015); Epps (1979); Hayashi and Yoshida (2005).

### 1.3 Folder and tab layout

- **GitHub:** lecture folders stay **flat** under `lectures/`, numbered globally (`01-…` to `14-…`), so links survive changes to the outline. The part is shown as a column in the README and in the roadmap above, not in the folder path.
- **Doc:** each part is a parent tab ("Part I: Foundations", "Part II: Clock-time bars: trend and relative value", …) holding a short paragraph on what the part covers and how it leads into the next, with its lectures as sub-tabs.

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
9. **Appendix: main charts:** three or four PNGs from the notebook, each with a one-to-three-sentence caption, plus links to the notebook and lecture folder.

Headings must match what follows them. A heading that promises "three" of something must be followed by three, and must not clash with nearby tables or lists.

## 4. Writing style

- Plain, specific, direct. Sentences under about 25 words; paragraphs of at most three sentences.
- British spelling (normalised, behaviour, optimised), as in the existing lectures.
- Numbers with units and real dates ("16 March 2020", "a 4.3% fall", "27-bar window"). Prefer a table to a list of numbers in prose.
- Name methods neutrally. Describe discretionary trading without loaded words: "a person can read the same data differently over time or bring in extra information", not "state of mind".
- Define a term the first time it is used; reuse the same term afterwards (e.g. *rolling*, *expanding*, *cumulative* memory).
- Cross-reference with section numbers: "Lecture 2, §6.3".
- No hype, no "key takeaways" boxes beyond the summary, no repetition of a table's numbers in prose.
- **Cite at the point of the claim.** Put the reference in the sentence that uses it, e.g. "(Durbin and Koopman, 2012, ch. 5)", with a chapter when known, so a reader interested in one point can go straight to the source. Every inline citation also appears in the reading list, with a note on what it is used for (e.g. "— starting a Kalman filter (§9.1)").
- **Say what is ours.** Results derived or measured for these notes are labelled as such: "the calculation is ours", "our measurement for these notes". Such numbers must be reproducible in the companion notebook.
- **Justify specific examples.** When naming one tool, library, dataset or vendor out of many, say in a clause why that one (e.g. TA-Lib: the long-standing open-source reference implementation that documents the issue).
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
| Inline symbol or expression | `$…$`, in prose and in table cells: `$w_t$`, `$\sigma_o^2$`, `$\ln(C_t/C_{t-1})$` |
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
| Kalman | level ℓ, trend τ, noise variances Q (state) and R (observation) |
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
