"""Path-dependent and range-based trend rules that need daily high, low and close.

Each function returns a DataFrame (date x asset) of states or signals for the *close of day t*,
using data up to and including t only. State rules return +1 (long), 0 (flat) or -1 (short); the
portfolio layer decides whether the short side is used (long-short) or ignored (long-flat).
Prices should be adjusted for distributions so gaps on ex-dividend days do not trigger rules.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma_crossover(prices: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    """+1 when the fast simple moving average is above the slow one, -1 below."""
    return np.sign(prices.rolling(fast).mean() - prices.rolling(slow).mean())


def average_true_range(
    high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame, period: int = 14
) -> pd.DataFrame:
    """Wilder's average true range."""
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()]).groupby(level=0).max()
    return tr.reindex(close.index).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def donchian_state(
    high: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
    entry: int = 55,
    exit_: int = 20,
) -> pd.DataFrame:
    """Turtle-style channel breakout.

    Enter long when the close exceeds the highest high of the previous `entry` days and leave when
    it falls below the lowest low of the previous `exit_` days. Shorts mirror this (enter on a
    new `entry`-day low, leave on an `exit_`-day high). Flat in between.
    """
    up_in = high.rolling(entry).max().shift(1)
    dn_in = low.rolling(entry).min().shift(1)
    up_out = high.rolling(exit_).max().shift(1)
    dn_out = low.rolling(exit_).min().shift(1)
    out = np.zeros(close.shape)
    c, ui, di, uo, do = (a.to_numpy() for a in (close, up_in, dn_in, up_out, dn_out))
    for j in range(c.shape[1]):
        s = 0
        for t in range(c.shape[0]):
            if np.isnan(ui[t, j]) or np.isnan(do[t, j]) or np.isnan(c[t, j]):
                out[t, j] = 0
                continue
            if s == 0:
                if c[t, j] > ui[t, j]:
                    s = 1
                elif c[t, j] < di[t, j]:
                    s = -1
            elif s == 1 and c[t, j] < do[t, j]:
                s = 0
            elif s == -1 and c[t, j] > uo[t, j]:
                s = 0
            out[t, j] = s
    return pd.DataFrame(out, index=close.index, columns=close.columns)


def _persist(raw: pd.DataFrame) -> pd.DataFrame:
    """Carry the last non-NaN state forward; 0 before the first one."""
    return raw.ffill().fillna(0.0)


def pivot_state(
    high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame, k: int = 5
) -> pd.DataFrame:
    """Swing-point breakout.

    A pivot high is a day whose high is the highest of the k days on each side; it is only known
    (confirmed) k days later. Long when the close breaks above the last confirmed pivot high,
    short when it breaks below the last confirmed pivot low; the state persists until the opposite
    break.
    """
    hd, ld = high.shift(k), low.shift(k)
    piv_high = hd.where(hd >= high.rolling(2 * k + 1).max()).ffill()
    piv_low = ld.where(ld <= low.rolling(2 * k + 1).min()).ffill()
    raw = pd.DataFrame(
        np.where(close > piv_high, 1.0, np.where(close < piv_low, -1.0, np.nan)),
        index=close.index,
        columns=close.columns,
    )
    return _persist(raw)


def darvas_state(
    high: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
    confirm: int = 3,
    lookback: int = 20,
) -> pd.DataFrame:
    """Darvas box breakout.

    A box top is a day whose high is the highest of the previous `lookback` days and is not
    exceeded during the next `confirm` days; the box bottom is the lowest low from that day
    onward. Long when the close breaks above the latest box top, short when it breaks below the
    box bottom; the state persists until the opposite break.
    """
    hd = high.shift(confirm)
    is_top = (hd >= high.rolling(lookback + 1).max().shift(confirm)) & (
        high.rolling(confirm).max() <= hd
    )
    top = hd.where(is_top).ffill()
    bottom = low.rolling(confirm + 1).min().where(is_top).ffill()
    raw = pd.DataFrame(
        np.where(close > top, 1.0, np.where(close < bottom, -1.0, np.nan)),
        index=close.index,
        columns=close.columns,
    )
    return _persist(raw)


def kama(prices: pd.DataFrame, er_window: int = 10, fast: int = 2, slow: int = 30) -> pd.DataFrame:
    """Kaufman's adaptive moving average: smoothing speeds up when the market trends.

    The efficiency ratio is net change over the window divided by the sum of absolute daily changes.
    """
    change = (prices - prices.shift(er_window)).abs()
    path = prices.diff().abs().rolling(er_window).sum()
    er = (change / path.replace(0.0, np.nan)).fillna(0.0)
    fast_sc, slow_sc = 2.0 / (fast + 1), 2.0 / (slow + 1)
    sc = ((er * (fast_sc - slow_sc) + slow_sc) ** 2).to_numpy()
    p = prices.to_numpy()
    out = np.full(p.shape, np.nan)
    for j in range(p.shape[1]):
        start = er_window
        out[start, j] = p[start, j]
        for t in range(start + 1, p.shape[0]):
            out[t, j] = out[t - 1, j] + sc[t, j] * (p[t, j] - out[t - 1, j])
    return pd.DataFrame(out, index=prices.index, columns=prices.columns)


def kama_signal(
    prices: pd.DataFrame,
    er_window: int = 10,
    fast: int = 2,
    slow: int = 30,
    filter_mult: float | None = 0.5,
) -> pd.DataFrame:
    """Trend state from KAMA.

    With `filter_mult=None`: +1 when the price is above KAMA, -1 below. Otherwise Kaufman's
    filtered version: long once KAMA rises by more than filter_mult x the 20-day standard
    deviation of its own daily changes, short once it falls by that much, else keep the last state.
    """
    k = kama(prices, er_window, fast, slow)
    if filter_mult is None:
        return np.sign(prices - k)
    d = k.diff()
    thr = filter_mult * d.rolling(20).std()
    raw = pd.DataFrame(
        np.where(d > thr, 1.0, np.where(d < -thr, -1.0, np.nan)),
        index=prices.index,
        columns=prices.columns,
    )
    return _persist(raw.where(thr.notna()))


def supertrend(
    high: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
    period: int = 10,
    mult: float = 3.0,
) -> pd.DataFrame:
    """SuperTrend: +1 / -1 trend from ratcheting ATR bands around the mid-price."""
    atr = average_true_range(high, low, close, period)
    mid = (high + low) / 2.0
    ub, lb = (mid + mult * atr).to_numpy(), (mid - mult * atr).to_numpy()
    c = close.to_numpy()
    out = np.zeros(c.shape)
    for j in range(c.shape[1]):
        fu = fl = np.nan
        trend = 0
        for t in range(c.shape[0]):
            if np.isnan(ub[t, j]):
                continue
            if np.isnan(fu):
                fu, fl, trend = ub[t, j], lb[t, j], 1
            else:
                fu = ub[t, j] if (ub[t, j] < fu or c[t - 1, j] > fu) else fu
                fl = lb[t, j] if (lb[t, j] > fl or c[t - 1, j] < fl) else fl
                if c[t, j] > fu:
                    trend = 1
                elif c[t, j] < fl:
                    trend = -1
            out[t, j] = trend
    return pd.DataFrame(out, index=close.index, columns=close.columns)


def chandelier_state(
    high: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
    entry: int = 55,
    atr_period: int = 20,
    mult: float = 3.0,
) -> pd.DataFrame:
    """Channel-breakout entry with an ATR trailing stop.

    Enter long on a close above the previous `entry`-day high; the stop trails at the highest close
    since entry minus mult x ATR and only moves up; exit (flat) when the close falls below it.
    Shorts mirror this on a new `entry`-day low.
    """
    atr = average_true_range(high, low, close, atr_period).to_numpy()
    up_in = high.rolling(entry).max().shift(1).to_numpy()
    dn_in = low.rolling(entry).min().shift(1).to_numpy()
    c = close.to_numpy()
    out = np.zeros(c.shape)
    for j in range(c.shape[1]):
        s, extreme, stop = 0, np.nan, np.nan
        for t in range(c.shape[0]):
            if np.isnan(up_in[t, j]) or np.isnan(atr[t, j]) or np.isnan(c[t, j]):
                continue
            if s == 0:
                if c[t, j] > up_in[t, j]:
                    s, extreme = 1, c[t, j]
                    stop = extreme - mult * atr[t, j]
                elif c[t, j] < dn_in[t, j]:
                    s, extreme = -1, c[t, j]
                    stop = extreme + mult * atr[t, j]
            elif s == 1:
                extreme = max(extreme, c[t, j])
                stop = max(stop, extreme - mult * atr[t, j])
                if c[t, j] < stop:
                    s = 0
            else:
                extreme = min(extreme, c[t, j])
                stop = min(stop, extreme + mult * atr[t, j])
                if c[t, j] > stop:
                    s = 0
            out[t, j] = s
    return pd.DataFrame(out, index=close.index, columns=close.columns)
