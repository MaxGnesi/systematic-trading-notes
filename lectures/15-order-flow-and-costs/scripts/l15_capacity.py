"""Lecture 15 §7: capacity. (1) Daily traded volume V and daily volatility sigma of BTCUSDT, 2021-2026. (2) The shape of impact against size measured as a
share of the day's volume: in windows of 5, 15 and 60 minutes, the net aggressive buying Q (dollars) over V (28-day median daily volume, known before) and
the price move during the window in the direction of Q over sigma (square root of the 28-day median daily variance); binned by Q/V, log-log slope.
This is aggregate impact, a crowd of traders, not one trader's metaorder. (3) Funding paid by a long position, per day held."""
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
lp = np.log(g["close"].to_numpy()); r1 = np.r_[0.0, np.diff(lp)]; usd = g["usd"].to_numpy(); sus = g["signed_usd"].to_numpy()
V = pl.Series(usd).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()          # typical daily volume, known before
sig = np.sqrt(pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy())

# (1) per day: volume and volatility
day = (pl.DataFrame({"time": g["time"], "usd": usd, "r2": r1 ** 2}).group_by(pl.col("time").dt.date().alias("day"))
       .agg(pl.col("usd").sum().alias("V"), pl.col("r2").sum().sqrt().alias("sigma")).sort("day"))
yr = day.group_by(pl.col("day").dt.year().alias("year")).agg((pl.col("V").median() / 1e9).round(1).alias("V_bn_median"), (pl.col("sigma").median() * 1e4).round(0).alias("sigma_bp_median")).sort("year")

# (2) impact shape
cs = lambda x: np.r_[0.0, np.cumsum(x)]; c_s = cs(sus)
res = {"by_year": yr.to_dicts(), "shape": {}}
for W in (5, 15, 60):
    s_ = np.arange(28 * 1440, n - W, W); Q = c_s[s_ + W] - c_s[s_]; ret = lp[s_ + W - 1] - lp[s_ - 1]
    x = np.abs(Q) / V[s_]; y = np.sign(Q) * ret / sig[s_]; ok = np.isfinite(x) & np.isfinite(y) & (x > 0)
    x, y = x[ok], y[ok]
    edges = np.quantile(x, np.linspace(0, 1, 21)); b = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, 19)
    bx = np.array([np.median(x[b == k]) for k in range(20)]); by = np.array([y[b == k].mean() for k in range(20)])
    top = bx > np.quantile(x, 0.5)                                              # slope on the upper half of sizes, where the price move is clearly positive
    slope_all = np.polyfit(np.log(bx[by > 0]), np.log(by[by > 0]), 1)[0]; slope_top = np.polyfit(np.log(bx[top]), np.log(by[top]), 1)[0]
    res["shape"][f"{W} min"] = dict(n=int(len(x)), bins_x=bx.tolist(), bins_y=by.tolist(), slope_all=round(float(slope_all), 2), slope_upper=round(float(slope_top), 2),
                                    y_at_0p1pct=float(np.interp(np.log(1e-3), np.log(bx), by)))

# (3) funding paid by a long position
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").filter(pl.col("time") >= pl.datetime(2021, 10, 1))
fy = (fr.group_by(pl.col("time").dt.year().alias("year")).agg((pl.col("fundingRate").sum() / pl.col("time").dt.date().n_unique() * 1e4).round(2).alias("bp_per_day_long"),
                                                              (pl.col("fundingRate") > 0).mean().round(3).alias("share_longs_pay")).sort("year"))
res["funding"] = fy.to_dicts()
(L15_RESULTS / "l15_capacity.json").write_text(json.dumps(res, indent=1, default=str))
print(yr); print(fy)
for W, r in res["shape"].items():
    print(W, "n", r["n"], "log-log slope, all bins with a positive move:", r["slope_all"], " upper half of sizes:", r["slope_upper"], " move at Q/V = 0.1%:", round(r["y_at_0p1pct"], 3), "sigma")
    print("   Q/V bins:", " ".join(f"{a:.1e}:{b:+.3f}" for a, b in zip(r["bins_x"][::3], r["bins_y"][::3])))
