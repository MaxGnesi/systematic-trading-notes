"""Lecture 19 §3, one day, light pass (hypotheses in results/hypotheses.md). From L19_OUT/state/DAY.parquet (one row per book update) and the trades:
(1) samples as Gould & Bonart (2015): one point per interval between mid changes, the state at a random update inside it, kept if the spread is
one tick; fields: I1, I5, the smaller best queue, the next mid change (up or down, ticks) and the mid change over 1 s and 10 s (ticks).
(2) markouts of the resting side of every taker order (trades with the same ms and side): size-weighted sums of M(h) per BTC, in ticks, by size
bucket, for h = 0, 0.1, 1, 10, 60 s, against the mid of the last book state before the trade.
Output: L19_OUT/s3/samples_DAY.parquet, L19_OUT/s3/mk_DAY.json. Usage: python l19_s3_day.py DAY [...]"""
import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np, polars as pl, psutil
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
OUT = L19.S3; OUT.mkdir(exist_ok=True)
TRADES = L19.TRADES
H = [0, 100, 1000, 10000, 60000]                                                     # markout horizons, ms
BUCKETS = [0, 0.01, 0.1, 1, np.inf]                                                  # taker order size, BTC


def guard(mb=800):
    """Wait while the machine is short of memory (16 GB PC, other jobs running)."""
    for _ in range(120):
        if psutil.virtual_memory().available / 2**20 > mb: return
        time.sleep(30)
    sys.exit("memory stayed short; stopped")


for day in sys.argv[1:]:
    if (OUT / f"mk_{day}.json").exists(): continue
    guard(); t0 = time.time()
    d0 = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000); d1 = d0 + 86_400_000
    X = pl.read_parquet(L19.STATE / f"{day}.parquet").filter((pl.col("ts") >= d0 - 60_000) & (pl.col("ts") < d1 + 70_000))
    X = X.with_columns((pl.col("bid") + pl.col("ask")).alias("m2"))                 # twice the mid, in ticks (an integer)
    # (1) samples
    S = X.with_columns((pl.col("m2") != pl.col("m2").shift(1)).fill_null(True).cum_sum().alias("seg"))
    nxt = S.group_by("seg").agg(pl.col("m2").first().alias("m2_first")).sort("seg").with_columns(pl.col("m2_first").shift(-1).alias("m2_next"))
    rng = np.random.default_rng(int(day.replace("-", "")))
    S = S.with_columns(pl.Series("r", rng.random(S.height))).sort("r").group_by("seg").first().sort("ts")
    S = S.join(nxt.select("seg", "m2_next"), on="seg").filter((pl.col("ts") >= d0) & (pl.col("ts") < d1) & (pl.col("ask") - pl.col("bid") == 1))
    S = S.drop_nulls("m2_next")
    for h in (1000, 10000):
        F = X.select(pl.col("ts").alias("th"), pl.col("m2").alias(f"m2_{h}"))
        S = S.with_columns((pl.col("ts") + h).alias("th")).sort("th").join_asof(F, on="th", strategy="backward").drop("th")
    S = S.select("ts", ((pl.col("q_bid") - pl.col("q_ask")) / (pl.col("q_bid") + pl.col("q_ask"))).cast(pl.Float32).alias("I1"),
                 ((pl.col("q_bid5") - pl.col("q_ask5")) / (pl.col("q_bid5") + pl.col("q_ask5"))).cast(pl.Float32).alias("I5"),
                 pl.min_horizontal("q_bid", "q_ask").cast(pl.Float32).alias("qmin"), (pl.col("m2_next") > pl.col("m2")).alias("up"),
                 ((pl.col("m2_next") - pl.col("m2")) / 2).cast(pl.Float32).alias("d_next"),
                 ((pl.col("m2_1000") - pl.col("m2")) / 2).cast(pl.Float32).alias("d_1s"), ((pl.col("m2_10000") - pl.col("m2")) / 2).cast(pl.Float32).alias("d_10s"))
    S.write_parquet(OUT / f"samples_{day}.parquet")
    # (2) markouts of the resting side
    T = pl.read_parquet(TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).filter((pl.col("ts") >= d0) & (pl.col("ts") < d1))
    T = T.group_by("ts", "side").agg(pl.col("size").sum().alias("q"), ((pl.col("tick") * pl.col("size")).sum() / pl.col("size").sum()).alias("p")).sort("ts")
    M = T.with_columns((pl.col("ts") - 1).alias("th")).join_asof(X.select(pl.col("ts").alias("th"), pl.col("m2").alias("m2_0"), (pl.col("ask") - pl.col("bid")).alias("spr")),
                                                               on="th", strategy="backward").drop("th")
    for h in H[1:]:
        M = M.with_columns((pl.col("ts") + h).alias("th")).join_asof(X.select(pl.col("ts").alias("th"), pl.col("m2").alias(f"m2_{h}")), on="th", strategy="backward").drop("th")
    M = M.drop_nulls()
    res = {"day": day, "fills": M.height, "buckets": []}
    for lo, hi in zip(BUCKETS[:-1], BUCKETS[1:]):
        for spr_one in (False, True):
            B = M.filter((pl.col("q") >= lo) & (pl.col("q") < hi))
            if spr_one: B = B.filter(pl.col("spr") == 1)
            s_mk = (-pl.col("side")).cast(pl.Float64)                                # the maker's side: opposite to the taker
            row = {"lo": lo, "hi": None if np.isinf(hi) else hi, "spread_one": spr_one, "n": B.height, "size": float(B["q"].sum())}
            for h in H:
                row[f"m{h}"] = float(B.select((s_mk * (pl.col(f"m2_{h}") / 2 - pl.col("p")) * pl.col("q")).sum()).item())
            res["buckets"].append(row)
    (OUT / f"mk_{day}.json").write_text(json.dumps(res))
    print(day, f"{time.time() - t0:.0f} s, samples {S.height:,}, fills {M.height:,}", flush=True)
