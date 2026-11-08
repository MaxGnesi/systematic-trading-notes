"""Lecture 22 §3, step 2: one pass over the book of one day (engine time cts), for two things the order table cannot give.
Pulls (Lecture 18's rule): in each book message, the levels among the best 20 of a side whose size fell by more than the trades at that price since the last message explain;
a pull is 5 or more such levels on one side. Refill (layer B, H1): for every real order of 1 BTC or more in L22_OUT/orders, the size it met at the prices it took (from the best before
it to its worst price), then at each probe time after it the size standing at those same prices, and the size standing over as many levels from the new best on the same side.
Output: L22_OUT/book/DAY.parquet (ts, nb, na, pull) and L22_OUT/refill/DAY.parquet. Usage: python l22_book.py YYYY-MM-DD"""
import heapq, sys, time
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L

DAY = sys.argv[1]; TOP, PULL = 20, 5; PROBES = (100, 500, 1_000, 2_000, 5_000, 10_000, 30_000, 60_000); t_start = time.time()
for d in ("book", "refill"): (L.OUT / d).mkdir(parents=True, exist_ok=True)
tr = pl.read_parquet(L.TRADES / f"{DAY}.parquet", columns=["ts", "tick", "size"]).sort("ts"); t_ts, t_tick, t_size = tr["ts"].to_numpy(), tr["tick"].to_numpy(), tr["size"].to_numpy()
T = pl.read_parquet(L.TRADES / f"{DAY}.parquet", columns=["ts", "side", "tick"]).group_by("ts", "side").agg(pl.col("tick").min().alias("lo"), pl.col("tick").max().alias("hi"))
O = pl.read_parquet(L.OUT / "orders" / f"{DAY}.parquet", columns=["ts", "side", "S"]).filter(pl.col("S") >= 1).join(T, on=["ts", "side"]).sort("ts")
o_ts, o_side, o_lo, o_hi = O["ts"].to_numpy(), O["side"].to_numpy(), O["lo"].to_numpy(), O["hi"].to_numpy()
probe_q = []; oi = 0; met = {}; rec = []                                                 # probe_q: probes due (time, order index, probe ms), a heap
bids, asks = {}, {}; out = []; prev_ts = None; ti = 0


def taken(i, book):
    """The prices order i took: from its first to its last trade price, on the side it took (asks for a buy)."""
    return range(o_lo[i], o_hi[i] + 1)


def level_sum(book, prices):
    return sum(book.get(p, 0.0) for p in prices)


def near_new_best(i, book):
    """As many levels as order i took, from the best now on the side it took."""
    k = o_hi[i] - o_lo[i] + 1
    if not book: return 0.0
    best = min(book) if o_side[i] == 1 else max(book)
    return level_sum(book, range(best, best + k) if o_side[i] == 1 else range(best - k + 1, best + 1))


def apply(ts, rows):
    """One message: record orders arriving before it and probes due before it, count unexplained decreases among the best TOP levels, then apply the changes."""
    global ti, prev_ts, oi
    while oi < len(o_ts) and o_ts[oi] <= ts:                                          # the book as the order met it: the last message at or before it
        book = asks if o_side[oi] == 1 else bids; met[oi] = level_sum(book, taken(oi, book))
        for pr in PROBES: heapq.heappush(probe_q, (o_ts[oi] + pr, oi, pr))
        oi += 1
    while probe_q and probe_q[0][0] <= ts:
        _, i, pr = heapq.heappop(probe_q); book = asks if o_side[i] == 1 else bids; rec.append((i, pr, level_sum(book, taken(i, book)), near_new_best(i, book)))
    traded = {}
    if prev_ts is not None:
        while ti < len(t_ts) and t_ts[ti] <= ts:
            if t_ts[ti] > prev_ts: traded[t_tick[ti]] = traded.get(t_tick[ti], 0.0) + t_size[ti]
            ti += 1
    snap = rows[0][0] == 1
    if snap: bids.clear(); asks.clear()
    nb = na = 0
    if not snap and bids and asks:
        topb = set(sorted(bids, reverse=True)[:TOP]); topa = set(sorted(asks)[:TOP])
        for _, s, p, q in rows:
            book, top = (bids, topb) if s == 1 else (asks, topa)
            if p in top and q < book[p] - traded.get(p, 0.0) - 1e-9:
                if s == 1: nb += 1
                else: na += 1
    for _, s, p, q in rows:
        book = bids if s == 1 else asks
        if q == 0: book.pop(p, None)
        else: book[p] = q
    out.append((ts, nb, na)); prev_ts = ts


pf = pq.ParquetFile(L.BOOK / f"{DAY}.parquet"); cur_u, msg = None, []
for batch in pf.iter_batches(batch_size=2_000_000, columns=["cts", "u", "snap", "side", "tick", "size"]):
    ts, u, sn, sd, tk, sz = (batch.column(i).to_numpy() for i in range(6))
    for k in range(len(u)):
        if u[k] != cur_u:
            if msg: apply(msg_ts, msg)
            cur_u, msg_ts, msg = u[k], ts[k], []
        msg.append((sn[k], sd[k], tk[k], sz[k]))
if msg: apply(msg_ts, msg)
pl.DataFrame(out, schema=["ts", "nb", "na"], orient="row").with_columns(((pl.col("nb") >= PULL) | (pl.col("na") >= PULL)).alias("pull")).write_parquet(L.OUT / "book" / f"{DAY}.parquet")
R = pl.DataFrame(rec, schema=["i", "probe", "fixed", "near"], orient="row").with_columns(pl.col("i").replace_strict({i: v for i, v in met.items()}, default=None).alias("met"),
                                                                                          pl.col("i").replace_strict(dict(enumerate(o_ts.tolist())), default=None).alias("ts"),
                                                                                          pl.col("i").replace_strict(dict(enumerate(o_side.tolist())), default=None).alias("side"))
R.drop("i").write_parquet(L.OUT / "refill" / f"{DAY}.parquet")
print(f"{DAY}: {len(out):,} book messages, {len(o_ts):,} orders of 1 BTC or more, {R.height:,} probes, {time.time() - t_start:.0f} s")
