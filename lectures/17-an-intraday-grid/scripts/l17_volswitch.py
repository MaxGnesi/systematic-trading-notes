"""Lecture 17: does a volatility switch known at the time keep the grid out of the runs? No look-ahead anywhere.
Hourly volatility = sum of squared 1-minute log returns of the last price in the hour. Ratio = the last FINISHED hour's volatility / the median of
the previous 28 days of hourly volatility (672 hours, the current hour excluded). Day-level state: yesterday's volatility / median of the 28 days before.
Day split: yesterday's ratio in fixed bins (<0.75, 0.75-1, 1-1.5, 1.5-2, >2). Switch: grid on only while the last finished hour's ratio is below K
(pre-fixed 1.5, 2, 3); switched off it closes at market and pauses, back on it restarts at the price.
Grid as l17_tape_vs_shuffled.py (ladder about 200 bp each side, stop + restart, daily close, costs). In sample 2021-24, out of sample 2025-26."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l17_grid as g


STEPS = [10, 25, 50, 100, 200]; WIDTH = 200; KS = [1.5, 2.0, 3.0]
YEARS = [(f"{ONE_YEAR}-01", f"{ONE_YEAR}-12")] if ONE_YEAR else [("2021-10", "2021-12"), ("2022-01", "2022-12"), ("2023-01", "2023-12"), ("2024-01", "2024-12"), ("2025-01", "2025-12"), ("2026-01", "2026-09")]

# 1. hourly volatility over the whole sample (light: one year of seconds at a time)
hv = []
for a, b in YEARS:
    s, hb, ls, last, fs, fr = g.load(a, b)
    m = pl.DataFrame({"m": s // 60, "p": last}).group_by("m").agg(pl.col("p").last()).sort("m")
    m = m.with_columns(pl.col("p").log().diff().alias("r")).with_columns((pl.col("m") // 60).alias("h"))
    hv.append(m.group_by("h").agg((pl.col("r") ** 2).sum().alias("rv")))
H = pl.concat(hv).group_by("h").agg(pl.col("rv").sum()).sort("h")
H = H.with_columns(pl.col("rv").shift(1).rolling_median(672, min_samples=336).alias("med"))
H = H.with_columns((pl.col("rv") / pl.col("med")).alias("ratio"))
ratio = dict(zip(H["h"].to_list(), H["ratio"].to_list()))
D = H.with_columns((pl.col("h") // 24).alias("d")).group_by("d").agg(pl.col("rv").sum()).sort("d")
D = D.with_columns((pl.col("rv").shift(1) / pl.col("rv").shift(2).rolling_median(28, min_samples=14)).alias("yday"))
yday = dict(zip(D["d"].to_list(), D["yday"].to_list()))

# 2. grids: always on vs switched, tape only
rows = []
for a, b in YEARS:
    data = g.load(a, b); s = data[0]
    hr = np.array([ratio.get(h - 1, np.nan) or np.nan for h in range(s[0] // 3600, s[-1] // 3600 + 1)], dtype=float)
    last_ratio = hr[s // 3600 - s[0] // 3600]
    for st in STEPS:
        n = max(1, round(WIDTH / st))
        base = g.run(data, st, n=n).with_columns(pl.lit("always on").alias("rule"))
        rows.append(base.with_columns(pl.lit(st).alias("step")))
        for K in KS:
            on = ~(last_ratio >= K)                                   # unknown ratio (start of sample) = on
            rows.append(g.run(data, st, n=n, on=on).with_columns(pl.lit(f"off above {K}").alias("rule"), pl.lit(st).alias("step")))
    print(a[:4], "done", flush=True)
    del data
R = pl.concat(rows).with_columns(pl.col("day").cast(pl.Int64), pl.from_epoch(pl.col("day").cast(pl.Int64) * 86400).dt.year().alias("year"))
R = R.with_columns(pl.col("day").replace_strict(yday, default=None).alias("yday"))
R.write_parquet(L17_RESULTS / "l17_volswitch.parquet")
R = R.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("IS 2021-24")).otherwise(pl.lit("OOS 2025-26")).alias("period"))
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250)
print(R.group_by("step", "rule", "period").agg(pl.col("gross").mean().round(3), pl.col("net").mean().round(3), (pl.col("net").mean() / pl.col("net").std() * pl.len().sqrt()).round(1).alias("t_net"),
      pl.col("net").quantile(0.01).round(2).alias("worst1pct"), pl.col("off_share").mean().round(3), pl.col("trips").mean().round(1)).sort("step", "period", "rule"))
B = R.filter(pl.col("rule") == "always on").with_columns(pl.col("yday").cut([0.75, 1.0, 1.5, 2.0]).alias("yday_bin"))
print(B.group_by("step", "yday_bin").agg(pl.col("gross").mean().round(3), pl.col("net").mean().round(3), pl.len().alias("days")).sort("step", "yday_bin"))
