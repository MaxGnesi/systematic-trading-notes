"""Lecture 17 §7: the maker rebate at which the grid breaks even, from l17_directions.parquet (fees maker 2 bp, taker 5 bp). The net result with a
maker fee of zero is net + maker fees; the dollars filled passively per day are maker fees / 2 bp; the break-even rebate is the loss at a zero maker fee
divided by those dollars, in bp (the exchange would pay it on every resting fill). The taker fee at stops, switches and closes stays at 5 bp."""
import json
from pathlib import Path
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
import polars as pl


R = pl.read_parquet(L17_RESULTS / "l17_directions.parquet").filter(pl.col("rule").is_in(["always on", "vol switch (base)", "skew, sign"]))
R = R.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("2021-24")).otherwise(pl.lit("2025-26")).alias("p"))
A = R.group_by("rule", "step", "p").agg(((pl.col("net") + pl.col("maker_fee")).mean()).alias("net_at_zero"), (pl.col("maker_fee") / 2).mean().alias("per_bp"),
                                         pl.col("taker_fee").mean().alias("taker"), pl.col("gross").mean().alias("gross"))
A = A.with_columns((-pl.col("net_at_zero") / pl.col("per_bp")).alias("rebate_bp"), (pl.col("per_bp") * 100).alias("filled_x_capital")).sort("rule", "step", "p")
(L17_RESULTS / "l17_s7.json").write_text(json.dumps(A.to_dicts(), indent=1))
pl.Config.set_tbl_rows(30); pl.Config.set_float_precision(2)
print(A.pivot(on="p", index=["rule", "step"], values=["rebate_bp", "filled_x_capital", "gross", "taker"]))
