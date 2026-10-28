"""Lecture 17: the grid on the tape against the same days with their minutes shuffled, five years, one year at a time.
Steps 10-200 bp; the ladder reaches about 200 bp to each side at every step (levels = 200 / step), stop + restart, daily close, costs on.
Per step: daily means of every part (gross = round trips + inventory; gap; fees; funding; net), by year and in total."""
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

STEPS = [10, 25, 50, 100, 200]; WIDTH = 200
YEARS = [(f"{ONE_YEAR}-01", f"{ONE_YEAR}-12")] if ONE_YEAR else [("2021-10", "2021-12"), ("2022-01", "2022-12"), ("2023-01", "2023-12"), ("2024-01", "2024-12"), ("2025-01", "2025-12"), ("2026-01", "2026-09")]
frames = []
for a, b in YEARS:
    D = g.load(a, b)
    for st in STEPS:
        for sh in (False, True):
            df = g.run(D, st, n=max(1, round(WIDTH / st)), shuffle=sh, seed=1)
            frames.append(df.with_columns(pl.lit(st).alias("step"), pl.lit("shuffled" if sh else "tape").alias("path")))
    print(a[:4], "done", flush=True)
    del D
R = pl.concat(frames).with_columns(pl.from_epoch(pl.col("day").cast(pl.Int64) * 86400).dt.year().alias("year"))
R.write_parquet(L17_RESULTS / "l17_tape_vs_shuffled.parquet")
cols = ["gross", "trips_income", "inventory", "gap", "maker_fee", "taker_fee", "funding", "net", "trips", "stops", "ambiguous"]
T = R.group_by("step", "path").agg([pl.col(c).mean() for c in cols] + [pl.len().alias("days"), (pl.col("gross").std() / pl.len().sqrt()).alias("se")]).sort("step", "path")
pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250)
print(T)
W = R.pivot(on="path", index=["step", "day"], values="gross").with_columns((pl.col("tape") - pl.col("shuffled")).alias("diff"))
print(W.group_by("step").agg(pl.col("diff").mean().alias("tape_minus_shuffled"), (pl.col("diff").mean() / pl.col("diff").std() * pl.len().sqrt()).alias("t")).sort("step"))
Y = R.filter(pl.col("path") == "tape").group_by("step", "year").agg(pl.col("gross").mean(), pl.col("net").mean()).sort("step", "year")
print(Y.pivot(on="year", index="step", values="net"))
