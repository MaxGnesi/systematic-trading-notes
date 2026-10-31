"""Lecture 20, H4: VPIN on Bybit BTCUSDT over the 45 days (Easley, Lopez de Prado and O'Hara, 2012). Buckets of V = average daily volume of the
in-sample days / 50, filled in time order across days, orders split at bucket edges; buy volume (a) from the true taker side, (b) by bulk volume
classification over one-minute bars (share bought = Phi(dp / sigma), sigma = standard deviation of one-minute mid changes in sample).
VPIN = mean |V_buy - V_sell| / V over the last 50 completed buckets, sampled at the start of every hour. Per hour also: realised volatility of the
mid over the hour (sum of squared one-minute changes, ticks^2), volume (BTC). Output: L20_OUT/s3/vpin_hours.parquet, L20_OUT/s3/vpin_buckets.parquet."""
import sys
from math import erf, sqrt
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
DAYS = L20.days(); INS = [d for d in DAYS if d <= "2025-10-09"]

O = pl.concat([pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size"]) for d in DAYS]).sort("ts")
# one-minute mid (last update in each minute) from the book state
M = pl.concat([pl.read_parquet(L20.STATE / f"{d}.parquet", columns=["ts", "bid", "ask"]).sort("ts").with_columns((pl.col("ts") // 60000).alias("min"))
               .group_by("min").agg(((pl.col("bid") + pl.col("ask")) / 2).last().alias("mid")) for d in DAYS]).group_by("min").agg(pl.col("mid").last()).sort("min")
M = M.with_columns((pl.col("mid") - pl.col("mid").shift(1)).alias("dm"))
day_of = lambda ms: pl.from_epoch(ms, time_unit="ms").dt.strftime("%Y-%m-%d")
vol_day = O.with_columns(day_of(pl.col("ts")).alias("d")).group_by("d").agg(pl.col("size").sum())
V = float(vol_day.filter(pl.col("d").is_in(INS))["size"].mean()) / 50
sig = float(M.with_columns(day_of(pl.col("min") * 60000).alias("d")).filter(pl.col("d").is_in(INS))["dm"].std())
print(f"bucket {V:,.0f} BTC, sigma of one-minute mid change {sig:.1f} ticks")


def buckets(ts, vol, buy):
    """Buckets of volume V from units (time, volume, bought volume); a unit straddling an edge is split in proportion. Returns end time and buy share."""
    cv = np.cumsum(vol); cb = np.cumsum(buy); edges = np.arange(V, cv[-1], V)
    j = np.searchsorted(cv, edges)                                   # unit in which each edge falls
    prev_v = np.where(j > 0, cv[j - 1], 0.0); prev_b = np.where(j > 0, cb[j - 1], 0.0)
    frac = (edges - prev_v) / vol[j]
    cb_edge = prev_b + frac * buy[j]
    vb = np.diff(np.concatenate([[0.0], cb_edge]))
    return ts[j], vb / V


ts = O["ts"].to_numpy(); vol = O["size"].to_numpy(); side = O["side"].to_numpy()
t_true, b_true = buckets(ts, vol, np.where(side == 1, vol, 0.0))
# bulk classification: one-minute bars of volume, buy share from the bar's mid change
Bm = O.with_columns((pl.col("ts") // 60000).alias("min")).group_by("min").agg(pl.col("size").sum()).sort("min").join(M, on="min", how="left")
phi = np.array([0.5 * (1 + erf(x / (sig * sqrt(2)))) if x == x else 0.5 for x in Bm["dm"].fill_null(0).to_numpy()])
bv = Bm["size"].to_numpy()
t_bvc, b_bvc = buckets(Bm["min"].to_numpy() * 60000 + 59999, bv, bv * phi)
Bk = pl.DataFrame(dict(t_end=t_true, buy_share=b_true)); Bk.write_parquet(OUT / "vpin_buckets.parquet")
print("buckets", len(t_true), "per day about", round(len(t_true) / len(DAYS), 1))

imb_t = np.abs(2 * b_true - 1); imb_b = np.abs(2 * b_bvc - 1)
cs_t = np.concatenate([[0], np.cumsum(imb_t)]); cs_b = np.concatenate([[0], np.cumsum(imb_b)])
hours = np.arange((int(ts[0]) // 3600000 + 1) * 3600000, int(ts[-1]) // 3600000 * 3600000 + 1, 3600000)


def vpin_at(h, t_end, cs):
    k = np.searchsorted(t_end, h, side="left")                      # buckets completed before h
    return (cs[k] - cs[k - 50]) / 50 if k >= 50 else np.nan


H = pl.DataFrame(dict(h=hours, vpin=[vpin_at(h, t_true, cs_t) for h in hours], vpin_bvc=[vpin_at(h, t_bvc, cs_b) for h in hours]))
RV = M.with_columns((pl.col("min") // 60).alias("hr")).group_by("hr").agg((pl.col("dm") ** 2).sum().alias("rv"), pl.len().alias("nmin"))
VO = O.with_columns((pl.col("ts") // 3600000).alias("hr")).group_by("hr").agg(pl.col("size").sum().alias("vol"))
H = H.with_columns((pl.col("h") // 3600000).alias("hr")).join(RV, on="hr", how="left").join(VO, on="hr", how="left").sort("hr")
H = H.with_columns(pl.col("rv").shift(-0).alias("rv_next"), pl.col("rv").shift(1).alias("rv_last"), pl.col("vol").shift(1).alias("vol_last"),
                   day_of(pl.col("h")).alias("day"))                # the hour starting at h is 'next'; the one before it is 'last'
H.write_parquet(OUT / "vpin_hours.parquet")
print(H.drop_nulls().select(pl.corr("vpin", "rv_next", method="spearman").alias("rho_true"), pl.corr("vpin_bvc", "rv_next", method="spearman").alias("rho_bvc"),
                            pl.corr("vpin", "vol_last", method="spearman").alias("rho_vpin_vol"), pl.corr("vpin", "vpin_bvc", method="spearman").alias("true_vs_bvc")))
