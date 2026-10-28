"""Lecture 17: the per-second table the grid simulator runs on, built once from the tape (Lecture 12), one month at a time.
For every second with trades: the highest price paid by aggressive buyers (a resting sell at L is filled for sure only if a buyer paid more than L),
the lowest price received by aggressive sellers (a resting buy at L is filled for sure only if a seller got less than L), the last price,
and the dollars traded. Months already built are skipped; each month waits for free memory first."""
import sys
from pathlib import Path
import polars as pl
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
import tape

SYM = "BTCUSDT"; OUT = tape.ROOT / "interim" / "l17" / "seconds"; OUT.mkdir(parents=True, exist_ok=True)
for ym in tape.months("2021-10", "2026-09"):
    f = OUT / f"{ym}.parquet"
    if f.exists(): continue
    tape.wait_for_memory(1.5)
    q = (pl.scan_parquet(tape.source(SYM, ym))
           .select((pl.col("transact_time") // 1000).alias("s"), "price", "quantity", "is_buyer_maker", "agg_trade_id")
           .group_by("s").agg(pl.col("price").filter(~pl.col("is_buyer_maker")).max().alias("hi_buy"),
                              pl.col("price").filter(pl.col("is_buyer_maker")).min().alias("lo_sell"),
                              pl.col("price").sort_by("agg_trade_id").last().alias("last"),
                              (pl.col("price") * pl.col("quantity")).sum().alias("usd"))
           .sort("s"))
    q.collect(engine="streaming").write_parquet(f)
    print(ym, "done", flush=True)
