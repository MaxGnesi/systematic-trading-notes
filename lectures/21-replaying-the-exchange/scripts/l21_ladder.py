"""Lecture 21: the book's levels near the best at chosen moments of one day, without rebuilding every update in memory. The day's book file is read
one row group at a time (about half an hour each); the state of the book at the end of each group is carried to the next; inside a group, the
messages of each price are kept sorted by time, so the size at any price at any moment is a binary search. A snapshot message resets the book:
levels it does not list are empty. Each message gives the new size at its price (0: the level is gone), so the size at a price at time t is that of
its last message at or before t, after the last snapshot.

ladders(day, times, K) -> for each time (ms, engine clock, sorted), the best K levels of each side as published at that time:
    bid_px, bid_sz, ask_px, ask_sz: arrays of shape (len(times), K), prices in ticks (0 where fewer than K levels exist), sizes in BTC."""
import numpy as np, polars as pl, pyarrow.parquet as pq
import l21 as L21


def _groups(day):
    f = pq.ParquetFile(L21.BOOK / f"{day}.parquet")
    for i in range(f.metadata.num_row_groups):
        yield pl.from_arrow(f.read_row_group(i, columns=["cts", "snap", "side", "tick", "size"])).sort("cts", maintain_order=True)


def ladders(day, times, K=50, best=None):
    """best: optional (bid, ask) arrays in ticks at each time (Lecture 19's state), used as the starting price; otherwise found from the book."""
    times = np.asarray(times, dtype=np.int64); n = len(times)
    out = {k: np.zeros((n, K), dtype=np.int64 if k.endswith("px") else float) for k in ("bid_px", "bid_sz", "ask_px", "ask_sz")}
    state = {1: {}, -1: {}}                                                  # side -> {tick: size}, the book before the current group
    j = 0
    for G in _groups(day):
        if j >= n: break
        c, sn, sd, tk, sz = (G[k].to_numpy() for k in ("cts", "snap", "side", "tick", "size"))
        snaps = np.unique(c[sn == 1])                                         # snapshot times in this group
        # per side and price: message times and sizes, sorted by time
        msgs = {}
        for s in (1, -1):
            m = sd == s; o = np.lexsort((c[m], tk[m])); T_, C_, Z_ = tk[m][o], c[m][o], sz[m][o]
            cut = np.r_[0, np.nonzero(np.diff(T_))[0] + 1, len(T_)]
            msgs[s] = {int(T_[a]): (C_[a:b], Z_[a:b]) for a, b in zip(cut[:-1], cut[1:])}
        g_end = c[-1]
        while j < n and times[j] <= g_end:
            t = times[j]
            s0 = snaps[snaps <= t]; s0 = s0[-1] if len(s0) else None              # last snapshot in this group before t
            for s, px_k, sz_k in ((1, "bid_px", "bid_sz"), (-1, "ask_px", "ask_sz")):
                def size_at(p):
                    m = msgs[s].get(p)
                    if m is not None:
                        k = np.searchsorted(m[0], t, side="right") - 1
                        if k >= 0 and (s0 is None or m[0][k] >= s0): return float(m[1][k])
                    return 0.0 if s0 is not None else state[s].get(p, 0.0)
                # candidate prices: every price with a message in this group or in the carried state
                cand = set(msgs[s]) | (set() if s0 is not None else set(state[s]))
                start = None if best is None else int(best[0 if s == 1 else 1][j])
                ps = sorted((p for p in cand if (start is None or (p <= start if s == 1 else p >= start))), reverse=(s == 1))
                got = 0
                for p in ps:
                    q = size_at(p)
                    if q > 0:
                        out[px_k][j, got] = p; out[sz_k][j, got] = q; got += 1
                        if got == K: break
            j += 1
        # carry the book to the next group: apply every message of the group in time order (last message per price after the last snapshot)
        if len(snaps):
            state = {1: {}, -1: {}}; keep = c >= snaps[-1]
        else:
            keep = np.ones(len(c), bool)
        L = pl.DataFrame({"side": sd[keep], "tick": tk[keep], "size": sz[keep]}).group_by("side", "tick").agg(pl.col("size").last())
        for s_, p_, q_ in L.iter_rows():
            if q_ == 0: state[s_].pop(p_, None)
            else: state[s_][p_] = q_
    return out
