"""Trend and momentum signals from prices.

Every function takes a date x asset price DataFrame and returns a DataFrame of the same shape.
The value at date t uses prices up to and including t only; the backtester applies a one-day lag
before trading on it. Values are NaN until enough history exists.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def past_return(prices: pd.DataFrame, lookback: int, skip: int = 0) -> pd.DataFrame:
    """Return over `lookback` days ending `skip` days ago (skip=21 gives the classic 12-1 style)."""
    return prices.shift(skip) / prices.shift(skip + lookback) - 1.0


def risk_adjusted_return(prices: pd.DataFrame, lookback: int, skip: int = 0) -> pd.DataFrame:
    """Past return divided by its expected size, vol * sqrt(lookback): a t-statistic-like score.

    For a single asset's own trend this has the same sign as `past_return`; it matters when the
    magnitude is used (continuous sizing, cross-sectional ranking).
    """
    vol = prices.pct_change().rolling(lookback).std().shift(skip)
    return past_return(prices, lookback, skip) / (vol * np.sqrt(lookback))


def multi_horizon_sign(
    prices: pd.DataFrame, lookbacks: tuple[int, ...] = (21, 63, 126, 252)
) -> pd.DataFrame:
    """Average of sign(past return) over several horizons, in [-1, 1]."""
    return sum(np.sign(past_return(prices, lb)) for lb in lookbacks) / len(lookbacks)


def sma_signal(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """+1 when the price is above its simple moving average, -1 below."""
    return np.sign(prices / prices.rolling(window).mean() - 1.0)


def ewma_crossover(
    prices: pd.DataFrame, fast_halflife: float, slow_halflife: float
) -> pd.DataFrame:
    """+1 when the fast EWMA of log price is above the slow one, -1 below."""
    lp = np.log(prices)
    warm = int(slow_halflife * 2)
    fast = lp.ewm(halflife=fast_halflife, min_periods=warm).mean()
    slow = lp.ewm(halflife=slow_halflife, min_periods=warm).mean()
    return np.sign(fast - slow)


def breakout_position(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """Position of the price inside its trailing high-low range, mapped to [-1, 1]."""
    hi = prices.rolling(window).max()
    lo = prices.rolling(window).min()
    return 2.0 * (prices - lo) / (hi - lo).replace(0.0, np.nan) - 1.0


def trend_tstat(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """t-statistic of the slope of log price on time over a trailing window."""
    x = np.arange(window, dtype=float)
    xc = x - x.mean()
    sxx = float((xc**2).sum())

    def tstat(y: np.ndarray) -> float:
        yc = y - y.mean()
        slope = float((xc * yc).sum() / sxx)
        resid = yc - slope * xc
        se = np.sqrt(float(resid @ resid) / (window - 2) / sxx)
        return slope / se if se > 0 else 0.0

    return np.log(prices).rolling(window).apply(tstat, raw=True)
