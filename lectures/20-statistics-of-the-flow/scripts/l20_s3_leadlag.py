"""Lecture 20, H6: lead and lag between Binance (X) and Bybit (Y), last traded price in each ms on each venue. Hayashi-Yoshida correlation of
price changes at lags -1000..+1000 ms in 1 ms steps (Hoffmann, Rosenbaum and Yoshida, 2013): Bybit's times shifted back by tau, so tau > 0 means
Binance moves first. For each change of X over (s, e], the sum of Y's changes over all of Y's intervals that overlap (s, e] telescopes to
Y(first Y time >= e) - Y(last Y time <= s), so each lag costs two look-ups in a table of counts per ms. Per day also the same at the mid of Bybit's book (cts).
Output: L20_OUT/s3/leadlag.parquet (day, lag, rho_last, rho_mid). Usage: python l20_s3_leadlag.py [DAY ...]"""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
LAGS = np.arange(-1000, 1001)


def hy_profile(tx, x, ty, y, lags):
    keep = np.nonzero(np.diff(x))[0] + 1                      # only X's changes matter
    s, e, dx = tx[keep - 1], tx[keep], x[keep] - x[keep - 1]
    norm = np.sqrt((dx ** 2).sum() * (np.diff(y) ** 2).sum())
    base = min(tx[0], ty[0]) - lags.max() - 2; span = max(tx[-1], ty[-1]) - base + lags.max() + 3
    cnt = np.cumsum(np.bincount(ty - base, minlength=span)[:span]).astype(np.int32)   # cnt[t - base] = number of Y times <= t
    s0, e0 = s - base, e - base
    out = np.empty(len(lags))
    for i, tau in enumerate(lags):
        j0 = cnt[s0 + tau] - 1                                # last Y time <= s + tau: Y read tau later
        j1 = cnt[e0 + tau - 1]                                # first Y time >= e + tau
        ok = (j0 >= 0) & (j1 < len(y))
        out[i] = (dx[ok] * (y[j1[ok]] - y[j0[ok]])).sum() / norm
    return out


if __name__ == "__main__":
    days = L20.day_list()
    rows = []; t0 = time.time()
    for d in days:
        X = pl.read_parquet(L20.ORD / f"binance_px_{d}.parquet").sort("ts")
        Y = pl.read_parquet(L20.ORD / f"bybit_px_{d}.parquet").sort("ts")
        M = pl.read_parquet(L20.STATE / f"{d}.parquet", columns=["ts", "bid", "ask"]).sort("ts").group_by("ts", maintain_order=True).agg(
            ((pl.col("bid") + pl.col("ask")) / 20).last().alias("mid"))
        tx, x = X["ts"].to_numpy(), X["px"].to_numpy()
        r_last = hy_profile(tx, x, Y["ts"].to_numpy(), Y["px"].to_numpy(), LAGS)
        r_mid = hy_profile(tx, x, M["ts"].to_numpy(), M["mid"].to_numpy(), LAGS)
        rows.append(pl.DataFrame(dict(day=[d] * len(LAGS), lag=LAGS, rho_last=r_last, rho_mid=r_mid)))
        print(d, f"{time.time() - t0:.0f} s, peak last {LAGS[r_last.argmax()]} ms ({r_last.max():.3f}), peak mid {LAGS[r_mid.argmax()]} ms ({r_mid.max():.3f}),"
              f" LLR {(r_last[LAGS > 0] ** 2).sum() / (r_last[LAGS < 0] ** 2).sum():.2f}", flush=True)
    pl.concat(rows).write_parquet(OUT / f"{L20.tag()}leadlag.parquet")
