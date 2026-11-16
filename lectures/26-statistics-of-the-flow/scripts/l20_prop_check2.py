"""Audit of H3, part 2: does the mid respond to a taker order at the next book update, or over several? On 1 Oct, for taker orders of at least
2 BTC whose trades walked at least one tick (worst price beyond the best), the signed change of the mid from the last update before the order to
each of the next k updates, k = -3..10; and the same for Binance-first moves is not attempted here. Also: where does the order's worst price sit
relative to the book after the next update (has the book already moved there)?"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("prop_check2")

D = sys.argv[1] if len(sys.argv) > 1 else "2025-10-01"
S = pl.read_parquet(L20.STATE / f"{D}.parquet", columns=["ts", "bid", "ask"]).sort("ts").group_by("ts", maintain_order=True).agg(pl.col("bid").last(), pl.col("ask").last())
U = S["ts"].to_numpy(); M = (S["bid"].to_numpy() + S["ask"].to_numpy()) / 2.0      # ticks
O = pl.read_parquet(L20.ORD / f"bybit_{D}.parquet").drop_nulls("mid2").sort("ts")
for lo, hi in ((0.0, 0.1), (0.1, 2.0), (2.0, 1e9)):
    o = O.filter((pl.col("size") >= lo) & (pl.col("size") < hi))
    j = np.searchsorted(U, o["ts"].to_numpy(), side="left") - 1                     # last update strictly before the order
    s = o["side"].to_numpy(); ok = (j >= 3) & (j + 10 < len(U)); j, s = j[ok], s[ok]
    base = M[j]; prof = [float(np.mean(s * (M[j + k] - base))) for k in range(-3, 11)]
    gap = (U[j + 1] - o["ts"].to_numpy()[ok])
    print(f"size {lo}-{hi} BTC, n {ok.sum()}: mid change in ticks at update k (0 = last before):", [round(v, 1) for v in prof],
          f"| ms from order to next update: median {np.median(gap):.0f}")
