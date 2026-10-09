# Systematic Trading Notes

Lecture notes on systematic trading (MSc-level): the pipeline from data to execution, strategy
families, research pitfalls, and a worked case study.

## Lectures

| # | Title | Markdown | Original |
|---|---|---|---|
| 1 | Introduction: definitions, the systematic pipeline, data, strategy styles, research pitfalls, a worked trend-following case study | [lecture-01-introduction.md](lectures/lecture-01-introduction.md) | [lecture-01-introduction.docx](lectures/lecture-01-introduction.docx) |
| 2 | OHLCV and price aggregation: what a bar is, seven single-bar price constructions, a taxonomy of weighting schemes (SMA, EMA/EWMA, VWAP, KAMA), why the Kalman filter is a different kind of estimator, and a worked numeric example | [lecture-02-ohlcv-and-aggregation.md](lectures/lecture-02-ohlcv-and-aggregation.md) | — |
| 3 | Other aggregation targets: volatility (ATR), trend strength (efficiency ratio, ADX), flow (OBV), relationship between series (rolling correlation and beta), and distribution shape (rolling skew/kurtosis) — one shared worked dataset throughout | [lecture-03-other-aggregation-targets.md](lectures/lecture-03-other-aggregation-targets.md) | — |

Each lecture is kept in both forms where a source Word document exists: a Markdown version for
reading on GitHub (headings, tables and equations render inline), and the original file for anyone
who wants it.

## Notebooks

Lectures 2 and 3's claims verified against real market data, not the lectures' constructed
examples. Each notebook was executed before committing, so its charts and tables are visible
directly on GitHub without running anything.

| # | Title | Notebook | Lecture |
|---|---|---|---|
| 11 | Price-level aggregation on QQQ: the seven price constructions and SMA/EMA/VWAP/KAMA/Kalman, read through the August 2015 flash-crash day | [notebooks/11_price_aggregation_methods.ipynb](notebooks/11_price_aggregation_methods.ipynb) | [Lecture 2](lectures/lecture-02-ohlcv-and-aggregation.md) |
| 12 | Other aggregation targets on QQQ and GLD: ATR, efficiency ratio and ADX, on-balance volume, rolling correlation/beta, rolling skew/kurtosis | [notebooks/12_other_aggregation_targets.ipynb](notebooks/12_other_aggregation_targets.ipynb) | [Lecture 3](lectures/lecture-03-other-aggregation-targets.md) |

`trading_models/` is the minimal subset of a larger private research project needed to run these
two notebooks specifically (traced by import, not hand-picked) — not the full project, which also
covers portfolio construction, covariance estimation and a broader trend-following platform.
Where a technique already has a tested implementation there (Kaufman's Adaptive Moving Average,
the Kalman filter, Wilder's ATR/ADX/efficiency ratio), the notebooks import it directly rather
than reimplementing it; only on-balance volume and rolling correlation/beta, which don't exist in
the package, are computed locally in the notebooks themselves.

### Running them yourself

```bash
python -m venv .venv
.venv\Scripts\activate          # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
pip install -e .
jupyter lab notebooks/
```

No price data is bundled in this repository: both notebooks fetch QQQ and GLD daily bars live
from Yahoo Finance on first run (via `yfinance`) and cache them locally under `data/raw/`, which
is git-ignored. This is a deliberate choice, not an oversight — Yahoo Finance's terms generally
restrict redistributing its data, so re-running the notebooks is the way to get it, not pulling it
from this repository.
