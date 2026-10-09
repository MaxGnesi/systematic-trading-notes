"""Statistical / model-based baselines.

`regression_slope_tstat` (the project brief's "rolling linear fit with a t-stat threshold") is
defined once, in `trend_strength` (it is the same statistic as that module's "t-stat of the
slope" filter), and re-exported here under this taxonomy's name for discoverability.

`kalman_local_linear_trend` is new: a real, causal Kalman filter, not a rolling-window
regression -- it adapts its own effective lookback to how noisy the series currently is, rather
than using a fixed window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trading_models.trend_following.data.schema import InstrumentPanel
from trading_models.trend_following.signals.baselines.trend_strength import regression_slope_tstat

__all__ = ["kalman_local_linear_trend", "regression_slope_tstat"]


def kalman_local_linear_trend(
    panel: InstrumentPanel, level_var: float = 1e-4, trend_var: float = 1e-6, obs_var: float = 1e-3
) -> pd.DataFrame:
    """Local-linear-trend Kalman filter on log(close): a 2-state (level, trend) filter; the
    trend component is returned as a continuous baseline (an Envelope maps it to a position).

    Causal by construction -- a forward predict/update recursion, so the trend estimate at t
    uses observations through t only, never later ones. Process/observation noise variances
    (`level_var`, `trend_var`, `obs_var`) are fixed hyperparameters here, not fit by maximum
    likelihood; a real deployment would estimate them per instrument.
    """
    log_close = np.log(panel.close)
    arr = log_close.to_numpy()
    n, k = arr.shape
    out = np.full((n, k), np.nan)
    transition = np.array([[1.0, 1.0], [0.0, 1.0]])
    observe = np.array([[1.0, 0.0]])
    process_noise = np.array([[level_var, 0.0], [0.0, trend_var]])

    for j in range(k):
        col = arr[:, j]
        valid = ~np.isnan(col)
        if not valid.any():
            continue
        first = int(np.argmax(valid))
        state = np.array([col[first], 0.0])
        cov = np.eye(2)
        for t in range(first, n):
            state = transition @ state
            cov = transition @ cov @ transition.T + process_noise
            if np.isnan(col[t]):
                out[t, j] = state[1]
                continue
            innovation = col[t] - (observe @ state)[0]
            innovation_var = (observe @ cov @ observe.T)[0, 0] + obs_var
            gain = (cov @ observe.T).flatten() / innovation_var
            state = state + gain * innovation
            cov = (np.eye(2) - np.outer(gain, observe)) @ cov
            out[t, j] = state[1]
    return pd.DataFrame(out, index=log_close.index, columns=log_close.columns)
