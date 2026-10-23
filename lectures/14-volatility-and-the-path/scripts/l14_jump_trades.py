"""Lecture 14 §5.1: are jumps moves without trades? Each one-minute move divided by the local diffusive volatility (bipower over the past hour);
for ordinary minutes, large moves and jumps: the trades and dollars of the minute against the day's median minute."""
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
m = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close", "trades", "usd").collect().sort("time")
m = m.with_columns(pl.col("close").log().diff().alias("r"), pl.col("time").dt.date().alias("day"))
m = m.with_columns((np.pi / 2 * (pl.col("r").abs() * pl.col("r").abs().shift(1))).rolling_mean(60).shift(1).sqrt().alias("sig"))
m = m.join(m.group_by("day").agg(pl.col("trades").median().alias("tmed"), pl.col("usd").median().alias("umed")), on="day")
m = m.with_columns((pl.col("r") / pl.col("sig")).alias("z"), (pl.col("trades") / pl.col("tmed")).alias("tr"), (pl.col("usd") / pl.col("umed")).alias("ur")).drop_nulls(["z"]).filter(pl.col("sig") > 0)
R = {}
for lo, hi, lab in ((0, 1, "ordinary, below 1"), (2, 4, "large, 2 to 4"), (4, 8, "jumps, 4 to 8"), (8, 1e9, "jumps, above 8")):
    s = m.filter(pl.col("z").abs().is_between(lo, hi, closed="left")); tr = s["tr"].to_numpy(); ur = s["ur"].to_numpy()
    R[lab] = dict(minutes=s.height, trades_vs_median=round(float(np.median(tr)), 1), share_fewer_trades=round(float(np.mean(tr < 1)), 3), dollars_vs_median=round(float(np.median(ur)), 1))
(L14_RESULTS / "l14_jump_trades.json").write_text(json.dumps(R, indent=1))
if __name__ == "__main__":
    print(json.dumps(R, indent=1))
