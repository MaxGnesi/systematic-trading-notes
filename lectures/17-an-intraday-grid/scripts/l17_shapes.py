"""Lecture 17 §4: the size profile and the width, on the tape, pre-fixed. Shapes (Lecture 16, §8): uniform, V-shaped (more size further out),
bell-shaped (more near the centre), bimodal (a bell on each side of the price, a few levels away), every shape with the same capital in a full ladder. Steps 25, 50, 100, 200 bp; width: the ladder reaching
100, 200 or 400 bp each way (levels = width / step, at least 1). Stop + restart, daily close, maker 2 / taker 5 bp, funding.
In sample 2021-24, out of sample 2025-26."""
import sys
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
import l17_grid as g, tape


STEPS = [25, 50, 100, 200]; WIDTHS = [100, 200, 400]; SHAPES = ["uniform", "V-shaped", "bell-shaped", "bimodal"]
YEARS = [(f"{ONE_YEAR}-01", f"{ONE_YEAR}-12")] if ONE_YEAR else [("2021-10", "2021-12"), ("2022-01", "2022-12"), ("2023-01", "2023-12"), ("2024-01", "2024-12"), ("2025-01", "2025-12"), ("2026-01", "2026-09")]
rows = []
for a, b in YEARS:
    tape.wait_for_memory(2.0)
    data = g.load(a, b)
    for st in STEPS:
        for wd in WIDTHS:
            n = max(1, round(wd / st))
            for sh in (SHAPES if n >= 2 else ["uniform"]):
                rows.append(g.run(data, st, n=n, sizes=sh).with_columns(pl.lit(sh).alias("shape"), pl.lit(st).alias("step"), pl.lit(wd).alias("width"), pl.lit(n).alias("levels")))
    print(a[:4], "done", flush=True)
    del data
R = pl.concat(rows).with_columns(pl.from_epoch(pl.col("day").cast(pl.Int64) * 86400).dt.year().alias("year"))
R.write_parquet(L17_RESULTS / "l17_shapes.parquet")
R = R.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("IS")).otherwise(pl.lit("OOS")).alias("p"))
A = R.group_by("step", "width", "levels", "shape", "p").agg(pl.col("gross").mean().round(3).alias("g"), pl.col("net").mean().round(3).alias("n"),
     (pl.col("net").mean() / pl.col("net").std() * np.sqrt(365)).round(1).alias("sr"), pl.col("net").quantile(0.01).round(1).alias("w1"),
     pl.col("trips_income").mean().round(3).alias("ti"), pl.col("inventory").mean().round(3).alias("inv"))
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(20)
print(A.pivot(on="p", index=["step", "width", "levels", "shape"], values=["g", "n", "sr", "w1", "ti", "inv"]).sort("step", "width", "shape"))
