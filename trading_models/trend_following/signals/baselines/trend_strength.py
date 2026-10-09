"""Trend-strength filters: magnitude (how trendy is this instrument right now), not direction.

Meant to gate or scale a directional baseline (e.g. only take a moving-average crossover when
ADX is above some threshold), not to be traded on their own sign -- ADX, R-squared, the
efficiency ratio and the Hurst exponent are all unsigned or centred-at-0.5 magnitudes. Wiring a
magnitude baseline into an Envelope as a confidence gate is left to the registry/ensemble layer,
not built into these functions.

`regression_slope_tstat` is `trading_models.momentum.trend_tstat` re-exported under this
taxonomy's name -- the project brief lists "t-stat of the slope" here and "regression-slope
trend" again under Statistical/model-based; it is the same statistic, implemented once.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trading_models.momentum import average_true_range
from trading_models.momentum import trend_tstat as regression_slope_tstat
from trading_models.trend_following.data.schema import InstrumentPanel

__all__ = [
    "adx",
    "efficiency_ratio",
    "hurst_exponent",
    "regression_slope_tstat",
    "rolling_r_squared",
]


def adx(panel: InstrumentPanel, period: int = 14) -> pd.DataFrame:
    """Wilder's Average Directional Index: 0-100-ish, unsigned (direction comes from comparing
    +DI and -DI, not from ADX itself, and is not exposed here -- this is a strength filter)."""
    high, low, close = panel.high, panel.low, panel.close
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr = average_true_range(high, low, close, period)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rolling_r_squared(panel: InstrumentPanel, window: int) -> pd.DataFrame:
    """R-squared of a rolling linear regression of log(close) on time: in [0, 1], the companion
    statistic to `regression_slope_tstat` (same regression, fit quality instead of its t-stat)."""
    x = np.arange(window, dtype=float)
    xc = x - x.mean()
    sxx = float((xc**2).sum())

    def r2(y: np.ndarray) -> float:
        yc = y - y.mean()
        slope = float((xc * yc).sum() / sxx)
        ss_res = float(((yc - slope * xc) ** 2).sum())
        ss_tot = float((yc**2).sum())
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return np.log(panel.close).rolling(window).apply(r2, raw=True)


def efficiency_ratio(panel: InstrumentPanel, window: int = 10) -> pd.DataFrame:
    """Kaufman's efficiency ratio: net change over `window` days / sum of daily absolute
    changes -- 1.0 for a straight-line trend, near 0 for pure noise. The same statistic
    `kama_baseline` uses internally to speed up or slow down its own smoothing, exposed here as
    its own trend-strength filter."""
    close = panel.close
    change = (close - close.shift(window)).abs()
    path = close.diff().abs().rolling(window).sum()
    return (change / path.replace(0.0, np.nan)).fillna(0.0)


def hurst_exponent(panel: InstrumentPanel, window: int = 100, min_chunk: int = 8) -> pd.DataFrame:
    """Hurst exponent via rescaled-range (R/S) analysis: within the trailing `window`, log(mean
    R/S) is regressed on log(chunk size) across a few geometrically-spaced chunk sizes. ~0.5 is a
    random walk, above 0.5 is trending/persistent, below 0.5 is mean-reverting. A standard but
    noisy estimator -- treat differences of a few hundredths as noise, not signal."""
    returns = np.log(panel.close).diff()
    sizes: list[int] = []
    s = min_chunk
    while s <= window // 2:
        sizes.append(s)
        s *= 2
    if len(sizes) < 2:
        sizes = sorted({max(2, window // 4), max(3, window // 2)})

    def hurst_of(x: np.ndarray) -> float:
        log_rs, log_n = [], []
        for size in sizes:
            n_chunks = len(x) // size
            if n_chunks < 1:
                continue
            rs_vals = []
            for c in range(n_chunks):
                chunk = x[c * size : (c + 1) * size]
                cum = np.cumsum(chunk - chunk.mean())
                s_dev = chunk.std()
                if s_dev > 0:
                    rs_vals.append((cum.max() - cum.min()) / s_dev)
            if rs_vals:
                log_rs.append(float(np.log(np.mean(rs_vals))))
                log_n.append(float(np.log(size)))
        if len(log_n) < 2:
            return np.nan
        return float(np.polyfit(log_n, log_rs, 1)[0])

    return returns.rolling(window).apply(hurst_of, raw=True)
