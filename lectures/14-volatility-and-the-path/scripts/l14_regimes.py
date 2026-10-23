"""Lecture 14 §3: does the path behave differently on volatile days? Days grouped by their realised variance (one-minute returns);
within each group: variance ratio at 30 minutes, 1 hour and 4 hours, and the step test (tape against its own returns shuffled within the group).
Also grouped by the previous day's variance, which is known in advance."""
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
nd = n // 1440; X = np.log(g["close"].to_numpy())[: nd * 1440].reshape(nd, 1440)
r1 = np.diff(X, axis=1); rv = (r1 ** 2).sum(1)
rng = np.random.default_rng(0); R = {}
GROUPS = {"calmest half": (0, 50), "50-80%": (50, 80), "80-90%": (80, 90), "most volatile 10%": (90, 100), "most volatile 2%": (98, 100)}


def tests(days):
    out = {}
    for k in (30, 60, 240):
        Xk = X[days][:, ::k]; out[f"vr_{k}m"] = round(float((np.diff(Xk, axis=1) ** 2).sum() / (r1[days] ** 2).sum()), 3)
    x = np.concatenate([np.r_[X[d, 0], X[d, 0] + np.cumsum(r1[d])] for d in days])          # the days joined (each day starts at its own open)
    r = np.concatenate([r1[d] for d in days]); sh = np.r_[x[0], x[0] + np.cumsum(rng.permutation(r))]
    for bp in (20, 50, 100):
        ct = [(lambda s: float(np.mean(s[1:] == s[:-1])))(steps(z, bp / 1e4)[0]) for z in (np.r_[x[0], x[0] + np.cumsum(r)], sh)]
        out[f"step_{bp}bp_pts"] = round((ct[0] - ct[1]) * 100, 2)
    return out


for basis, val in (("same day", rv), ("previous day", np.r_[np.nan, rv[:-1]])):
    R[basis] = {}
    ok = np.isfinite(val)
    for lab, (lo, hi) in GROUPS.items():
        a, b = np.nanpercentile(val, lo), np.nanpercentile(val, hi)
        days = np.where(ok & (val >= a) & (val <= b))[0]
        R[basis][lab] = dict(days=int(len(days)), **tests(days))
        print(basis, lab, R[basis][lab], flush=True)
(L14_RESULTS / "l14_regimes.json").write_text(json.dumps(R, indent=1))
