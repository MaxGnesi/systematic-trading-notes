"""Lecture 19: the state of the book after every update of one day (Bybit BTCUSDT, engine time cts), streamed from Parquet in batches.
Per update: best bid and ask (ticks), the size at each (BTC), and the size in the best 5 levels of each side. Output: L19_OUT/state/DAY.parquet.
Usage: python l19_state.py DAY [...]"""
import sys, time
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
ROOT = L19.PARQUET; OUT = L19.STATE; OUT.mkdir(exist_ok=True)

for day in sys.argv[1:]:
    if (OUT / f"{day}.parquet").exists(): continue
    t0 = time.time(); bids, asks = {}, {}; rows = []; cur = None; pending = []
    def close(ts):
        if bids and asks:
            b5 = sorted(bids, reverse=True)[:5]; a5 = sorted(asks)[:5]
            rows.append((ts, b5[0], a5[0], bids[b5[0]], asks[a5[0]], sum(bids[p] for p in b5), sum(asks[p] for p in a5)))
    pf = pq.ParquetFile(ROOT / "orderbook" / "BTCUSDT" / f"{day}.parquet")
    for batch in pf.iter_batches(batch_size=2_000_000, columns=["cts", "snap", "side", "tick", "size"]):
        ct, sn, sd, tk, sz = (batch.column(i).to_numpy() for i in range(5))
        for k in range(len(ct)):
            if ct[k] != cur:
                if cur is not None: close(cur)
                cur = ct[k]
                if sn[k] == 1: bids.clear(); asks.clear()
            book = bids if sd[k] == 1 else asks
            if sz[k] == 0: book.pop(int(tk[k]), None)
            else: book[int(tk[k])] = float(sz[k])
    close(cur)
    S = pl.DataFrame(rows, schema=["ts", "bid", "ask", "q_bid", "q_ask", "q_bid5", "q_ask5"], orient="row")
    S.write_parquet(OUT / f"{day}.parquet")
    print(day, f"{time.time() - t0:.0f} s, updates {len(S):,}", flush=True)
