# Systematic Trading Notes

Lecture notes on systematic trading (MSc level). Each lecture lives in its own folder together with
the notebook that tests its claims on real market data and the charts it cites.

The course roadmap (planned lectures on clock-time bars (trend and stat arb), tick data and alternative bars, prediction markets, and a final part on
testing and portfolio construction) and the style and formula conventions are in [COURSE_GUIDE.md](COURSE_GUIDE.md).

## Lectures

| # | Lecture | Companion notebook | What it covers |
|---|---|---|---|
| 1 | [Introduction](lectures/01-introduction/lecture.md) ([.docx](lectures/01-introduction/lecture.docx)) | — | Definitions, the systematic pipeline, data, strategy styles, research pitfalls, a worked trend-following case study |
| 2 | [OHLCV and Price Smoothing](lectures/02-ohlcv-and-price-smoothing/lecture.md) | [02_price_smoothing.ipynb](lectures/02-ohlcv-and-price-smoothing/02_price_smoothing.ipynb) | What a bar is; seven single-bar prices; SMA, EMA, VWAP, KAMA and the Kalman filter; matching memory before comparing (Brown's α = 2/(N+1), Wilder's 2n−1); lag, overshoot, smoothness and tracking on QQQ 1999–2026 |
| 3 | [Same Bars, Different Questions: Volatility, Flow, Correlation and Tails](lectures/03-same-bars-different-questions/lecture.md) | [03_same_bars_different_questions.ipynb](lectures/03-same-bars-different-questions/03_same_bars_different_questions.ipynb) | Units; ATR and the √(8/π) range-to-volatility result; Parkinson, Garman–Klass, Rogers–Satchell, Yang–Zhang; discrete-sampling bias; ER and ADX; OBV to order imbalance; stock–bond correlation; bias-adjusted skewness and kurtosis; block-bootstrap bands on SPY, QQQ, GLD and AGG |
| 4 | [Tracking Hidden States: the Kalman Filter](lectures/04-tracking-hidden-states/lecture.md) | [04_tracking_hidden_states.ipynb](lectures/04-tracking-hidden-states/04_tracking_hidden_states.ipynb) | Bottom-up smoothing versus top-down state tracking; level, slope and acceleration as hidden states, each with its own trading signal; the dials Q and R; starting the filter; robust and other extensions; extended and unscented filters on hidden volatility; evaluating trend filters for trend systems |
| 5 | [What Trend Following Captures](lectures/05-what-trend-following-captures/lecture.md) | [05_what_trend_following_captures.ipynb](lectures/05-what-trend-following-captures/05_what_trend_following_captures.ipynb) | Part II opener, about the market: trend profits split into drift and timing on 16 ETFs; timing earned in episodes (forced selling, liquidity spirals, hedging flows); five questions about a market (drift, frictions, gaps, decay, intervention); what to capture and why it should last; data mining and multiple testing; the evidence, CTAs and trend in other strategies |
| 6 | [Trend Following: the Map and the Machinery](lectures/06-trend-following-map-and-machinery/lecture.md) | [06_trend_following_map_and_machinery.ipynb](lectures/06-trend-following-map-and-machinery/06_trend_following_map_and_machinery.ipynb) | About the system: a short map (three families, five design choices) with one model card per family; five representative rules and how much they overlap (horizon matters more than family); direction and speed decide crisis protection; forecasts, volatility targeting, costs and turnover, payoff profiles |
| 7 | [Comparing Trend Systems](lectures/07-comparing-trend-systems/lecture.md) (draft outline) | to follow | Comparing systems fairly: a common axis for speed (direction changes, turnover, trend signature); does a system add anything (spanning, breakeven cost); is the difference real (block bootstrap, Ledoit–Wolf, reality check, SPA, Romano–Wolf, probability of backtest overfitting); robustness over the best point |
| 9 | [Sizing Trend Systems](lectures/09-sizing-trend-systems/lecture.md) (draft) | [09_sizing_trend_systems.ipynb](lectures/09-sizing-trend-systems/09_sizing_trend_systems.ipynb) | Sizing per trade (stop distance), per asset (inverse volatility), by conviction, over time (portfolio target, volatility management, drawdown control) and by edge (Kelly), on the same signals and 16 ETFs |

## Layout

```
lectures/
  01-introduction/
    lecture.md, lecture.docx
  02-ohlcv-and-price-smoothing/
    lecture.md
    02_price_smoothing.ipynb
    figures/                     PNG charts cited by the lecture and written by the notebook
  03-same-bars-different-questions/
    lecture.md
    03_same_bars_different_questions.ipynb
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
