"""Follow-up (not registered): did the price move ahead of the tariff post in the direction of the news? Return of Bybit's mid and Binance's last
trade over the h minutes before 20:50:01.702 (h = 1, 2, 5, 10, 15, 30, 60, 120), against windows ending at the same phase of every hour on the
other 44 days (hh:50:01.702), rank and one-sided p for a fall; return in bp and in units of each window's own typical move (z against reference).
Also the move after the post for scale (to 21:14 = T0 and to 21:30)."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("predrift")

DAYS = L20.days()
POST = int(np.datetime64("2025-10-10T20:50:01.702", "ms").astype(np.int64)); PH = POST % 3_600_000
by = pl.concat([pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "mid2"]) for d in DAYS]).unique("sec", keep="last").sort("sec")
bt, bp = (by["sec"].to_numpy() * 1000 + 999), by["mid2"].to_numpy() / 2.0          # mid at the end of each second
bn = pl.concat([pl.read_parquet(L20.ORD / f"binance_px_{d}.parquet") for d in DAYS]).sort("ts")
nt, npx = bn["ts"].to_numpy(), bn["px"].to_numpy()
px = lambda T, P, t: P[np.searchsorted(T, t, side="right") - 1]                        # last value at or before t
t0 = int(np.datetime64(f"{DAYS[0]}T00:00:00", "ms").astype(np.int64)); t1 = int(np.datetime64(f"{DAYS[-1]}T23:59:59", "ms").astype(np.int64))
c0 = int(np.datetime64("2025-10-10T00:00:00", "ms").astype(np.int64))
ends = np.arange(t0 + PH, t1, 3_600_000); ends = ends[ends > t0 + 2 * 3_600_000]
for name, T, P in (("Bybit mid", bt, bp), ("Binance last", nt, npx)):
    print(name)
    for h in (1, 2, 5, 10, 15, 30, 60, 120):
        L = h * 60_000
        r = 1e4 * np.log(px(T, P, ends - 1) / px(T, P, ends - 1 - L))
        ref = r[(ends - L >= c0 + 86_400_000) | (ends <= c0)]
        x = 1e4 * np.log(px(T, P, POST - 1) / px(T, P, POST - 1 - L))
        print(f"  {h:4d} min before: {x:+7.1f} bp | rank {np.mean(ref < x):.3f} (share of {len(ref)} windows lower) | p(fall) = {(1 + (ref <= x).sum()) / (1 + len(ref)):.3f} | z = {x / ref.std():+.2f}")
    for lab, te in (("post -> T0 21:14", int(np.datetime64('2025-10-10T21:14:00', 'ms').astype(np.int64))), ("post -> 21:30", int(np.datetime64('2025-10-10T21:30:00', 'ms').astype(np.int64)))):
        print(f"  after: {lab}: {1e4 * np.log(px(T, P, te) / px(T, P, POST - 1)):+.0f} bp")
# minute path of the last 15 minutes before the post, Bybit mid
print("Bybit mid, last 15 min before the post (end of each minute):", [round(px(bt, bp, POST - 1 - k * 60_000) / 10, 1) for k in range(15, -1, -1)])
