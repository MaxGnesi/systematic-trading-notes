"""Lecture 20: order-flow imbalance at the best 10 levels of Bybit BTCUSDT, per second (engine time cts), from a replay of the book.
For each update, the contribution e_k at the k-th best level of each side (Cont, Kukanov and Stoikov, 2014, applied level by level as Xu, Gould
and Howison, 2019), added up per second. Per second also: last mid (ticks x 2, i.e. bid + ask), last book imbalance at the best, average size at
the best ((q_bid + q_ask) / 2), average depth in the best 10 levels of both sides, number of updates, and a flag if the book was reset (snapshot).
Output: L20_OUT/book10/DAY.parquet. Usage: python l20_book10.py DAY [...]"""
import heapq, sys, time
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

ROOT = L20.PARQUET; OUT = Path(__file__).parent / "l20_book10"
K = 10

for day in sys.argv[1:]:
    if (OUT / f"{day}.parquet").exists(): continue
    t0 = time.time(); bids, asks = {}, {}; rows = []; cur = None
    prev = None                     # previous top-10: (bid prices, bid sizes, ask prices, ask sizes)
    sec = None; acc = None

    def flush():
        if acc is not None: rows.append(acc)

    def close(ts, reset):
        global prev, sec, acc
        if not (bids and asks): return
        bp = heapq.nlargest(K, bids); ap = heapq.nsmallest(K, asks)
        if len(bp) < K or len(ap) < K: return
        bq = [bids[p] for p in bp]; aq = [asks[p] for p in ap]
        s = ts // 1000
        if s != sec:
            flush(); sec = s
            acc = [s] + [0.0] * K + [0, 0.0, 0.0, 0.0, 0, 0]      # sec, ofi_1..ofi_K, mid2, I, q_best_sum, depth10_sum, n, reset
        if prev is not None and not reset:
            pb0, qb0, pa0, qa0 = prev
            for k in range(K):
                e = ((bq[k] if bp[k] >= pb0[k] else 0.0) - (qb0[k] if bp[k] <= pb0[k] else 0.0)
                     - (aq[k] if ap[k] <= pa0[k] else 0.0) + (qa0[k] if ap[k] >= pa0[k] else 0.0))
                acc[1 + k] += e
        if reset: acc[K + 6] = 1
        acc[K + 1] = bp[0] + ap[0]
        acc[K + 2] = (bq[0] - aq[0]) / (bq[0] + aq[0])
        acc[K + 3] += (bq[0] + aq[0]) / 2
        acc[K + 4] += sum(bq) + sum(aq)
        acc[K + 5] += 1
        prev = (bp, bq, ap, aq)

    pf = pq.ParquetFile(ROOT / "orderbook" / "BTCUSDT" / f"{day}.parquet")
    reset = False
    for batch in pf.iter_batches(batch_size=2_000_000, columns=["cts", "snap", "side", "tick", "size"]):
        ct, sn, sd, tk, sz = (batch.column(i).to_numpy() for i in range(5))
        for j in range(len(ct)):
            if ct[j] != cur:
                if cur is not None: close(cur, reset)
                cur = ct[j]; reset = False
                if sn[j] == 1: bids.clear(); asks.clear(); reset = True
            book = bids if sd[j] == 1 else asks
            if sz[j] == 0: book.pop(int(tk[j]), None)
            else: book[int(tk[j])] = float(sz[j])
    close(cur, reset); flush()
    cols = ["sec"] + [f"ofi_{k + 1}" for k in range(K)] + ["mid2", "I", "q_best_sum", "depth10_sum", "n", "reset"]
    S = pl.DataFrame(rows, schema=cols, orient="row")
    S = S.with_columns((pl.col("q_best_sum") / pl.col("n")).alias("q_best"), (pl.col("depth10_sum") / pl.col("n")).alias("depth10")).drop("q_best_sum", "depth10_sum")
    S.write_parquet(OUT / f"{day}.parquet")
    print(day, f"{time.time() - t0:.0f} s, seconds {len(S):,}, updates {int(S['n'].sum()):,}, resets {int(S['reset'].sum())}", flush=True)
