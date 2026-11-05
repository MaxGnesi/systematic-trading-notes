"""Lecture 21 §4, H4: is the replay kinder than reality? Real fills: the resting side of real taker orders below 0.01 BTC (trades with the same ms and side, as in
Lecture 19) executed at the best price on that side at the last book update. Their 1-s markout against that of the replay's fills (the test resting order, Q2,
a = 1, L = 50 ms), out of sample. Non-inferiority: the replay is not more than 0.1 bp better; p: share of 2,000 resamples of days with replay - real >= 0.1 bp.
Output: L21_OUT/s4/h4.parquet (per day) and h4_test.parquet. Usage: python l21_s4_h4.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
OUT = L21.OUT / "s4"; OUT.mkdir(exist_ok=True); rng = np.random.default_rng(0); MARGIN = 0.1
files = sorted((L21.OUT / "mm").glob("*.parquet")); days = [f.stem for f in files]; rows = []
for day in days:
    S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts"); ts, bid, ask = (S[c].to_numpy() for c in ("ts", "bid", "ask")); mid = (bid + ask) / 2
    T = (pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).group_by("ts", "side")
         .agg(pl.col("size").sum().alias("q"), ((pl.col("tick") * pl.col("size")).sum() / pl.col("size").sum()).alias("p")).filter(pl.col("q") < 0.01))
    t, sd, p = (T[c].to_numpy() for c in ("ts", "side", "p")); k = np.searchsorted(ts, t, side="right") - 1; ok = k >= 0
    t, sd, p, k = t[ok], sd[ok], p[ok], k[ok]
    at = (sd == -1) & (p == bid[k]) | (sd == 1) & (p == ask[k])                 # at the best on the resting side's price
    t, sd, p = t[at], sd[at], p[at]; k1 = np.searchsorted(ts, t + 1000, side="right") - 1
    m1 = -sd * (mid[k1] - p) / p * 1e4                                           # the resting side: bought when the taker sold
    R = pl.scan_parquet(L21.OUT / "mm" / f"{day}.parquet").filter(pl.col("filled") & (pl.col("quoter") == "instant") & (pl.col("L") == 50) & (pl.col("rule") == "Q2 a=1")).select(
        ((pl.col("mid1") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m")).collect()["m"].to_numpy()
    rows.append(dict(day=day, real_n=len(m1), real_sum=float(m1.sum()), all_orders=int(ok.sum()), replay_n=len(R), replay_sum=float(R.sum())))
D = pl.DataFrame(rows); D.write_parquet(OUT / "h4.parquet")
v = D.select("real_n", "real_sum", "replay_n", "replay_sum").to_numpy(); idx = rng.integers(0, len(days), (2000, len(days)))
f = lambda w: w[..., 3].sum(-1) / w[..., 2].sum(-1) - w[..., 1].sum(-1) / w[..., 0].sum(-1); bs = f(v[idx])
out = dict(real=v[:, 1].sum() / v[:, 0].sum(), replay=v[:, 3].sum() / v[:, 2].sum(), diff=float(f(v)), lo=float(np.quantile(bs, .025)), hi=float(np.quantile(bs, .975)), p=float((bs >= MARGIN).mean()), real_fills=int(v[:, 0].sum()), share_at_best=float(v[:, 0].sum() / D["all_orders"].sum()))
pl.DataFrame([out]).write_parquet(OUT / "h4_test.parquet"); print(out)
