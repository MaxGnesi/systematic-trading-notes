"""Lecture 15 §2: the flow matrix. Windows of W minutes in the top or bottom fifth of flow (net aggressive buying / dollars); the next window's
return in the direction of the flow (positive: continuation, negative: reversal), in bp. Cells: flow with / against the slower trend, or no clear
trend (the past three days' return divided by its typical size, from the past 28 days: beyond +-0.5), x the volatility regime (last hour's
realised variance vs its 28-day median, thirds). All conditions known at the end of the window. Days as clusters for the standard error."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close", "usd", "signed_usd").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
       .with_columns(pl.col("close").forward_fill(), pl.col("usd").fill_null(0.0), pl.col("signed_usd").fill_null(0.0)))
lp = np.log(g["close"].to_numpy()); usd = g["usd"].to_numpy(); su = g["signed_usd"].to_numpy(); r1 = np.r_[0.0, np.diff(lp)]
rv60 = np.convolve(r1 ** 2, np.ones(60), "full")[:n]
med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
H = 3 * 1440; daily_var = pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()   # typical daily variance, past 28 days
cu, cs = np.r_[0, np.cumsum(usd)], np.r_[0, np.cumsum(su)]
R = {}
for W in (5, 30):
    s = np.arange(29 * 1440, n - 2 * W, W)
    u = cu[s + W] - cu[s]; f = np.where(u > 0, (cs[s + W] - cs[s]) / np.where(u > 0, u, 1), np.nan)
    nxt = (lp[s + 2 * W - 1] - lp[s + W - 1]) * 1e4
    e = s + W - 1; trend = (lp[e] - lp[e - H]) / np.sqrt(daily_var[e] * 3); reg = rv60[e] / med[e]; day = s // 1440
    ok = np.isfinite(f) & np.isfinite(trend) & np.isfinite(reg)
    f, nxt, trend, reg, day = f[ok], nxt[ok], trend[ok], reg[ok], day[ok]
    lo, hi = np.quantile(f, [0.2, 0.8]); strong = (f <= lo) | (f >= hi); sgn = np.sign(f)
    t1, t2 = np.quantile(reg, [1 / 3, 2 / 3]); rg = np.digitize(reg, [t1, t2])
    rel = np.where(np.abs(trend) < 0.5, "no clear trend", np.where(np.sign(trend) == sgn, "with the trend", "against the trend"))
    cont = sgn * nxt
    out = {}
    for rl in ("against the trend", "no clear trend", "with the trend"):
        out[rl] = {}
        for k, vl in enumerate(("calm", "normal", "volatile")):
            m = strong & (rel == rl) & (rg == k)
            dm = pl.DataFrame({"d": day[m], "x": cont[m]}).group_by("d").agg(pl.col("x").mean())["x"].to_numpy()
            out[rl][vl] = dict(bp=round(float(cont[m].mean()), 2), t=round(float(dm.mean() / (dm.std() / np.sqrt(len(dm)))), 1), n=int(m.sum()))
    R[f"{W} min"] = out
    print(f"== {W}-minute windows: next window in the direction of the flow, bp (t, n)")
    for rl, row in out.items():
        print(f"  {rl:18} " + " | ".join(f"{vl}: {v['bp']:+5.2f} (t {v['t']:4}, n {v['n']})" for vl, v in row.items()))
(L15_RESULTS / "l15_flow_matrix.json").write_text(json.dumps(R, indent=1))
