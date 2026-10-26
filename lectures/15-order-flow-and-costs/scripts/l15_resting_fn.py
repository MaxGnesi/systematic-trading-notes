"""Numba helper for l15_resting_tail.py (in a file so that numba can cache it)."""
import numba as nb
import numpy as np


@nb.njit(cache=True)
def first_through(ts, px, t0, lim, side, horizon):
    """For each decision: milliseconds until the first trade strictly through the limit (below it for a buy, above for a sell), or -1 if none within the horizon."""
    out = np.full(len(t0), -1, np.int64)
    j = 0
    for i in range(len(t0)):
        while j < len(ts) and ts[j] <= t0[i]: j += 1                           # decisions are sorted; trades after the decision only
        k = j
        while k < len(ts) and ts[k] <= t0[i] + horizon:
            if (side == 1 and px[k] < lim[i]) or (side == -1 and px[k] > lim[i]):
                out[i] = ts[k] - t0[i]; break
            k += 1
    return out
