"""Lecture 18 §5: large market orders against the book just before them, every day. A market order = all fills of one side in the same millisecond.
For every order of at least 1 BTC: the book as of its last message before the order (engine time, cts); the price that walking that book predicted;
the average price actually paid; the fade, how much worse the order did than predicted, in bp of the mid (positive = worse). Context: the mid's move
and the traded volume in the second before. Refill, for orders of at least 2 BTC: the depth within 5 bp on the side taken, just before, and the time
until it is back to 90% of that (up to 60 s). Output: L18_OUT/sweeps/DAY.parquet. With --lag=MS, each order is judged against the book as of
its last message MS milliseconds before it, as a trader with a view that much older (output: L18_OUT/sweeps_lagMS). Usage: python l18_sweeps.py [--lag=MS] [DAY ...] (default: all days not done)."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
ROOT = L18.PARQUET; LAG = next((int(a[6:]) for a in sys.argv if a.startswith("--lag=")), 0)
OUT = L18.OUT / ("sweeps" if LAG == 0 else f"sweeps_lag{LAG}"); OUT.mkdir(exist_ok=True)
BAND, MIN_BTC, REFILL_BTC = 5e-4, 1.0, 2.0
days = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(p.stem for p in (ROOT / "orderbook" / "BTCUSDT").glob("*.parquet"))


def walk(levels, size):
    left, cost = size, 0.0
    for p, q in levels:
        x = min(left, q); cost += x * p; left -= x
        if left <= 1e-12: return cost / size
    return None


def side_depth(book, mid, s):
    return sum(q for p, q in book.items() if (p <= mid * (1 + BAND) if s == 1 else p >= mid * (1 - BAND)))


for day in days:
    if (OUT / f"{day}.parquet").exists(): continue
    t0 = time.time()
    tr = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).sort("ts")
    orders = (tr.group_by("ts", "side", maintain_order=True).agg(pl.col("size").sum().alias("btc"), ((pl.col("tick") * pl.col("size")).sum() / pl.col("size").sum()).alias("vwap"),
                                                               pl.len().alias("fills")))
    vol_1s = tr.with_columns((pl.col("ts") // 1000).alias("s")).group_by("s").agg(pl.col("size").sum().alias("v"))
    big = orders.filter(pl.col("btc") >= MIN_BTC).sort("ts")
    O_ts, O_side, O_btc, O_vwap, O_fills = (big[c].to_numpy() for c in ("ts", "side", "btc", "vwap", "fills"))
    b = pl.read_parquet(ROOT / "orderbook" / "BTCUSDT" / f"{day}.parquet", columns=["cts", "snap", "side", "tick", "size"])
    bt, sn, sd, tk, sz = (b[c].to_numpy() for c in ("cts", "snap", "side", "tick", "size"))
    starts = np.flatnonzero(np.r_[True, np.diff(bt) != 0])
    bids, asks = {}, {}; j = 0; rows = []; pending = []; mids = []                   # pending refills: [row index, side, target depth, t_order]
    for k, a in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(b)
        while j < len(O_ts) and O_ts[j] - LAG < bt[a]:
            if bids and asks:
                bb, ba = max(bids), min(asks); mid = (bb + ba) / 2; s = O_side[j]
                lv = sorted(asks.items()) if s == 1 else sorted(bids.items(), reverse=True)
                pred = walk(lv, O_btc[j])
                d_before = side_depth(asks if s == 1 else bids, mid, s)
                rows.append(dict(ts=int(O_ts[j]), side=int(s), btc=float(O_btc[j]), fills=int(O_fills[j]), mid=mid / 10,
                                 predicted_bp=None if pred is None else s * (pred / mid - 1) * 1e4, actual_bp=s * (O_vwap[j] / mid - 1) * 1e4,
                                 depth_before=d_before, refill_s=None))
                if O_btc[j] >= REFILL_BTC and d_before > 0: pending.append([len(rows) - 1, s, 0.9 * d_before, O_ts[j]])
            j += 1
        if sn[a] == 1: bids.clear(); asks.clear()
        for s_, p, q in zip(sd[a:e].tolist(), tk[a:e].tolist(), sz[a:e].tolist()):
            bk = bids if s_ == 1 else asks
            if q == 0: bk.pop(p, None)
            else: bk[p] = q
        if bids and asks: mids.append((int(bt[a]), (max(bids) + min(asks)) / 20))
        if pending and bids and asks:
            mid = (max(bids) + min(asks)) / 2; keep = []
            for item in pending:
                i, s, target, t_ord = item
                if bt[a] <= t_ord: keep.append(item); continue
                if side_depth(asks if s == 1 else bids, mid, s) >= target: rows[i]["refill_s"] = (bt[a] - t_ord) / 1000
                elif bt[a] - t_ord < 60_000: keep.append(item)
                else: rows[i]["refill_s"] = 60.0
            pending = keep
    R = pl.DataFrame(rows, schema_overrides={"predicted_bp": pl.Float64, "refill_s": pl.Float64})
    M = pl.DataFrame(mids, schema=["mts", "m"], orient="row").sort("mts")
    R = R.sort("ts").with_columns((pl.col("ts") - 1000).alias("t_1s")).join_asof(M, left_on="t_1s", right_on="mts", strategy="backward")
    R = R.with_columns(((pl.col("mid") / pl.col("m") - 1).abs() * 1e4).alias("move_1s_bp"), (pl.col("ts") // 1000 - 1).alias("s")).join(vol_1s, on="s", how="left")
    R = R.with_columns((pl.col("actual_bp") - pl.col("predicted_bp")).alias("fade_bp"), pl.lit(day).alias("day")).rename({"v": "vol_1s"}).drop("t_1s", "mts", "m", "s")
    R.write_parquet(OUT / f"{day}.parquet")
    print(day, f"{time.time() - t0:.0f} s, orders >= {MIN_BTC} BTC: {len(R)}, median fade {R['fade_bp'].median():.2f} bp", flush=True)
