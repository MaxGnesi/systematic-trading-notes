"""Lecture 17 §4: the levers, on the tape, all pre-fixed. Base: the grid of §3 (ladder about 200 bp each side, stop + restart, daily close, maker 2 /
taker 5 bp, funding), steps 25, 50, 100, 200 bp. (1) Step x levels per side: 2, 4, 8 levels at every step (reach = levels x step). (2) Exits, on the
base: stop + restart / stop, then off for the rest of the day / hold at the cap (no stop). (3) Refresh, on the base: the ladder re-centred every hour or
every 4 hours (close at market and lay a new ladder: the grid is switched off for one second at each refresh), against once a day.
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


STEPS = [25, 50, 100, 200]; WIDTH = 200
YEARS = [(f"{ONE_YEAR}-01", f"{ONE_YEAR}-12")] if ONE_YEAR else [("2021-10", "2021-12"), ("2022-01", "2022-12"), ("2023-01", "2023-12"), ("2024-01", "2024-12"), ("2025-01", "2025-12"), ("2026-01", "2026-09")]
rows = []
for a, b in YEARS:
    tape.wait_for_memory(2.0)
    data = g.load(a, b); s = data[0]
    first = np.r_[True, np.diff(s // 3600) != 0]; first4 = np.r_[True, np.diff(s // 14400) != 0]
    refresh = {"refresh every hour": ~(first & (s % 86400 >= 3600)), "refresh every 4 hours": ~(first4 & (s % 86400 >= 14400))}
    for st in STEPS:
        nb = max(1, round(WIDTH / st))
        V = {f"levels {n}": dict(n=n) for n in (2, 4, 8)}
        V["base"] = dict(n=nb)
        V["stop, off for the day"] = dict(n=nb, restart=1); V["hold at the cap"] = dict(n=nb, stop=False)
        for k, on in refresh.items(): V[k] = dict(n=nb, on=on)
        for name, kw in V.items():
            rows.append(g.run(data, st, **kw).with_columns(pl.lit(name).alias("rule"), pl.lit(st).alias("step"), pl.lit(kw["n"]).alias("levels")))
    print(a[:4], "done", flush=True)
    del data
R = pl.concat(rows).with_columns(pl.from_epoch(pl.col("day").cast(pl.Int64) * 86400).dt.year().alias("year"))
R.write_parquet(L17_RESULTS / "l17_levers.parquet")
R = R.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("IS")).otherwise(pl.lit("OOS")).alias("period"))
A = R.group_by("step", "rule", "levels", "period").agg(pl.col("gross").mean(), pl.col("net").mean(),
                                                     (pl.col("net").mean() / pl.col("net").std() * np.sqrt(365)).alias("sharpe"), pl.col("net").quantile(0.01).alias("w1"))
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_float_precision(3)
print(A.pivot(on="period", index=["step", "rule", "levels"], values=["gross", "net", "sharpe", "w1"]).sort("step", "rule", "levels"))
