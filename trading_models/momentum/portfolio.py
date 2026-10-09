"""Turn signals into target weights.

Weights are decided at the close of day t from information up to t; the backtester trades them
on day t+1. Cash is whatever is left over: return = sum(w r) + (1 - sum(w)) * cash_rate, so a
flat position earns the cash rate and short proceeds are invested in cash.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def inverse_vol_base(returns: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Inverse-volatility weights summing to one at every date (trailing window)."""
    inv = 1.0 / returns.rolling(window).std()
    return inv.div(inv.sum(axis=1), axis=0)


def long_flat(signal: pd.DataFrame, base: pd.DataFrame, continuous: bool = False) -> pd.DataFrame:
    """Hold the base weight where the signal is positive, cash elsewhere (0 <= sum(w) <= 1).

    With `continuous=True` the base weight is scaled by max(signal, 0) instead of on/off.
    """
    on = signal.clip(lower=0.0, upper=1.0) if continuous else (signal > 0).astype(float)
    return base * on.where(signal.notna())


def long_short_ts(signal: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Base weight times the signal in [-1, 1]: long when positive, short when negative."""
    return base * signal.clip(-1.0, 1.0)


def cross_sectional_top_bottom(
    signal: pd.DataFrame, base: pd.DataFrame, k: int = 3, long_short: bool = True
) -> pd.DataFrame:
    """Long the top k assets, short the bottom k (each leg 0.5 gross, inverse-vol within the leg).

    With `long_short=False` only the long leg is held, scaled to gross 1 (fully invested).
    """
    ranks = signal.rank(axis=1, ascending=False, method="first")
    n = signal.notna().sum(axis=1)
    top = (ranks <= k).astype(float)
    bottom = ranks.gt(n - k, axis=0).astype(float)
    long_w = base * top
    long_w = long_w.div(long_w.sum(axis=1), axis=0)
    if not long_short:
        return long_w.where(signal.notna().any(axis=1), np.nan)
    short_w = base * bottom
    short_w = short_w.div(short_w.sum(axis=1), axis=0)
    return 0.5 * long_w - 0.5 * short_w


def dual_momentum(
    relative: pd.DataFrame, absolute: pd.DataFrame, base: pd.DataFrame, k: int = 3
) -> pd.DataFrame:
    """Long the top k by relative strength, but only those with positive absolute momentum.

    The long leg is scaled so the k names would sum to one; names failing the absolute test
    are replaced by cash (long-flat cross-sectional momentum).
    """
    ranks = relative.rank(axis=1, ascending=False, method="first")
    picked = (ranks <= k).astype(float)
    w = base * picked
    w = w.div(w.sum(axis=1), axis=0)
    return w * (absolute > 0).astype(float).where(absolute.notna())


def score_weighted(signal: pd.DataFrame) -> pd.DataFrame:
    """Dollar-neutral long-short weights proportional to the cross-sectional z-score, gross 1."""
    z = signal.sub(signal.mean(axis=1), axis=0).div(signal.std(axis=1), axis=0)
    return z.div(z.abs().sum(axis=1), axis=0)


def rebalance_every(weights: pd.DataFrame, every: int) -> pd.DataFrame:
    """Update weights only every `every` rows and hold them in between."""
    if every <= 1:
        return weights
    return weights.iloc[::every].reindex(weights.index, method="ffill")
