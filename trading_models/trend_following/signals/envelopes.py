"""Envelopes: map a Baseline's raw score to a target position in [-1, 1].

Time-series envelopes (`sign_envelope`, `clip_envelope`, `tanh_envelope`) act per instrument,
independently. Cross-sectional envelopes (`rank_top_bottom_envelope`) act across the row (need
every instrument's score for that date to decide any one instrument's position), and
`dual_gate_envelope` combines a cross-sectional ranking with a time-series absolute-trend filter
(dual momentum: only the top-ranked names whose own trend is also positive).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sign_envelope(score: pd.DataFrame) -> pd.DataFrame:
    """+1 / -1 / 0, the sign of the score. NaN stays NaN (no position before it warms up)."""
    return np.sign(score)


def clip_envelope(score: pd.DataFrame, scale: float = 1.0) -> pd.DataFrame:
    """score / scale, clipped to [-1, 1]. `scale` is the score reaching full conviction."""
    return (score / scale).clip(-1.0, 1.0)


def tanh_envelope(score: pd.DataFrame, scale: float = 1.0) -> pd.DataFrame:
    """tanh(score / scale): a smooth version of `clip_envelope` with no hard corner at +-1."""
    return np.tanh(score / scale)


def rank_top_bottom_envelope(score: pd.DataFrame, k: int, long_short: bool = True) -> pd.DataFrame:
    """Long the top k instruments by score, short the bottom k (each leg sums to 1 in absolute
    value; +1/k or -1/k per selected name), or long-only (top k, summing to 1) if `long_short`
    is False. Ties are broken by column order (`rank(method="first")`), so output is deterministic
    rather than arbitrary."""
    ranks = score.rank(axis=1, ascending=False, method="first")
    n = score.notna().sum(axis=1)
    top = (ranks <= k).astype(float)
    long_leg = top.div(top.sum(axis=1).replace(0.0, np.nan), axis=0)
    if not long_short:
        return long_leg.where(score.notna().any(axis=1))
    bottom = ranks.gt(n - k, axis=0).astype(float)
    short_leg = bottom.div(bottom.sum(axis=1).replace(0.0, np.nan), axis=0)
    return long_leg - short_leg


def dual_gate_envelope(
    relative_score: pd.DataFrame, absolute_score: pd.DataFrame, k: int
) -> pd.DataFrame:
    """Long the top k by `relative_score`, but only names where `absolute_score` is also positive
    (dual momentum). Long-only, long-flat: a name ranked top but with a negative absolute trend
    gets zero, not a short."""
    picked = rank_top_bottom_envelope(relative_score, k, long_short=False)
    return picked.where((absolute_score > 0) & absolute_score.notna(), 0.0).where(picked.notna())
