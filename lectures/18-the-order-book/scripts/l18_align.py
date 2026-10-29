"""Lecture 18 §4: which clock aligns the book with the trades? For every trade, the book as of the last message whose time (ts = sent, or cts =
matching engine, optionally shifted) is before the trade: was the trade's price a resting level on the side it traded against (asks for a buy,
bids for a sell), and was it at the best price? The clock that makes the most trades consistent is the one to use. Usage: python l18_align.py DAY"""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
DAY = sys.argv[1]; ROOT = L18.PARQUET; HERE = L18.OUT
book = pl.read_parquet(ROOT / "orderbook" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "cts", "snap", "side", "tick", "size"])
tr = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "side", "tick"]).sort("ts")
T_ts, T_side, T_tick = tr["ts"].to_numpy(), tr["side"].to_numpy(), tr["tick"].to_numpy()
side, tick, size, snap = (book[c].to_numpy() for c in ("side", "tick", "size", "snap"))
res = {}
for clock, shift in (("ts", 0), ("cts", 0), ("cts", -100), ("cts", 100)):
    bt = book[clock].to_numpy() + shift
    msg_start = np.flatnonzero(np.r_[True, np.diff(bt) != 0])                       # first row of each message
    bids, asks = {}, {}; j = 0; n = len(T_ts); on_level = at_best = checked = 0
    for k, a in enumerate(msg_start):
        e = msg_start[k + 1] if k + 1 < len(msg_start) else len(book)
        t_msg = bt[a]
        while j < n and T_ts[j] < t_msg:                                           # trades before this message: judged on the book so far
            if bids and asks:
                p = T_tick[j]
                if T_side[j] == 1: on = p in asks; best = p == min(asks)
                else: on = p in bids; best = p == max(bids)
                on_level += on; at_best += best; checked += 1
            j += 1
        if snap[a] == 1: bids.clear(); asks.clear()
        for s, p, q in zip(side[a:e].tolist(), tick[a:e].tolist(), size[a:e].tolist()):
            bk = bids if s == 1 else asks
            if q == 0: bk.pop(p, None)
            else: bk[p] = q
    key = f"{clock}{shift:+d} ms" if shift else clock
    res[key] = dict(trades=checked, on_a_resting_level=round(on_level / checked, 4), at_the_best=round(at_best / checked, 4))
    print(key, res[key], flush=True)
(HERE / f"l18_align_{DAY}.json").write_text(json.dumps(res, indent=1))
