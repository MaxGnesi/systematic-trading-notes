"""Lecture 21 §3.2: the small tables behind figure 21_11, from the per-day orders of l21_s32_latency.py (L21_OUT/s32/orders).
size.parquet: by order size S and latency L, over all 45 days and both sides: moments, moments without a price (the 200 levels hold less than
  S), mean and median slippage in bp, share of orders that paid more than expected, share of IOC orders filled short, mean share left resting
  by a limit order; with 95% bands from 2,000 resamples of days.
ret.parquet: the IOC order of 0.001 BTC at L = 50 ms, by the move of the mid over the next second (bins in bp, positive in the order's favour)
  and by the volatility of the hour (terciles over all hours): share filled short, moments.
Output: L21_OUT/s32/. Usage: python l21_s32_sum.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
S32 = L21.OUT / "s32"; rng = np.random.default_rng(0)
EDGES = [-np.inf, -2, -0.5, 0.5, 2, 5, np.inf]; LABELS = ["< -2", "-2 to -0.5", "about 0", "0.5 to 2", "2 to 5", "> 5"]

per_day, rets = [], []
for f in sorted((S32 / "orders").glob("*.parquet")):
    D = pl.read_parquet(f).with_columns((pl.col("paid_bp") - pl.col("exp_bp")).alias("slip"))
    per_day.append(D.group_by("S", "L").agg(
        pl.len().alias("n"), pl.col("slip").is_nan().sum().alias("empty"), pl.col("slip").filter(pl.col("slip").is_not_nan()).sum().alias("slip_sum"),
        (pl.col("slip") > 1e-9).sum().alias("worse"), (pl.col("ioc_fill") < 1 - 1e-9).sum().alias("short"), (1 - pl.col("ioc_fill")).sum().alias("left_sum"),
        pl.col("slip").filter(pl.col("slip").is_not_nan()).median().alias("slip_med")).with_columns(pl.lit(f.stem).alias("day")))
    rets.append(D.filter((pl.col("S") < 0.002) & (pl.col("L") == 50)).select("ret1_bp", "vol_h", "ioc_fill").with_columns(pl.lit(f.stem).alias("day")))
P = pl.concat(per_day); R = pl.concat(rets)
days = P["day"].unique().sort().to_list()


def band(G, num, den):
    """Ratio of sums over days, with a 95% band from resampling days."""
    g = {d: (a, b) for d, a, b in G.select("day", num, den).iter_rows()}; v = np.array([g.get(d, (0.0, 0.0)) for d in days])
    idx = rng.integers(0, len(days), (2000, len(days))); bs = v[idx, 0].sum(1) / v[idx, 1].sum(1)
    return v[:, 0].sum() / v[:, 1].sum(), *np.quantile(bs, [0.025, 0.975])


rows = []
for (S, L), G in P.group_by("S", "L"):
    G = G.with_columns((pl.col("n") - pl.col("empty")).alias("priced"))
    rows.append(dict(S=float(S), L=int(L), n=int(G["n"].sum()), empty=int(G["empty"].sum()),
                     **dict(zip(("slip", "slip_lo", "slip_hi"), band(G, "slip_sum", "priced"))),
                     slip_median_of_days=float(G["slip_med"].median()), **dict(zip(("worse", "worse_lo", "worse_hi"), band(G, "worse", "priced"))),
                     **dict(zip(("short", "short_lo", "short_hi"), band(G, "short", "n"))), left=float(G["left_sum"].sum() / G["n"].sum())))
pl.DataFrame(rows).sort("S", "L").write_parquet(S32 / "size.parquet")

R = R.with_columns(pl.col("ret1_bp").cut(EDGES[1:-1], labels=LABELS, left_closed=True).alias("move"),
                   pl.col("vol_h").qcut(3, labels=["calm", "middle", "volatile"]).alias("vol"), (pl.col("ioc_fill") < 1 - 1e-9).alias("short"))
out = []
for by in ("move", "vol"):
    G = R.group_by("day", by).agg(pl.col("short").sum().alias("s"), pl.len().alias("n"))
    for k, H in G.group_by(by):
        r = band(H, "s", "n"); out.append(dict(by=by, cls=str(k[0]), n=int(H["n"].sum()), short=r[0], lo=r[1], hi=r[2]))
pl.DataFrame(out).write_parquet(S32 / "ret.parquet")
with pl.Config(tbl_rows=40, tbl_cols=20, tbl_width_chars=250):
    print(pl.read_parquet(S32 / "size.parquet")); print(pl.read_parquet(S32 / "ret.parquet").sort("by", "cls"))
