"""Lecture 14 §2: what a candle loses.
1. Which came first, the high or the low: two common guesses ('the bar's direction', 'the open nearer the high') against the tape, by bar length,
   and on a simulated random walk.
2. Stop and target at the same distance from the open, as a share of the typical hourly range (past 28 days): bars touching both, and how
   often the direction guess picks the right one (truth from the first minute in which each level was touched).
3. The distance travelled: the sum of absolute one-minute moves of an hour, divided by its range."""
import json, sys
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

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "open", "high", "low", "close").collect().sort("time")
R = {"order": {}, "random_walk": {}, "stop_target": {}}

# 1. which came first, on the tape
for mins, lab in ((5, "5 min"), (60, "1 hour"), (1440, "1 day")):
    b = (m1.with_columns(pl.col("time").dt.truncate(f"{mins}m").alias("bar"))
           .group_by("bar").agg(pl.col("open").first(), pl.col("close").last(), pl.col("high").max().alias("H"), pl.col("low").min().alias("L"),
                                pl.col("time").filter(pl.col("high") == pl.col("high").max()).first().alias("tH"),
                                pl.col("time").filter(pl.col("low") == pl.col("low").min()).first().alias("tL"), pl.len().alias("n"))
           .filter((pl.col("n") == mins) & (pl.col("tH") != pl.col("tL"))))
    hf = (b["tH"] < b["tL"]).to_numpy(); o, h, l, c = (b[x].to_numpy() for x in ("open", "H", "L", "close"))
    R["order"][lab] = dict(bars=b.height, direction_rule=round(float(np.mean((c < o) == hf)), 3), open_nearer=round(float(np.mean(((h - o) < (o - l)) == hf)), 3))
# ... and on a random walk
rng = np.random.default_rng(1)
accA, accB = [], []
for _ in range(10):
    x = np.c_[np.zeros(20000), np.cumsum(rng.standard_normal((20000, 240)), axis=1)]
    hf = x.argmax(1) < x.argmin(1); o, c = x[:, 0], x[:, -1]
    accA.append(np.mean(((x.max(1) - o) < (o - x.min(1))) == hf)); accB.append(np.mean((c < o) == hf))
R["random_walk"] = dict(direction_rule=round(float(np.mean(accB)), 3), open_nearer=round(float(np.mean(accA)), 3))

# 2. stop and target on hourly bars
m1 = m1.with_columns(pl.col("time").dt.truncate("1h").alias("bar"))
hb = (m1.group_by("bar").agg(pl.col("open").first().alias("O"), pl.col("close").last().alias("C"), pl.col("high").max().alias("H"), pl.col("low").min().alias("L"),
                             pl.len().alias("n")).sort("bar").filter(pl.col("n") == 60))
typ = pl.Series(np.log(hb["H"] / hb["L"]).to_numpy()).shift(1).rolling_median(28 * 24, min_samples=7 * 24).to_numpy()
hb = hb.with_columns(pl.Series("typ", typ)).drop_nulls("typ")
mm = m1.select("bar", "high", "low").join(hb.select("bar", "O", "typ"), on="bar").with_columns(pl.int_range(pl.len()).over("bar").alias("k"))
for f in (0.25, 0.5, 1.0):
    t = (mm.with_columns((pl.col("O") * np.exp(f * pl.col("typ"))).alias("up"), (pl.col("O") * np.exp(-f * pl.col("typ"))).alias("dn"))
           .group_by("bar").agg(pl.col("k").filter(pl.col("high") >= pl.col("up")).min().alias("ku"), pl.col("k").filter(pl.col("low") <= pl.col("dn")).min().alias("kd"))
           .join(hb.select("bar", "O", "C"), on="bar"))
    both = t.filter(pl.col("ku").is_not_null() & pl.col("kd").is_not_null()); bb = both.filter(pl.col("ku") != pl.col("kd"))
    up_first = (bb["ku"] < bb["kd"]).to_numpy(); guess = ~(bb["C"] > bb["O"]).to_numpy()
    R["stop_target"][f] = dict(touch_both=round(both.height / t.height, 3), direction_right=round(float(np.mean(guess == up_first)), 3))

# 3. distance travelled within an hour, over its range
a = m1.with_columns(pl.col("close").log().diff().abs().alias("a"))
h = a.group_by("bar").agg(pl.col("a").sum().alias("path"), (pl.col("high").max().log() - pl.col("low").min().log()).alias("rng"), pl.len().alias("n")).filter(pl.col("n") == 60)
r = (h["path"] / h["rng"]).to_numpy(); r = r[np.isfinite(r)]
mid = h.filter(pl.col("rng").is_between(pl.col("rng").quantile(0.45), pl.col("rng").quantile(0.55)))
R["path_over_range"] = dict(median=round(float(np.median(r)), 1), same_range_p10=round(float((mid["path"] / mid["rng"]).quantile(0.1)), 1),
                            same_range_p90=round(float((mid["path"] / mid["rng"]).quantile(0.9)), 1))
(L14_RESULTS / "l14_s2.json").write_text(json.dumps(R, indent=1))
if __name__ == "__main__":
    print(json.dumps(R, indent=1))
