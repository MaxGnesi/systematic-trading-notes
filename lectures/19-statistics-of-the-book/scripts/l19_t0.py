"""Lecture 19 §4: the start of the cascade, T0, fixed by a rule: the first minute of 10 October whose one-minute change of the mid is larger than
any on the in-sample days (20 September - 9 October), from the per-minute frames of l19_book2.py. Output: L19_OUT/l19_T0.txt (ms since 1970, UTC)."""
import sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19


def moves(day):
    m = pl.read_parquet(L19.S3 / f"b2_min_{day}.parquet").sort("t").with_columns(((pl.col("bid") + pl.col("ask")) / 20).alias("mid"))
    return m.with_columns((pl.col("mid") - pl.col("mid").shift(1)).abs().alias("move"))


days = sorted(p.stem.replace("b2_min_", "") for p in L19.S3.glob("b2_min_*.parquet"))
largest = max(moves(d)["move"].max() for d in days if d < L19.CASC)
first = moves(L19.CASC).filter(pl.col("move") > largest).row(0, named=True)
(L19.OUT / "l19_T0.txt").write_text(str(first["t"]))
print(f"in-sample days {sum(d < L19.CASC for d in days)}, largest one-minute move ${largest:,.1f}; T0 =",
      pl.from_epoch(pl.Series([first["t"]]), time_unit="ms")[0], f"UTC, move ${first['move']:,.1f}")
