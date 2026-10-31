"""Follow-up on Kyle's lambda, robustness over block length (5, 15, 30, 60, 120 min): per block, the per-BTC slope (lin) and the square-root slope
(sqrt) of the mid change on Bybit's TI over 10-second intervals. For each length: exponent of lin on volume (in sample), rank correlation of each with
volume, the highest in-sample percentile reached on 10 Oct in the cascade (20:50-22:50) and in the two hours before the post (18:50-20:50), blocks
aligned so that one ends at 20:50:00. For 120 min also the rank of the block before the post among all blocks of the other 44 days (H9c follow-up)."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("kyle_check3")

DAYS = L20.days()
POST_K = int(np.datetime64("2025-10-10T20:50:00", "s").astype(np.int64)) // 10
K = []
for d in DAYS:
    d0 = int(np.datetime64(f"{d}T00:00:00", "s").astype(np.int64))
    sec = pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "mid2", "reset"]).filter((pl.col("sec") >= d0) & (pl.col("sec") < d0 + 86400))
    k = sec.with_columns((pl.col("sec") // 10).alias("k")).group_by("k").agg(pl.col("mid2").last(), pl.col("reset").max()).sort("k")
    k = k.with_columns(((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"), (pl.col("k") - pl.col("k").shift(1)).alias("dk"))
    O = pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size"])
    t = O.group_by((pl.col("ts") // 10_000).alias("k")).agg((pl.col("side") * pl.col("size")).sum().alias("x"), pl.col("size").sum().alias("vol"))
    K.append(k.join(t, on="k", how="left").with_columns(pl.col("x").fill_null(0.0), pl.col("vol").fill_null(0.0), pl.lit(d).alias("day"))
             .filter((pl.col("dk") == 1) & (pl.col("reset") == 0)))
K = pl.concat(K).with_columns((pl.col("x").sign() * pl.col("x").abs().sqrt()).alias("z"))
sp = lambda a, b: float(np.corrcoef(a.rank().to_numpy(), b.rank().to_numpy())[0, 1])
for L in (5, 15, 30, 60, 120):
    n = L * 6
    G = K.with_columns(((pl.col("k") - POST_K) // n).alias("b")).group_by("b").agg(
        pl.col("day").first(), pl.len().alias("m"), pl.col("vol").sum(),
        ((pl.col("x") - pl.col("x").mean()) * (pl.col("dm") - pl.col("dm").mean())).sum().alias("sxy"), ((pl.col("x") - pl.col("x").mean()) ** 2).sum().alias("sxx"),
        ((pl.col("z") - pl.col("z").mean()) * (pl.col("dm") - pl.col("dm").mean())).sum().alias("szy"), ((pl.col("z") - pl.col("z").mean()) ** 2).sum().alias("szz"))
    G = G.filter(pl.col("m") >= 0.66 * n).with_columns((pl.col("sxy") / pl.col("sxx")).alias("lin"), (pl.col("szy") / pl.col("szz")).alias("sqrt")).filter((pl.col("lin") > 0) & (pl.col("vol") > 0))
    I = G.filter(pl.col("day") < "2025-10-10")
    ex = np.polyfit(np.log(I["vol"]), np.log(I["lin"]), 1)[0]
    pc = lambda v, c: float((I[c] < v).mean())
    cas = G.filter((pl.col("b") >= 0) & (pl.col("b") < 120 // L)); pre = G.filter((pl.col("b") < 0) & (pl.col("b") >= -(120 // L)))
    print(f"{L:3d} min: exponent {ex:+.2f} | rho(vol) lin {sp(I['lin'], I['vol']):+.2f} sqrt {sp(I['sqrt'], I['vol']):+.2f} | cascade max pct lin {max(pc(v, 'lin') for v in cas['lin']):.3f} "
          f"sqrt {max(pc(v, 'sqrt') for v in cas['sqrt']):.3f} | 2 h before max pct lin {max(pc(v, 'lin') for v in pre['lin']):.3f} sqrt {max(pc(v, 'sqrt') for v in pre['sqrt']):.3f}")
    if L == 120:
        ref = G.filter(pl.col("day") != "2025-10-10"); x = pre.row(0, named=True)
        for c in ("lin", "sqrt"):
            r = ref[c].to_numpy(); print(f"   H9c follow-up {c}: 10 Oct {x[c]:.2f}, median {np.median(r):.2f}, above {np.mean(r < x[c]):.3f} of {len(r)} windows, p = {(1 + (r >= x[c]).sum()) / (1 + len(r)):.3f}")
