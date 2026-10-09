# Systematic Trading Notes

Lecture notes on systematic trading (MSc level). Each lecture lives in its own folder together with
the notebook that tests its claims on real market data and the charts it cites.

## Lectures

| # | Lecture | Companion notebook | What it covers |
|---|---|---|---|
| 1 | [Introduction](lectures/01-introduction/lecture.md) ([.docx](lectures/01-introduction/lecture.docx)) | — | Definitions, the systematic pipeline, data, strategy styles, research pitfalls, a worked trend-following case study |
| 2 | [OHLCV and Price Aggregation](lectures/02-ohlcv-and-aggregation/lecture.md) | [11_price_aggregation_methods.ipynb](lectures/02-ohlcv-and-aggregation/11_price_aggregation_methods.ipynb) | What a bar is; seven single-bar prices; SMA, EMA, VWAP, KAMA and the Kalman filter; matching memory before comparing (Brown's α = 2/(N+1), Wilder's 2n−1); lag, overshoot, smoothness and tracking on QQQ 1999–2026 |
| 3 | [Other Aggregation Targets](lectures/03-other-aggregation-targets/lecture.md) | [12_other_aggregation_targets.ipynb](lectures/03-other-aggregation-targets/12_other_aggregation_targets.ipynb) | Units; ATR and the √(8/π) range-to-volatility result; Parkinson, Garman–Klass, Rogers–Satchell, Yang–Zhang; discrete-sampling bias; ER and ADX; OBV to order imbalance; stock–bond correlation; bias-adjusted skewness and kurtosis; block-bootstrap bands on SPY, QQQ, GLD and AGG |

## Layout

```
lectures/
  01-introduction/
    lecture.md, lecture.docx
  02-ohlcv-and-aggregation/
    lecture.md
    11_price_aggregation_methods.ipynb
    figures/                     PNG charts cited by the lecture and written by the notebook
  03-other-aggregation-targets/
    lecture.md
    12_other_aggregation_targets.ipynb
    figures/
trading_models/                  shared Python package the notebooks import
data/raw/                        price cache, created on first run (git-ignored)
```

`trading_models/` stays at the root because it is shared: both notebooks import it, and later
lectures will too. It is the minimal subset of a larger private research project needed to run
these notebooks (traced by import, not hand-picked). Where a technique already has a tested
implementation there (Kaufman's Adaptive Moving Average, the Kalman filter, Wilder's ATR, ADX and
efficiency ratio), the notebooks import it rather than reimplementing it, and each notebook checks
its hand calculations against the package on a real date.

The notebooks are committed with their outputs, so tables and charts are visible on GitHub without
running anything. Charts are embedded as static PNGs; running a notebook regenerates them, together
with interactive HTML versions (git-ignored), in its lecture's `figures/` folder.

## Running the notebooks

```bash
python -m venv .venv
.venv\Scripts\activate          # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
pip install -e .
jupyter lab lectures/
```

Each notebook finds the repository root by looking for `pyproject.toml`, so it can be run from any
folder. PNG export needs a Chromium-based browser (Chrome or Edge) installed; without one, only the
HTML charts are written.

No price data is bundled. The notebooks fetch daily bars from Yahoo Finance on first run (via
`yfinance`) and cache them under `data/raw/`, which is git-ignored. This is deliberate: Yahoo
Finance's terms generally restrict redistributing its data, so re-running the notebooks is the way
to get it.
