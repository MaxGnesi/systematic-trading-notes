"""Lecture 20, H5: Hawkes processes fitted per hour to the times of Bybit taker orders (unique ms). Kernel: sum of exponentials with fixed decay times
1 ms, 10 ms, 100 ms, 1 s, 10 s, 100 s and non-negative weights a_k (Bacry, Mastromatteo and Muzy, 2015); constant outside rate mu per hour.
With the decays fixed the intensity is linear in (mu, a), so the log-likelihood is concave; fitted by L-BFGS-B. Branching ratio n = sum a_k.
Events of the previous hour do not excite the current one (each hour fitted on its own). Also usable for any window: fit(times_s, T).
Output: L20_OUT/s3/hawkes_hours.parquet. Usage: python l20_s3_hawkes.py [DAY ...]"""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
from numba import njit
from scipy.optimize import minimize
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
TAUS = np.array([0.001, 0.01, 0.1, 1.0, 10.0, 100.0]); BETAS = 1 / TAUS


@njit(cache=True)
def design(t, betas):
    """X[i, k] = beta_k * sum_{j<i} exp(-beta_k (t_i - t_j)): the intensity at event i from all earlier events, per unit weight of kernel k."""
    n, K = len(t), len(betas); X = np.zeros((n, K)); A = np.zeros(K)
    for i in range(1, n):
        dt = t[i] - t[i - 1]
        for k in range(K):
            A[k] = np.exp(-betas[k] * dt) * (1.0 + A[k])
            X[i, k] = betas[k] * A[k]
    return X


def fit(t, T):
    """t: event times in seconds from the window start, T: window length in seconds. Returns mu, weights a_k, n = sum a_k, log-likelihood."""
    X = design(t, BETAS)
    c = np.array([(1 - np.exp(-b * (T - t))).sum() for b in BETAS])          # integral of each unit kernel up to T
    def nll(p):
        lam = p[0] + X @ p[1:]
        return -(np.log(lam).sum() - p[0] * T - c @ p[1:])
    def grad(p):
        lam = p[0] + X @ p[1:]; w = 1 / lam
        return -np.concatenate([[w.sum() - T], X.T @ w - c])
    p0 = np.concatenate([[0.5 * len(t) / T], np.full(len(BETAS), 0.5 / len(BETAS))])
    r = minimize(nll, p0, jac=grad, method="L-BFGS-B", bounds=[(1e-9, None)] + [(0, None)] * len(BETAS))
    return r.x[0], r.x[1:], float(r.x[1:].sum()), -r.fun, r.success


if __name__ == "__main__":
    rows = []; t0 = time.time()
    for day in L20.day_list():
        ts = np.unique(pl.read_parquet(L20.ORD / f"bybit_{day}.parquet", columns=["ts"])["ts"].to_numpy())
        for h in range(24):
            h0 = int(np.datetime64(f"{day}T00:00:00", "ms").astype(np.int64)) + h * 3_600_000
            x = ts[(ts >= h0) & (ts < h0 + 3_600_000)]
            if len(x) < 100: continue
            mu, a, n, ll, ok = fit((x - h0) / 1000.0, 3600.0)
            rows.append(dict(day=day, hour=h, events=len(x), mu=mu, n=n, ok=ok, **{f"a_{t:g}": v for t, v in zip(TAUS, a)}))
        print(day, f"{time.time() - t0:.0f} s, median n {np.median([r['n'] for r in rows if r['day'] == day]):.3f}", flush=True)
    pl.DataFrame(rows).write_parquet(OUT / f"{L20.tag()}hawkes_hours.parquet")
