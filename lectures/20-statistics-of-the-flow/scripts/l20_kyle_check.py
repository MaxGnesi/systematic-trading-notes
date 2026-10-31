"""Lecture 20, follow-up on Kyle's lambda in the early-warning table: is the 15-minute slope dominated by estimation noise in quiet minutes?
Per 15-minute block on all 45 days: OLS slope of the mid change on Bybit's TI over 10-second intervals, its standard error, R2, volume,
average depth at the best. Output: L20_OUT/s4/kyle_blocks.parquet."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("kyle_check")

DAYS = L20.days(); rows = []
for d in DAYS:
    d0 = int(np.datetime64(f"{d}T00:00:00", "s").astype(np.int64))
    sec = pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "mid2", "reset", "q_best", "depth10"]).filter((pl.col("sec") >= d0) & (pl.col("sec") < d0 + 86400))
    k = sec.with_columns((pl.col("sec") // 10).alias("k")).group_by("k").agg(pl.col("mid2").last(), pl.col("reset").max(), pl.col("q_best").mean(), pl.col("depth10").mean()).sort("k")
    k = k.with_columns(((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"), (pl.col("k") - pl.col("k").shift(1)).alias("dk"))
    O = pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size"])
    t = O.group_by((pl.col("ts") // 10_000).alias("k")).agg((pl.col("side") * pl.col("size")).sum().alias("x"), pl.col("size").sum().alias("vol"))
    k = k.join(t, on="k", how="left").with_columns(pl.col("x").fill_null(0.0), pl.col("vol").fill_null(0.0)).filter((pl.col("dk") == 1) & (pl.col("reset") == 0))
    for (b,), g in k.with_columns((pl.col("k") // 90).alias("b")).group_by("b"):
        if g.height < 60: continue
        x, y = g["x"].to_numpy(), g["dm"].to_numpy(); xc = x - x.mean(); sxx = (xc ** 2).sum()
        if sxx <= 0: continue
        lam = (xc * (y - y.mean())).sum() / sxx; res = y - y.mean() - lam * xc
        se = np.sqrt((res ** 2).sum() / (len(y) - 2) / sxx); r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
        rows.append(dict(day=d, t=int(b) * 900_000, lam=lam, se=se, r2=r2, vol=float(g["vol"].sum()), sxx=sxx, q_best=float(g["q_best"].mean()),
                         depth10=float(g["depth10"].mean()), absmove=float(np.abs(y).sum())))
B = pl.DataFrame(rows); B.write_parquet(L20.S4 / "kyle_blocks.parquet")
I = B.filter(pl.col("day") < "2025-10-10"); thr = I["lam"].quantile(0.99)
hi = I.filter(pl.col("lam") > thr)
print("in-sample blocks", I.height, "p99 lambda", round(thr, 1))
print("top 1% blocks: median vol", round(hi["vol"].median()), "vs all", round(I["vol"].median()), "| median se", round(hi["se"].median(), 1), "vs", round(I["se"].median(), 1),
      "| median R2", round(hi["r2"].median(), 2), "vs", round(I["r2"].median(), 2), "| median t", round((hi["lam"] / hi["se"]).median(), 1))
print("spearman lam vs vol", round(np.corrcoef(I["lam"].rank().to_numpy(), I["vol"].rank().to_numpy())[0, 1], 2),
      "lam vs se", round(np.corrcoef(I["lam"].rank().to_numpy(), I["se"].rank().to_numpy())[0, 1], 2),
      "lam vs 1/depth10", round(np.corrcoef(I["lam"].rank().to_numpy(), (1 / I["depth10"]).rank().to_numpy())[0, 1], 2))
C = B.filter(pl.col("day") == "2025-10-10").with_columns((pl.col("t") // 900_000 % 96 * 15).alias("min_of_day")).filter(pl.col("min_of_day") >= 18 * 60).sort("t")
print("10 Oct from 18:00:"); print(C.select((pl.col("min_of_day") // 60).alias("h"), (pl.col("min_of_day") % 60).alias("m"), pl.col("lam").round(1), pl.col("se").round(1), pl.col("r2").round(2), pl.col("vol").round(0), pl.col("depth10").round(1)))
pct = lambda v: float((I["lam"] < v).mean())
print("in-sample percentile of 10 Oct 21:00-21:45 lambdas:", [round(pct(v), 3) for v in C.filter((pl.col("min_of_day") >= 21 * 60) & (pl.col("min_of_day") < 22 * 60))["lam"]])
