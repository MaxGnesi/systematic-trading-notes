"""Lecture 20, H7 post-hoc (labelled as such): is the negative rank correlation of Bybit's I1 with the gap Binance last trade - Bybit mid
a Simpson's paradox driven by Bybit's last mid move? On each in-sample day, at the samples of Lecture 19, the rank correlation of
(a) I1 with the sign of Bybit's last mid change, (b) the gap with that sign, (c) I1 with the gap within samples after an up move and after a
down move, (d) I1 with the gap by time since the last mid change (< 200 ms, 200 ms - 1 s, 1 - 5 s, > 5 s). Output: L20_OUT/s3/simpson.json. Usage: python l20_s3_simpson.py [DAY ...]"""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
DAYS = [d for d in L20.day_list() if d <= "2025-10-09"]
BINS = [(0, 200), (200, 1000), (1000, 5000), (5000, 10 ** 12)]


def spear(x, y):
    if len(x) < 30: return float("nan")
    return float(np.corrcoef(pl.Series(x).rank().to_numpy(), pl.Series(y).rank().to_numpy())[0, 1])


res = {}
for d in DAYS:
    s = pl.read_parquet(L20.S3_19 / f"samples_{d}.parquet").sort("ts").select("ts", "I1")
    st = pl.read_parquet(L20.STATE / f"{d}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 20).alias("mid")).sort("ts")
    st = st.group_by("ts", maintain_order=True).agg(pl.col("mid").last())
    ch = st.with_columns((pl.col("mid") - pl.col("mid").shift(1)).alias("dmid")).filter(pl.col("dmid") != 0).select(
        "ts", pl.col("dmid").sign().alias("move"), pl.col("ts").alias("t_move"))
    last = pl.read_parquet(L20.BN / f"{d}.parquet").rename({"price": "bn"}).sort("ts")
    w = s.join_asof(st, on="ts").join_asof(last, on="ts").join_asof(ch, on="ts").drop_nulls()
    w = w.with_columns((pl.col("bn") - pl.col("mid")).alias("gap"), (pl.col("ts") - pl.col("t_move")).alias("age"))
    r = dict(n=w.height, all=spear(w["I1"], w["gap"]), I1_move=spear(w["I1"], w["move"]), gap_move=spear(w["gap"], w["move"]))
    for m, name in ((1, "within_up"), (-1, "within_down")):
        g = w.filter(pl.col("move") == m); r[name] = spear(g["I1"], g["gap"])
    for a, b in BINS:
        g = w.filter((pl.col("age") >= a) & (pl.col("age") < b)); r[f"age_{a}_{b}"] = spear(g["I1"], g["gap"]); r[f"n_{a}_{b}"] = g.height
    res[d] = r
    print(d, {k: round(v, 3) for k, v in r.items()}, flush=True)
med = {k: float(np.nanmedian([res[d][k] for d in DAYS])) for k in res[DAYS[0]]}
pos = {k: int(sum(res[d][k] > 0 for d in DAYS)) for k in ("within_up", "within_down")}
(OUT / f"{L20.tag()}simpson.json").write_text(json.dumps(dict(days=res, median=med, days_positive=pos, n_days=len(DAYS))))
print("median", {k: round(v, 3) for k, v in med.items()}, "days positive", pos)
