"""Lecture 14 §6: does the bias of the duration (range-bar count) estimator depend on its settings?
Range bars on prices sampled every 0.1, 1, 5, 30 seconds (VWAP of the interval), with R set for 12, 48 or 192 bars a day from the day's own
one-minute realised variance (R = sqrt(RV / n), so that a bias of the method, not of the threshold forecast, is measured). Estimate: count x R^2 / 2.
Ratio to the day's one-minute realised variance, median over every 31st day."""
import json, sys
from datetime import datetime, timezone
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
import tape, bars

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
RES = (100, 1000, 5000, 30000); TARGET = (12, 48, 192)
days = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).select("day").collect()["day"].to_list()[::31]
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time").with_columns(pl.col("close").log().diff().alias("r"), pl.col("time").dt.date().alias("day"))
rv = dict(m1.group_by("day").agg((pl.col("r") ** 2).sum()).rows())
acc = {(r, n): [] for r in RES for n in TARGET}
for d0 in days:
    tape.wait_for_memory(1.5)
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price", "quantity").collect())
    ts, px, q = t["transact_time"].to_numpy(), t["price"].to_numpy(), t["quantity"].to_numpy()
    for res in RES:
        b = ts // res; first = np.r_[True, b[1:] != b[:-1]]; idx = np.cumsum(first) - 1
        lp = np.log(np.bincount(idx, px * q) / np.bincount(idx, q))
        for n in TARGET:
            R = np.sqrt(rv[d0] / n); cnt = len(bars._range_ends(lp, R))
            acc[(res, n)].append(cnt * R ** 2 / 2 / rv[d0])
out = {f"{res / 1000:g} s, {n} bars/day": round(float(np.median(v)), 3) for (res, n), v in acc.items()}
print(json.dumps(out, indent=1))
(L14_RESULTS / "l14_duration_bias.json").write_text(json.dumps(out, indent=1))
