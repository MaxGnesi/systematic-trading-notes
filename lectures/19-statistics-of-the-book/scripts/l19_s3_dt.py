"""Lecture 19 §3: for every sample of L19_OUT/s3/samples_DAY, the time to the next change of the mid (ms), and the number of book updates until then.
Output: L19_OUT/s3/dt_DAY.parquet."""
import sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
D = L19.S3
for f in sorted(D.glob("samples_*.parquet")):
    day = f.stem.replace("samples_", ""); S = pl.read_parquet(f, columns=["ts"])
    X = pl.read_parquet(L19.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).with_columns((pl.col("bid") + pl.col("ask")).alias("m2"))
    X = X.with_row_index("i").with_columns((pl.col("m2") != pl.col("m2").shift(1)).fill_null(True).alias("chg"))
    C = X.filter(pl.col("chg")).select(pl.col("ts").alias("t_chg"), pl.col("i").alias("i_chg"))
    S = S.join(X.select("ts", "i"), on="ts").sort("ts").join_asof(C, left_on="ts", right_on="t_chg", strategy="forward", allow_exact_matches=False)
    S.select("ts", (pl.col("t_chg") - pl.col("ts")).alias("dt_ms"), (pl.col("i_chg") - pl.col("i")).alias("n_upd")).write_parquet(D / f"dt_{day}.parquet")
print("ok")
