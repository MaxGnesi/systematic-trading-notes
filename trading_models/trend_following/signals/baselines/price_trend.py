"""Price-based trend, breakout and trailing-stop baselines.

Two kinds of function here: thin adapters onto `trading_models.momentum` (reused, not
reimplemented -- `momentum/` stays untouched) for TSMOM, moving-average crossovers, KAMA,
Donchian and SuperTrend; and genuinely new implementations for the rules `momentum/` doesn't
have yet (Keltner, Bollinger, Hull MA, MACD, Parabolic SAR).

Every function takes an `InstrumentPanel` and returns a DataFrame aligned to `panel.close`,
satisfying the `Baseline` protocol. "state" functions (Keltner/Bollinger, like the existing
Donchian/chandelier) persist +1/-1 until the opposite band is crossed, rather than going flat
between bands; "signal"/baseline-only functions return a continuous or +1/-1/NaN score for an
Envelope to map.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trading_models.momentum import (
    average_true_range,
)
from trading_models.momentum import (
    chandelier_state as _chandelier_state,
)
from trading_models.momentum import (
    donchian_state as _donchian_state,
)
from trading_models.momentum import (
    ewma_crossover as _ewma_crossover,
)
from trading_models.momentum import (
    kama_signal as _kama_signal,
)
from trading_models.momentum import (
    multi_horizon_sign as _multi_horizon_sign,
)
from trading_models.momentum import (
    past_return as _past_return,
)
from trading_models.momentum import (
    risk_adjusted_return as _risk_adjusted_return,
)
from trading_models.momentum import (
    sma_crossover as _sma_crossover,
)
from trading_models.momentum import (
    sma_signal as _sma_signal,
)
from trading_models.momentum import (
    supertrend as _supertrend,
)
from trading_models.trend_following.data.schema import InstrumentPanel

# ---------------------------------------------------------------------------
# Adapters onto trading_models.momentum
# ---------------------------------------------------------------------------


def past_return_baseline(panel: InstrumentPanel, lookback: int, skip: int = 0) -> pd.DataFrame:
    """TSMOM baseline: past-return over `lookback` days. `sign_envelope` gives classic TSMOM."""
    return _past_return(panel.close, lookback, skip)


def risk_adjusted_return_baseline(
    panel: InstrumentPanel, lookback: int, skip: int = 0
) -> pd.DataFrame:
    """Vol-scaled TSMOM baseline."""
    return _risk_adjusted_return(panel.close, lookback, skip)


def multi_horizon_baseline(
    panel: InstrumentPanel, lookbacks: tuple[int, ...] = (21, 63, 126, 252)
) -> pd.DataFrame:
    """Average of sign(past return) over several horizons, already in [-1, 1]."""
    return _multi_horizon_sign(panel.close, lookbacks)


def sma_signal_baseline(panel: InstrumentPanel, window: int) -> pd.DataFrame:
    return _sma_signal(panel.close, window)


def sma_crossover_baseline(panel: InstrumentPanel, fast: int, slow: int) -> pd.DataFrame:
    return _sma_crossover(panel.close, fast, slow)


def ewma_crossover_baseline(
    panel: InstrumentPanel, fast_halflife: float, slow_halflife: float
) -> pd.DataFrame:
    return _ewma_crossover(panel.close, fast_halflife, slow_halflife)


def kama_baseline(
    panel: InstrumentPanel,
    er_window: int = 10,
    fast: int = 2,
    slow: int = 30,
    filter_mult: float | None = 0.5,
) -> pd.DataFrame:
    return _kama_signal(panel.close, er_window, fast, slow, filter_mult)


def donchian_baseline(panel: InstrumentPanel, entry: int, exit_: int) -> pd.DataFrame:
    return _donchian_state(panel.high, panel.low, panel.close, entry, exit_)


def supertrend_baseline(
    panel: InstrumentPanel, period: int = 10, mult: float = 3.0
) -> pd.DataFrame:
    return _supertrend(panel.high, panel.low, panel.close, period, mult)


def chandelier_baseline(
    panel: InstrumentPanel, entry: int = 55, atr_period: int = 20, mult: float = 3.0
) -> pd.DataFrame:
    return _chandelier_state(panel.high, panel.low, panel.close, entry, atr_period, mult)


# ---------------------------------------------------------------------------
# New: channel breakouts
# ---------------------------------------------------------------------------


def _persist(raw: pd.DataFrame) -> pd.DataFrame:
    return raw.ffill().fillna(0.0)


def keltner_state(
    panel: InstrumentPanel, ma_window: int = 20, atr_window: int = 10, mult: float = 2.0
) -> pd.DataFrame:
    """Keltner Channel breakout: close above EMA + mult*ATR -> long, below EMA - mult*ATR -> short,
    else hold the last state (persists, like Donchian/chandelier)."""
    close, high, low = panel.close, panel.high, panel.low
    mid = close.ewm(span=ma_window, min_periods=ma_window).mean()
    atr = average_true_range(high, low, close, atr_window)
    upper, lower = mid + mult * atr, mid - mult * atr
    raw = pd.DataFrame(
        np.where(close > upper, 1.0, np.where(close < lower, -1.0, np.nan)),
        index=close.index,
        columns=close.columns,
    )
    return _persist(raw)


def bollinger_state(panel: InstrumentPanel, window: int = 20, mult: float = 2.0) -> pd.DataFrame:
    """Bollinger Band breakout: close above its rolling mean + mult*std -> long, below mean -
    mult*std -> short, else hold the last state."""
    close = panel.close
    mid = close.rolling(window).mean()
    sd = close.rolling(window).std()
    upper, lower = mid + mult * sd, mid - mult * sd
    raw = pd.DataFrame(
        np.where(close > upper, 1.0, np.where(close < lower, -1.0, np.nan)),
        index=close.index,
        columns=close.columns,
    )
    return _persist(raw)


# ---------------------------------------------------------------------------
# New: moving-average variants
# ---------------------------------------------------------------------------


def _wma(s: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)
    return s.rolling(window).apply(lambda x: float(np.dot(x, weights) / weights.sum()), raw=True)


def hull_ma(panel: InstrumentPanel, window: int = 20) -> pd.DataFrame:
    """Hull Moving Average: WMA(2*WMA(n/2) - WMA(n), sqrt(n)) -- a weighted-MA combination
    designed to track price more closely (less lag) than a plain SMA/EMA of the same window."""
    close = panel.close
    half, full = max(1, window // 2), window
    sqrt_n = max(1, round(window**0.5))
    raw = 2 * close.apply(lambda col: _wma(col, half)) - close.apply(lambda col: _wma(col, full))
    return raw.apply(lambda col: _wma(col, sqrt_n))


def hull_ma_signal(panel: InstrumentPanel, window: int = 20) -> pd.DataFrame:
    """+1 / -1 when the Hull MA is rising / falling day over day."""
    return np.sign(hull_ma(panel, window).diff())


def _macd_line(panel: InstrumentPanel, fast: int, slow: int) -> pd.DataFrame:
    close = panel.close
    return (
        close.ewm(span=fast, min_periods=fast).mean()
        - close.ewm(span=slow, min_periods=slow).mean()
    )


def macd(panel: InstrumentPanel, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD histogram: EMA(fast) - EMA(slow), minus its own `signal`-period EMA. A continuous
    momentum-of-momentum baseline, useful for an Envelope that wants to size up when the
    histogram grows and fade as it shrinks back toward zero -- not a reliable *directional*
    reading of a steady trend on its own: the histogram converges toward zero once both EMAs
    have caught up to a constant drift, so its sign near that point is dominated by whatever
    noise sits on top of the trend, not the trend itself (see `macd_signal`, which uses the
    MACD line's own sign instead, for a directional reading)."""
    macd_line = _macd_line(panel, fast, slow)
    signal_line = macd_line.ewm(span=signal, min_periods=signal).mean()
    return macd_line - signal_line


def macd_signal(
    panel: InstrumentPanel, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """+1 / -1, the sign of the MACD *line* (EMA(fast) - EMA(slow); `signal` is accepted for a
    uniform call signature across the registry but unused here -- see `macd`'s docstring for why
    the histogram's sign is not used for direction). Equivalent to `ewma_crossover_baseline`
    with EMA spans instead of half-lives."""
    del signal
    return np.sign(_macd_line(panel, fast, slow))


def parabolic_sar(
    panel: InstrumentPanel, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2
) -> pd.DataFrame:
    """Wilder's Parabolic SAR. +1 while the trailing stop sits below price (uptrend), -1 while
    it sits above (downtrend); flips when price crosses the stop, resetting the acceleration
    factor. Day 0's trend is seeded from the first two closes -- a reasonable choice, not
    Wilder's original rule (which is itself not fully standardised across sources)."""
    close_df = panel.close
    high, low, close = panel.high.to_numpy(), panel.low.to_numpy(), close_df.to_numpy()
    n, k = close.shape
    out = np.zeros((n, k))
    for j in range(k):
        if n < 2:
            continue
        trend = 1 if close[1, j] >= close[0, j] else -1
        ep = high[0, j] if trend == 1 else low[0, j]
        sar = low[0, j] if trend == 1 else high[0, j]
        af = af_start
        out[0, j] = trend
        for t in range(1, n):
            if np.isnan(high[t, j]) or np.isnan(low[t, j]):
                out[t, j] = out[t - 1, j]
                continue
            sar = sar + af * (ep - sar)
            if trend == 1:
                prior_low = low[t - 2, j] if t >= 2 else low[t - 1, j]
                sar = min(sar, low[t - 1, j], prior_low)
                if low[t, j] < sar:
                    trend, sar, ep, af = -1, ep, low[t, j], af_start
                elif high[t, j] > ep:
                    ep, af = high[t, j], min(af + af_step, af_max)
            else:
                prior_high = high[t - 2, j] if t >= 2 else high[t - 1, j]
                sar = max(sar, high[t - 1, j], prior_high)
                if high[t, j] > sar:
                    trend, sar, ep, af = 1, ep, high[t, j], af_start
                elif low[t, j] < ep:
                    ep, af = low[t, j], min(af + af_step, af_max)
            out[t, j] = trend
    return pd.DataFrame(out, index=close_df.index, columns=close_df.columns)
