"""Lecture 15 §2: does one-sided flow predict the price? Non-overlapping windows of W minutes; flow = net aggressive buying / dollars traded.
Windows sorted into fifths of flow; per fifth: the return during the window (impact) and over the next W minutes (continuation or reversal).
Volatility regime known in advance: the last hour's realised variance against its median over the past 28 days, in thirds.
Standard errors with days as clusters (mean of each day's returns per fifth)."""
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
lp = np.log(g["close"].to_numpy()); usd = g["usd"].to_numpy(); su = g["signed_usd"].to_numpy()
r1 = np.r_[0.0, np.diff(lp)]
rv60 = np.convolve(r1 ** 2, np.ones(60), "full")[:n]                        # realised variance of the last hour, ending at each minute
med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
R = {}
for W in (1, 5, 30):
    s = np.arange(28 * 1440, n - 2 * W, W)                                  # window [s, s+W); next window [s+W, s+2W)
    cu, cs = np.r_[0, np.cumsum(usd)], np.r_[0, np.cumsum(su)]
    u = cu[s + W] - cu[s]; f = np.where(u > 0, (cs[s + W] - cs[s]) / np.where(u > 0, u, 1), np.nan)
    now = (lp[s + W - 1] - lp[s - 1]) * 1e4; nxt = (lp[s + 2 * W - 1] - lp[s + W - 1]) * 1e4
    reg = rv60[s - 1] / med[s - 1]; day = s // 1440
    ok = np.isfinite(f) & np.isfinite(reg)
    f, now, nxt, reg, day = f[ok], now[ok], nxt[ok], reg[ok], day[ok]
    q = np.digitize(f, np.quantile(f, [0.2, 0.4, 0.6, 0.8]))
    t1, t2 = np.quantile(reg, [1 / 3, 2 / 3]); rg = np.digitize(reg, [t1, t2])
    out = {}
    for rlab, sel in (("all", np.ones(len(f), bool)), ("calm", rg == 0), ("normal", rg == 1), ("volatile", rg == 2)):
        row = {}
        for k in range(5):
            m = sel & (q == k)
            dm = pl.DataFrame({"d": day[m], "x": nxt[m]}).group_by("d").agg(pl.col("x").mean())["x"].to_numpy()
            row[f"fifth {k + 1}"] = dict(flow=round(float(np.median(f[m])), 3), during_bp=round(float(now[m].mean()), 2),
                                         next_bp=round(float(nxt[m].mean()), 2), next_se=round(float(dm.std() / np.sqrt(len(dm))), 2), n=int(m.sum()))
        top, bot = sel & (q == 4), sel & (q == 0)
        diff = pl.DataFrame({"d": np.r_[day[top], day[bot]], "x": np.r_[nxt[top], -nxt[bot]], "g": np.r_[np.ones(top.sum()), np.zeros(bot.sum())]})
        dd = diff.group_by("d", "g").agg(pl.col("x").mean()).group_by("d").agg(pl.col("x").sum())["x"].to_numpy()
        row["top minus bottom, next"] = dict(bp=round(float(nxt[top].mean() - nxt[bot].mean()), 2), t=round(float(dd.mean() / (dd.std() / np.sqrt(len(dd)))), 1))
        out[rlab] = row
    R[f"{W} min"] = out
    a = out["all"]
    print(f"{W:2} min | during: " + " ".join(f"{a[f'fifth {k}']['during_bp']:+6.1f}" for k in range(1, 6)) +
          " | next: " + " ".join(f"{a[f'fifth {k}']['next_bp']:+5.2f}" for k in range(1, 6)) +
          f" | top-bottom next {a['top minus bottom, next']['bp']:+.2f} bp (t {a['top minus bottom, next']['t']})" +
          " | by regime: " + " ".join(f"{r} {out[r]['top minus bottom, next']['bp']:+.2f} (t {out[r]['top minus bottom, next']['t']})" for r in ("calm", "normal", "volatile")), flush=True)
(L15_RESULTS / "l15_flow.json").write_text(json.dumps(R, indent=1))
