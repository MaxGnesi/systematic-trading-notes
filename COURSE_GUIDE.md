# Course Guide: Roadmap, Style and Formula Conventions

The working reference for writing and revising these lecture notes. Read it before editing any lecture, so every lecture looks and reads the same.

## 1. Roadmap

The course follows one pipeline throughout (data → signal → position → evaluation). What changes from part to part is **what counts as one observation**: a daily bar, a trade or quote, a probability. Each part opens with a short "what is the data here?" lecture and then goes straight to models. Each strategy lecture ends with a short *How we judge it* section that flags the evaluation problems specific to that data and points forward to Part V.

| Part | # | Lecture | Core idea | Notebooks / data | Status |
|---|---|---|---|---|---|
| I. Foundations | 1 | Introduction to Systematic Trading | The pipeline; bias moves into research; strategy families as examples | — | Done |
| | 2 | OHLCV and Moving Averages | A bar is compression; averaging is filtering; compare at equal memory | 11 (QQQ) | Done |
| | 3 | Same Bars, Different Questions: Volatility, Flow, Correlation and Tails | Same data, different transformations | 12 (SPY, QQQ, GLD, AGG) | Done |
| II. Daily bars | 4 | Signal to position | Volatility targeting; scaling raw signals into sized positions | 09 | Planned |
| | 5 | Trend across asset classes | What works where, and who pays | 09, 10 | Planned |
| | 6 | Stat arb: from pairs to baskets | Relative value, hedge ratios, spreads; mirror image of trend | StatARB repo (check contents first) | Planned |
| III. Tick data | 7 | The tape | Trades, quotes, the order book; what bars hide | new | Planned |
| | 8 | Other ways to cut time | Tick, volume, dollar and imbalance bars | new | Planned |
| | 9 | Same strategies, faster data | Trend and stat arb intraday: costs, noise, alternative bars, who is on the other side | new | Planned |
| | 10 | Strategies that only exist inside the bar | Market making, cross-venue arbitrage, latency | new | Planned |
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
