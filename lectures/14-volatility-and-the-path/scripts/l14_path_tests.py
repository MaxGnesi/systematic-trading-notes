"""Lecture 14 §3: the path against a path without memory.
1. Steps of size d: share that continue, on the tape and on its own one-minute returns shuffled within each year (same sizes, no memory).
2. Variance ratio: realised variance from k-minute returns over the realised variance from one-minute returns, same periods,
   k from 1 minute to 1 week; below 1, the price reverts at that horizon (sqrt(t) overstates risk), above 1 it trends."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from l14_steps import steps

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
       .with_columns(pl.col("close").forward_fill()))
lp = np.log(g["close"].to_numpy()); yr = g["time"].dt.year().to_numpy()
rng = np.random.default_rng(0); R = {"steps": {}, "variance_ratio": {}}

# 1. steps: tape against shuffled, by year
for bp in (10, 20, 50, 100):
    row = {}
    for y in np.unique(yr):
        x = lp[yr == y]; r = np.diff(x); sh = np.r_[x[0], x[0] + np.cumsum(rng.permutation(r))]
        ct = [(lambda s: float(np.mean(s[1:] == s[:-1])))(steps(z, bp / 1e4)[0]) for z in (x, sh)]
        row[int(y)] = dict(tape=round(ct[0], 4), shuffled=round(ct[1], 4), diff_pts=round((ct[0] - ct[1]) * 100, 2))
    R["steps"][bp] = row
    print(bp, "bp", {y: v["diff_pts"] for y, v in row.items()}, flush=True)

# 2. variance ratio over whole weeks, k = 1 minute ... 1 week
W = 7 * 1440; nw = len(lp) // W; X = lp[: nw * W].reshape(nw, W)
rv1 = (np.diff(X, axis=1) ** 2).sum(1)
wy = yr[: nw * W: W]
for k, lab in ((5, "5 min"), (30, "30 min"), (60, "1 hour"), (240, "4 hours"), (1440, "1 day"), (W, "1 week")):
    Xk = np.c_[X[:, ::k], X[:, -1]] if k < W else np.c_[X[:, 0], X[:, -1]]
    rvk = (np.diff(Xk, axis=1) ** 2).sum(1)
    vr = rvk.sum() / rv1.sum()
    by = {int(y): round(float(rvk[wy == y].sum() / rv1[wy == y].sum()), 3) for y in np.unique(wy)}
    # uncertainty: weeks resampled
    bs = [rvk[i].sum() / rv1[i].sum() for i in (rng.integers(0, nw, nw) for _ in range(500))]
    R["variance_ratio"][lab] = dict(ratio=round(float(vr), 3), ci90=[round(float(np.quantile(bs, .05)), 3), round(float(np.quantile(bs, .95)), 3)], by_year=by)
    print(lab, R["variance_ratio"][lab], flush=True)
(L14_RESULTS / "l14_path_tests.json").write_text(json.dumps(R, indent=1))
