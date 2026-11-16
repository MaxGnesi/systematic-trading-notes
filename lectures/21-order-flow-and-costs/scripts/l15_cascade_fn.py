"""Numba helpers for l15_cascades.py (in a file so that numba can cache them)."""
import numba as nb
import numpy as np


@nb.njit(cache=True)
def hours_in_band(lh, ll, width, cap):
    """For each hour t: how many hours before t the price stayed within a band of the given width (log high minus log low over hours t-L .. t-1)."""
    n = len(lh); out = np.full(n, np.nan)
    for t in range(1, n):
        if not np.isfinite(width[t]): continue
        hi = -1e18; lo = 1e18; L = 0
        for k in range(1, min(t, cap) + 1):
            hi = max(hi, lh[t - k]); lo = min(lo, ll[t - k])
            if hi - lo > width[t]: break
            L = k
        out[t] = L
    return out


@nb.njit(cache=True)
def same_sign_run(x):
    """For each minute: how many minutes in a row, ending with it, the net flow has had the same (non-zero) sign."""
    n = len(x); out = np.zeros(n)
    for i in range(n):
        s = np.sign(x[i])
        if s == 0: out[i] = 0
        elif i > 0 and np.sign(x[i - 1]) == s: out[i] = out[i - 1] + 1
        else: out[i] = 1
    return out
