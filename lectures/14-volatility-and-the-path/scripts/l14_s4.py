"""Lecture 14 §4: crossings and excursions, on calm and on volatile days.
Crossings: steps of size d per day (the ladder of l14_steps) against the random-walk count, the day's realised variance / d^2; turns = steps that reverse.
Excursions: a position opened at each full hour and held H; the worst move against a long and against a short, in units of sigma*sqrt(H),
sigma from the past 28 days' one-minute realised variance; random walk: P(max > k) = 2 P(Z > k), mean 0.80."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy.stats import norm
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
nd = n // 1440; lp = np.log(g["close"].to_numpy())[: nd * 1440]; X = lp.reshape(nd, 1440)
rv = (np.diff(X, axis=1) ** 2).sum(1)
calm, wild = rv <= np.percentile(rv, 50), rv >= np.percentile(rv, 90)
R = {"crossings": {}, "excursions": {}}

# 1. crossings per day
for bp in (20, 50, 100):
    d = bp / 1e4; rows = {}
    for lab, sel in (("calm half", calm), ("most volatile 10%", wild), ("all days", np.ones(nd, bool))):
        st, tu, pr = [], [], []
        for i in np.where(sel)[0]:
            s, _ = steps(X[i], d); st.append(len(s)); tu.append(int(np.sum(s[1:] != s[:-1]))); pr.append(rv[i] / d ** 2)
        st, tu, pr = map(np.array, (st, tu, pr))
        rows[lab] = dict(steps_per_day=round(float(st.mean()), 1), random_walk=round(float(pr.mean()), 1), ratio=round(float(st.sum() / pr.sum()), 3),
                         turns_per_day=round(float(tu.mean()), 1), turn_share=round(float(tu.sum() / max(st.sum() - len(st), 1)), 3))
    R["crossings"][bp] = rows; print(bp, "bp", rows, flush=True)

# 2. excursions of positions opened at each full hour
sig1 = pl.Series(rv / 1440).shift(1).rolling_mean(28, min_samples=7).to_numpy()          # one-minute variance, past 28 days
for H, lab in ((60, "1 hour"), (240, "4 hours"), (1440, "1 day")):
    starts = np.arange(1440 * 28, len(lp) - H, 60)
    day = starts // 1440; s = np.sqrt(sig1[day] * H); ok = np.isfinite(s)
    starts, day, s = starts[ok], day[ok], s[ok]
    W = lp[starts[:, None] + np.arange(H + 1)] - lp[starts][:, None]
    adv = np.r_[-W.min(1), W.max(1)] / np.r_[s, s]                          # worst move against a long, then against a short
    reg = np.r_[day, day]
    out = {}
    for rl, sel in (("calm half", calm[reg]), ("most volatile 10%", wild[reg]), ("all", np.ones(len(reg), bool))):
        a = adv[sel]
        out[rl] = dict(mean=round(float(a.mean()), 2), p_over_2=round(float((a > 2).mean()), 4), p_over_3=round(float((a > 3).mean()), 4))
    out["random walk"] = dict(mean=round(float(np.sqrt(2 / np.pi)), 2), p_over_2=round(float(2 * norm.sf(2)), 4), p_over_3=round(float(2 * norm.sf(3)), 4))
    R["excursions"][lab] = out; print(lab, out, flush=True)
(L14_RESULTS / "l14_s4.json").write_text(json.dumps(R, indent=1))
