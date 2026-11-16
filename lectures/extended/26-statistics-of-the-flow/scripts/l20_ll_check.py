"""Audit of H6 (lead-lag ratio < 1 from a long Bybit-first tail). Simulation on the real trade times of 1 Oct 2025 (12:00-14:00 UTC):
a latent price per ms (random walk, sd 1 tick per ms); Binance's last trade = latent price at its trade times; Bybit's = latent price 40 ms
earlier at its trade times, i.e. Binance leads by 40 ms. Variants: (1) no bounce, (2) bid-ask bounce on Bybit's last trade (+/- half spread by the
trade's real side), (3) bounce on both. Run our hy_profile, report peak and LLR over +/-1 s. Then the real data in the same two hours."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("ll_check")

from l20_s3_leadlag import hy_profile, LAGS
D = "2025-10-01"; a = int(np.datetime64(f"{D}T12:00:00", "ms").astype(np.int64)); b = a + 2 * 3_600_000; rng = np.random.default_rng(6)
X = pl.read_parquet(L20.ORD / f"binance_px_{D}.parquet").sort("ts").filter((pl.col("ts") >= a) & (pl.col("ts") < b))
Y = pl.read_parquet(L20.ORD / f"bybit_px_{D}.parquet").sort("ts").filter((pl.col("ts") >= a) & (pl.col("ts") < b))
bo = pl.read_parquet(L20.ORD / f"bybit_{D}.parquet", columns=["ts", "side"]).filter((pl.col("ts") >= a) & (pl.col("ts") < b)).group_by("ts").agg(pl.col("side").last())
no = pl.read_parquet(L20.ORD / f"binance_{D}.parquet", columns=["ts", "side"]).filter((pl.col("ts") >= a) & (pl.col("ts") < b)).group_by("ts").agg(pl.col("side").last())
tx, ty = X["ts"].to_numpy(), Y["ts"].to_numpy()
sx = X.join(no, on="ts", how="left")["side"].fill_null(1).to_numpy(); sy = Y.join(bo, on="ts", how="left")["side"].fill_null(1).to_numpy()
print("trades per second: Binance", round(len(tx) / 7200, 1), "Bybit", round(len(ty) / 7200, 1), "| median gap between price changes ms: Binance",
      np.median(np.diff(tx[np.r_[True, np.diff(X['px'].to_numpy()) != 0]])), "Bybit", np.median(np.diff(ty[np.r_[True, np.diff(Y['px'].to_numpy()) != 0]])))
lat = np.cumsum(rng.normal(0, 1.0, b - a + 2000))                    # latent price in ticks, index = ms since a - 1000
P = lambda t: lat[t - a + 1000]
llr = lambda r: (r[LAGS > 0] ** 2).sum() / (r[LAGS < 0] ** 2).sum()
for name, bx, by in (("no bounce", 0, 0), ("bounce on Bybit", 0, 1), ("bounce on both", 1, 1)):
    x = P(tx) + bx * sx * 0.5; y = P(ty - 40) + by * sy * 0.5
    r = hy_profile(tx, x, ty, y, LAGS)
    print(f"sim, {name:16s}: peak {LAGS[r.argmax()]} ms ({r.max():.2f}), LLR {llr(r):.2f}, sum r^2 at 300..1000 ms: + {(r[(LAGS >= 300)] ** 2).sum():.3f} / - {(r[(LAGS <= -300)] ** 2).sum():.3f}")
r = hy_profile(tx, X["px"].to_numpy(), ty, Y["px"].to_numpy(), LAGS)
print(f"real, 12-14 UTC         : peak {LAGS[r.argmax()]} ms ({r.max():.2f}), LLR {llr(r):.2f}, tail + {(r[(LAGS >= 300)] ** 2).sum():.3f} / - {(r[(LAGS <= -300)] ** 2).sum():.3f}")

# lead-lag ratio over narrower lag ranges: simulation (no bounce), 1 Oct 12-14, all 45 days pooled (out of sample), last trade and mid
def llr_w(r, w): return (r[(LAGS > 0) & (LAGS <= w)] ** 2).sum() / (r[(LAGS < 0) & (LAGS >= -w)] ** 2).sum()
rs = hy_profile(tx, P(tx), ty, P(ty - 40), LAGS)
LL = pl.read_parquet(L20.result_path(L20.S3, "leadlag.parquet")).filter(pl.col("day") >= "2025-10-11").group_by("lag").agg(pl.col("rho_last").mean(), pl.col("rho_mid").mean()).sort("lag")
for w in (50, 100, 200, 500, 1000):
    print(f"LLR within +/-{w:4d} ms: sim {llr_w(rs, w):6.2f} | real 1 Oct 12-14 {llr_w(r, w):5.2f} | pooled out of sample: last {llr_w(LL['rho_last'].to_numpy(), w):5.2f}, mid {llr_w(LL['rho_mid'].to_numpy(), w):5.2f}")
