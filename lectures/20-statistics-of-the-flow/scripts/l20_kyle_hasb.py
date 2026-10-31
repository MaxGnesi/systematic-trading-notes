"""Kyle's lambda in the published form of Hasbrouck (2009), as used by Goyenko, Holden and Trzcinka (2009): slope, without intercept, of the
return of the mid (here in basis points, log) on S = sum over taker orders of sign * sqrt(dollar volume of the order), over 10-second intervals.
(Published: 5-minute intervals and individual trades signed by the Lee-Ready rule; here 10-second intervals, so that 15-minute blocks have 90
points, and taker orders, whose side Bybit records.) Robustness over block lengths 5-120 min, aligned so that one block ends at 20:50 on 10 Oct;
H9c follow-up for the two hours before the post. Compared with the per-BTC slope and with our earlier variant (square root of the net flow)."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("kyle_hasb")

DAYS = L20.days()
POST_K = int(np.datetime64("2025-10-10T20:50:00", "s").astype(np.int64)) // 10
K = []
for d in DAYS:
    d0 = int(np.datetime64(f"{d}T00:00:00", "s").astype(np.int64))
    sec = pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "mid2", "reset"]).filter((pl.col("sec") >= d0) & (pl.col("sec") < d0 + 86400))
    k = sec.with_columns((pl.col("sec") // 10).alias("k")).group_by("k").agg(pl.col("mid2").last(), pl.col("reset").max()).sort("k")
    k = k.with_columns(((pl.col("mid2").log() - pl.col("mid2").shift(1).log()) * 1e4).alias("r"), ((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"),
                       (pl.col("k") - pl.col("k").shift(1)).alias("dk"))
    O = pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size", "tick"])
    t = O.group_by((pl.col("ts") // 10_000).alias("k")).agg((pl.col("side") * (pl.col("size") * pl.col("tick") / 10).sqrt()).sum().alias("S"),
                                                             (pl.col("side") * pl.col("size")).sum().alias("x"), pl.col("size").sum().alias("vol"))
    K.append(k.join(t, on="k", how="left").with_columns(pl.col("S").fill_null(0.0), pl.col("x").fill_null(0.0), pl.col("vol").fill_null(0.0), pl.lit(d).alias("day"))
             .filter((pl.col("dk") == 1) & (pl.col("reset") == 0)).select("k", "r", "dm", "S", "x", "vol", "day"))
K = pl.concat(K).with_columns((pl.col("x").sign() * pl.col("x").abs().sqrt()).alias("z"))
sp = lambda a, b: float(np.corrcoef(a.rank().to_numpy(), b.rank().to_numpy())[0, 1])
for L in (5, 15, 30, 60, 120):
    n = L * 6
    G = K.with_columns(((pl.col("k") - POST_K) // n).alias("b")).group_by("b").agg(
        pl.col("day").first(), pl.len().alias("m"), pl.col("vol").sum(),
        ((pl.col("r") * pl.col("S")).sum() / (pl.col("S") ** 2).sum()).alias("hasb"),
        (((pl.col("x") - pl.col("x").mean()) * (pl.col("dm") - pl.col("dm").mean())).sum() / ((pl.col("x") - pl.col("x").mean()) ** 2).sum()).alias("lin"),
        (((pl.col("z") - pl.col("z").mean()) * (pl.col("dm") - pl.col("dm").mean())).sum() / ((pl.col("z") - pl.col("z").mean()) ** 2).sum()).alias("sqrt"))
    G = G.filter((pl.col("m") >= 0.66 * n) & (pl.col("lin") > 0) & (pl.col("hasb") > 0) & (pl.col("vol") > 0))
    I = G.filter(pl.col("day") < "2025-10-10"); pc = lambda v, c: float((I[c] < v).mean())
    cas = G.filter((pl.col("b") >= 0) & (pl.col("b") < 120 // L)); pre = G.filter((pl.col("b") < 0) & (pl.col("b") >= -(120 // L)))
    print(f"{L:3d} min | rho(vol): lin {sp(I['lin'], I['vol']):+.2f} sqrt-net {sp(I['sqrt'], I['vol']):+.2f} Hasbrouck {sp(I['hasb'], I['vol']):+.2f} "
          f"| rho(Hasbrouck, sqrt-net) {sp(I['hasb'], I['sqrt']):+.2f} | cascade max pct: lin {max(pc(v, 'lin') for v in cas['lin']):.3f} Hasbrouck {max(pc(v, 'hasb') for v in cas['hasb']):.3f} "
          f"| 2 h before max pct: Hasbrouck {max(pc(v, 'hasb') for v in pre['hasb']):.3f}", flush=True)
    if L == 120:
        ref = G.filter(pl.col("day") != "2025-10-10"); x = pre.row(0, named=True); r = ref["hasb"].to_numpy()
        print(f"   H9c follow-up, Hasbrouck: 10 Oct {x['hasb']:.4f} bp per sqrt($), median {np.median(r):.4f}, above {np.mean(r < x['hasb']):.3f} of {len(r)}, p = {(1 + (r >= x['hasb']).sum()) / (1 + len(r)):.3f}")
