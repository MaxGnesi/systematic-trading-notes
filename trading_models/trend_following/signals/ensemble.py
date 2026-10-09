"""Combining several positions into one -- usually more robust than any single rule (averaging
out idiosyncratic whipsaws between lookbacks or signal families), at the cost of being slower to
turn when the ensemble members disagree.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def average_positions(
    positions: list[pd.DataFrame], weights: list[float] | None = None
) -> pd.DataFrame:
    """Weighted average of several position DataFrames (equal-weighted if `weights` is omitted).
    NaN in one member (e.g. still warming up) is excluded from that date's average, not treated
    as zero -- so an ensemble's early-history behaviour matches its slowest member's warm-up,
    not a silently diluted one."""
    if weights is None:
        weights = [1.0] * len(positions)
    if len(weights) != len(positions):
        raise ValueError("weights must have the same length as positions")
    stacked = pd.concat(positions, keys=range(len(positions)))
    w = pd.Series(weights, index=range(len(positions)))

    def _wavg(frame: pd.DataFrame) -> pd.Series:
        idx = frame.index.get_level_values(0)
        ww = w.loc[idx].to_numpy()[:, None]
        mask = frame.notna().to_numpy()
        num = (frame.fillna(0.0).to_numpy() * ww * mask).sum(axis=0)
        den = (ww * mask).sum(axis=0)
        return pd.Series(np.where(den > 0, num / den, np.nan), index=frame.columns)

    return stacked.groupby(level=1).apply(_wavg)


def majority_vote(positions: list[pd.DataFrame]) -> pd.DataFrame:
    """+1 if more members are long than short, -1 if more are short, 0 on a tie or all-NaN."""
    signs = [
        p.apply(lambda s: s.map(lambda x: (x > 0) - (x < 0) if pd.notna(x) else 0))
        for p in positions
    ]
    total = sum(signs)
    return total.apply(lambda s: s.map(lambda x: (x > 0) - (x < 0)))
