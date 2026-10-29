"""Lecture 18 §4: where do trades happen relative to the book just before them (last message by engine time, cts)? Each trade is classed by its
price against the best price on the side it traded against (best ask for a buy, best bid for a sell): at the best; worse than the best (it walked
deeper: part of a sweep); better than the best (the book had moved since its last message, up to 100 ms earlier). Also: is the trade price at the
best of the NEXT message (the book after the trade)? And the same split for the first trade of each millisecond only (one aggressive order may fill
at several prices in the same millisecond). Usage: python l18_trade_vs_book.py DAY"""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
DAY = sys.argv[1]; ROOT = L18.PARQUET; HERE = L18.OUT
book = pl.read_parquet(ROOT / "orderbook" / "BTCUSDT" / f"{DAY}.parquet", columns=["cts", "snap", "side", "tick", "size"])
tr = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "side", "tick"]).sort("ts")
T_ts, T_side, T_tick = tr["ts"].to_numpy(), tr["side"].to_numpy(), tr["tick"].to_numpy()
first_in_ms = np.r_[True, np.diff(T_ts) != 0]
bt, sn, sd, tk, sz = (book[c].to_numpy() for c in ("cts", "snap", "side", "tick", "size"))
starts = np.flatnonzero(np.r_[True, np.diff(bt) != 0])
cls = np.full(len(T_ts), -9, np.int8)                                              # -1 better than best, 0 at best, 1 deeper, 2 not on a level
pending = []                                                                        # trades waiting for the next book state
next_best = np.zeros(len(T_ts), bool)
bids, asks = {}, {}; j = 0
for k, a in enumerate(starts):
    e = starts[k + 1] if k + 1 < len(starts) else len(book)
    while j < len(T_ts) and T_ts[j] < bt[a]:
        if bids and asks:
            p = T_tick[j]
            if T_side[j] == 1: best = min(asks); cls[j] = 0 if p == best else (1 if p > best else -1)
            else: best = max(bids); cls[j] = 0 if p == best else (1 if p < best else -1)
            pending.append(j)
        j += 1
    if sn[a] == 1: bids.clear(); asks.clear()
    for s, p, q in zip(sd[a:e].tolist(), tk[a:e].tolist(), sz[a:e].tolist()):
        bk = bids if s == 1 else asks
        if q == 0: bk.pop(p, None)
        else: bk[p] = q
    if pending and bids and asks:                                                    # the book after: was the trade at its new best (refilled or moved)?
        for i in pending:
            nb = min(asks) if T_side[i] == 1 else max(bids)
            next_best[i] = abs(int(T_tick[i]) - nb) <= 1
        pending = []
ok = cls != -9
lab = {-1: "better than the best (book had moved)", 0: "at the best", 1: "deeper than the best (walked the book)"}
res = {}
for name, m in (("all trades", ok), ("first trade of each millisecond", ok & first_in_ms)):
    n = m.sum(); res[name] = {lab[c]: round(float((cls[m] == c).mean()), 4) for c in (-1, 0, 1)}; res[name]["trades"] = int(n)
    print(name, res[name])
res["better than best: at the best of the next message"] = round(float(next_best[ok & (cls == -1)].mean()), 4)
print("trades 'better than the best' that are at (within a tick of) the best of the next message:", res["better than best: at the best of the next message"])
(HERE / f"l18_trade_vs_book_{DAY}.json").write_text(json.dumps(res, indent=1))
