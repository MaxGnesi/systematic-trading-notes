"""The turn of the minute at 100 ms resolution: pull rate and mid move (vs the previous update) per 100 ms bucket from second 58 to second 3,
relative to the day's averages, median over the 45 days."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
HERE = L18.OUT
rows = []
for f in sorted((HERE / "pulls").glob("*.parquet")):
    M = pl.read_parquet(f, columns=["ts", "pull", "mid"]).sort("ts").with_columns((pl.col("mid") / pl.col("mid").shift(1) - 1).abs().mul(1e4).alias("step"))
    r, s = M["pull"].mean(), M["step"].mean()
    M = M.with_columns((((pl.col("ts") % 60_000) + 2_000) % 60_000 // 100).alias("b"))   # bucket 0 = second 58.0
    rows.append(M.filter(pl.col("b") < 60).group_by("b").agg((pl.col("pull").mean() / r).alias("pull"), (pl.col("step").mean() / s).alias("step")))
R = pl.concat(rows).group_by("b").agg(pl.col("pull", "step").median()).sort("b").with_columns(((pl.col("b") * 100 - 2000) / 1000).alias("t_s"))
pl.Config.set_tbl_rows(70); pl.Config.set_float_precision(2); print(R.select("t_s", "pull", "step"))
(HERE / "l18_s55_turn.json").write_text(json.dumps(R.to_dicts()))
