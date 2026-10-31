"""Lecture 20, H7: the Lecture 19 puzzle. On each in-sample day, at the samples of Lecture 19 (L19_OUT/s3/samples_DAY.parquet: one book state per
interval between mid changes, spread one tick), the rank correlation of Bybit's I1 with the gap Binance price - Bybit mid, the Binance price taken
(a) as its last trade, as in Lecture 19 (H18b), (b) as the midpoint of its last taker buy and last taker sell within the past 1 s (size-weighted
price of each taker order), which removes the bounce between Binance's bid and ask. Samples without both a buy and a sell in the past 1 s are left
out of (b), and (a) is reported on the same samples as well. Output: L20_OUT/s3/puzzle.json. Usage: python l20_s3_puzzle.py [DAY ...]"""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
DAYS = L20.day_list()


def spear(x, y): return float(np.corrcoef(pl.Series(x).rank().to_numpy(), pl.Series(y).rank().to_numpy())[0, 1])


res = {}
for d in DAYS:
    s = pl.read_parquet(L20.S3_19 / f"samples_{d}.parquet").sort("ts").select("ts", "I1")
    st = pl.read_parquet(L20.STATE / f"{d}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 20).alias("mid")).sort("ts")
    last = pl.read_parquet(L20.BN / f"{d}.parquet").rename({"price": "bn"}).sort("ts")
    bo = pl.read_parquet(L20.ORD / f"binance_{d}.parquet")
    buy = bo.filter(pl.col("side") == 1).select("ts", pl.col("price").alias("pb"), pl.col("ts").alias("tb")).sort("ts")
    sell = bo.filter(pl.col("side") == -1).select("ts", pl.col("price").alias("ps"), pl.col("ts").alias("ts_s")).sort("ts")
    w = s.join_asof(st, on="ts").join_asof(last, on="ts").join_asof(buy, on="ts").join_asof(sell, on="ts").drop_nulls()
    w = w.with_columns((pl.col("bn") - pl.col("mid")).alias("gap_last"), ((pl.col("pb") + pl.col("ps")) / 2 - pl.col("mid")).alias("gap_mid"),
                       ((pl.col("ts") - pl.col("tb") <= 1000) & (pl.col("ts") - pl.col("ts_s") <= 1000)).alias("fresh"))
    f = w.filter(pl.col("fresh"))
    res[d] = dict(n=w.height, n_fresh=f.height, rho_last_all=spear(w["I1"], w["gap_last"]), rho_last=spear(f["I1"], f["gap_last"]), rho_mid=spear(f["I1"], f["gap_mid"]))
    print(d, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[d].items()}, flush=True)
(OUT / f"{L20.tag()}puzzle.json").write_text(json.dumps(res))
