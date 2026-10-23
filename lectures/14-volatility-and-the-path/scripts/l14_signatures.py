"""Lecture 14 §5: do other volatility measures have the same signature as realised variance?
For bar lengths from 1 second to 1 hour: realised variance (sum of squared bar returns), bipower variation (pi/2 sum |r_i||r_i-1|) and the
realised range (sum over bars of ln(high/low)^2 / (4 ln 2), Parkinson per bar). Each divided by realised variance at one minute on the same days.
Below a minute from the trades of every 31st day; from a minute on, from one-minute bars over all days."""
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
import tape

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM; LN2 = np.log(2)


def measures(bars):
    """bars: DataFrame with open/high/low/close per bar in time order (one day)."""
    lc = np.log(bars["close"].to_numpy()); r = np.diff(lc)
    rv = float((r ** 2).sum()); bv = float(np.pi / 2 * (np.abs(r[1:]) * np.abs(r[:-1])).sum())
    rr = float((np.log(bars["high"] / bars["low"]).to_numpy() ** 2).sum() / (4 * LN2))
    return rv, bv, rr


R = {"short": {}, "long": {}}
# below a minute: trades of every 31st day
days = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).select("day").collect()["day"].to_list()[::31]
SEC = (1, 5, 10, 30, 60)
acc = {s: [] for s in SEC}
for d0 in days:
    tape.wait_for_memory(1.5)
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price").collect())
    for s in SEC:
        b = t.group_by((pl.col("transact_time") // (s * 1000)).alias("k"), maintain_order=True).agg(
            pl.col("price").first().alias("open"), pl.col("price").max().alias("high"), pl.col("price").min().alias("low"), pl.col("price").last().alias("close"))
        acc[s].append(measures(b))
base = np.array([x[0] for x in acc[60]])                                     # realised variance at one minute, same days
for s in SEC:
    m = np.array(acc[s])
    R["short"][f"{s}s"] = {k: round(float(np.mean(m[:, i]) / base.mean()), 3) for i, k in enumerate(("realised variance", "bipower", "realised range"))}
print("below a minute", R["short"], flush=True)

# from a minute on: all days, one-minute bars aggregated
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "open", "high", "low", "close").collect().sort("time")
m1 = m1.with_columns(pl.col("time").dt.date().alias("day"))
full = m1.group_by("day").len().filter(pl.col("len") == 1440)["day"]
m1 = m1.filter(pl.col("day").is_in(full))
out = {}
for k in (1, 5, 15, 30, 60):
    b = (m1.group_by(pl.col("time").dt.truncate(f"{k}m").alias("bar"), maintain_order=True)
           .agg(pl.col("day").first(), pl.col("open").first(), pl.col("high").max(), pl.col("low").min(), pl.col("close").last()).sort("bar"))
    b = b.with_columns(pl.col("close").log().diff().alias("r"), pl.col("close").log().diff().abs().shift(1).alias("ra"))
    g = b.group_by("day").agg((pl.col("r") ** 2).sum().alias("rv"), (np.pi / 2 * pl.col("r").abs() * pl.col("ra")).sum().alias("bv"),
                              ((pl.col("high") / pl.col("low")).log() ** 2 / (4 * LN2)).sum().alias("rr"))
    out[k] = g
base = out[1]["rv"].mean()
for k, g in out.items():
    R["long"][f"{k}m"] = {lab: round(float(g[c].mean() / base), 3) for lab, c in (("realised variance", "rv"), ("bipower", "bv"), ("realised range", "rr"))}
print("a minute and more", R["long"], flush=True)
(L14_RESULTS / "l14_signatures.json").write_text(json.dumps(R, indent=1))
