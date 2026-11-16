"""Audit of H3 (impact rises over the first ~14 orders). On 1 Oct 2025, with the real sequence of taker-order signs:
(A) simulate a mid with a known bare impact G0(n) = n^-0.2 (decaying), observed fresh before each order, and run our solver;
(B) the same simulated mid, but observed only at book updates (every order sees the mid of the last update before it), as in our data;
(C) the real data in book-update time: all taker orders between two updates form one event (sign of their net size), mid before the event.
Solver identical to l20_s3_prop.py."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("prop_check")

D = "2025-10-01"; rng = np.random.default_rng(3)


def solve(e, m, L):
    e0 = e - e.mean()
    C = np.array([1.0] + [np.mean(e0[:-l] * e0[l:]) / e0.var() for l in range(1, 2 * L + 1)])
    R = np.array([np.mean(e[:-l] * (m[l:] - m[:-l])) for l in range(1, L + 1)])
    ell = np.arange(1, L + 1); A = C[np.abs(ell[None, :] - ell[:, None])] - C[ell][None, :]
    return np.linalg.lstsq(A, R, rcond=None)[0], R


O = pl.read_parquet(L20.ORD / f"bybit_{D}.parquet").drop_nulls("mid2").sort("ts")
e = O["side"].to_numpy().astype(float); ts = O["ts"].to_numpy()
U = np.unique(pl.read_parquet(L20.STATE / f"{D}.parquet", columns=["ts"])["ts"].to_numpy())
grp = np.searchsorted(U, ts, side="left")                      # number of updates strictly before the order = its group
L = 1000; n = np.arange(1, 4001); G0 = n ** -0.2
conv = np.convolve(e, G0)[:len(e)]                             # conv[i] = sum_{j<=i} G0(i-j+1) e_j: mid just after order i
m_true = np.r_[0.0, conv[:-1]] + rng.normal(0, 0.5, len(e))    # mid just before order i
first = np.r_[0, np.flatnonzero(np.diff(grp)) + 1]; idx = np.repeat(first, np.diff(np.r_[first, len(e)]))
m_stale = m_true[idx]                                          # mid of the last update: as before the first order of the group
GA, _ = solve(e, m_true, L); GB, _ = solve(e, m_stale, L)
show = [0, 1, 4, 9, 13, 19, 49, 99, 499]
print("orders", len(e), "| orders per update group: median", np.median(np.diff(np.r_[first, len(e)])), "mean", round(len(e) / len(first), 2),
      "| share of orders not first in their group", round(1 - len(first) / len(e), 2))
print("lag      ", [s + 1 for s in show]); print("true G0  ", [round(G0[s], 2) for s in show])
print("(A) fresh", [round(GA[s], 2) for s in show]); print("(B) stale", [round(GB[s], 2) for s in show], "peak at", int(np.argmax(GB[:200]) + 1))
# (C) real data in update time
m = O["mid2"].to_numpy() / 2.0
ev = O.with_columns(pl.Series("g", grp)).group_by("g", maintain_order=True).agg((pl.col("side") * pl.col("size")).sum().alias("q"), pl.col("mid2").first())
ev = ev.filter(pl.col("q") != 0)
Gc, Rc = solve(np.sign(ev["q"].to_numpy()), ev["mid2"].to_numpy() / 2.0, 300)
Go, Ro = solve(e, m, L)
print("(C) real, order time  G:", [round(Go[s], 2) for s in show], "peak", int(np.argmax(Go[:200]) + 1))
print("(C) real, update time G:", [round(Gc[s], 2) for s in [0, 1, 2, 4, 9, 19, 49, 99, 199]], "(lags 1,2,3,5,10,20,50,100,200 events) peak", int(np.argmax(Gc[:100]) + 1),
      "| events", ev.height)
