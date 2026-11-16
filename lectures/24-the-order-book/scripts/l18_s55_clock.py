"""Is the pull sawtooth through the minute a clock effect, or does the market simply move more at the start of each minute? Per day and second of
the minute: pull rate overall, pull rate among updates with a quiet previous second (mid moved < 0.5 bp), share of such quiet updates, traded volume."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
HERE = L18.OUT
rows = []
for f in sorted((HERE / "pulls").glob("*.parquet")):
    M = pl.read_parquet(f, columns=["ts", "pull", "sec", "move_bp", "vol"]).drop_nulls("move_bp")
    day_rate, day_q = M["pull"].mean(), M.filter(pl.col("move_bp") < 0.5)["pull"].mean(); day_vol = M["vol"].mean(); day_move = M["move_bp"].mean()
    g = M.group_by("sec").agg((pl.col("pull").mean() / day_rate).alias("all"), (pl.col("pull").filter(pl.col("move_bp") < 0.5).mean() / day_q).alias("quiet"),
                              (pl.col("move_bp").mean() / day_move).alias("move"), (pl.col("vol").mean() / day_vol).alias("vol"))
    rows.append(g.with_columns(pl.lit(f.stem[-10:]).alias("day")))
A = pl.concat(rows)
R = A.group_by("sec").agg(pl.col("all", "quiet", "move", "vol").median()).sort("sec")
pl.Config.set_tbl_rows(70); pl.Config.set_float_precision(2); print(R)
print("days where quiet-second rate at sec 0-4 exceeds sec 50-59:", A.group_by("day").agg(pl.col("quiet").filter(pl.col("sec") < 5).mean() > pl.col("quiet").filter(pl.col("sec") >= 50).mean())["quiet"].sum())
(HERE / "l18_s55_clock.json").write_text(json.dumps(R.to_dicts()))
