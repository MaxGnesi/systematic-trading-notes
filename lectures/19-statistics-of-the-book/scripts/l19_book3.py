"""Lecture 19 §4 (H14, H16): the heavy pass of l19_book2.py without the imbalance samples and spoof candidates, recording the time of every
refilling chain (3rd refill in a row) and the publish delay ts - cts of every book update. Output: L19_OUT/s3/b3_ice_DAY.parquet, b3_lag_DAY.parquet.
Based on: Lecture 19 §3, heavy pass over the full book with the trades (hypotheses H6, H7, H9-H11 and icebergs in results/hypotheses.md). One day, streamed.
Every level of the book is a first-in, first-out line of chunks (size, time joined): increases join the back; decreases are taken from the front
up to the trades at that price in the interval, the rest is cancelled from the back. Per update, at the sampled moments of L19_OUT/s3/samples_DAY
only: I5 weighted by distance (exp(-k/lam), k ticks behind the best), and by distance with depth younger than tau left out; the time to empty
of each best queue over the previous second. At every minute: depth in the best 10 levels of both sides. Spoof candidates: increases of at least
2 BTC at 1-9 ticks behind the best, followed until removed (life, traded or not), with the change of plain and weighted I5 they caused.
Queue totals at the best: added, traded, cancelled. Icebergs: refills at the same price within 1 s of being traded away, chains of 3 or more.
Output: L19_OUT/s3/b2_*_DAY. Usage: python l19_book2.py DAY [...]"""
import json, math, sys, time, heapq
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq, psutil
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
OUT = L19.S3; ROOT = L19.PARQUET
LAMS = [0.5, 1, 1.5, 3, 5]; TAUS = [0.25, 0.5, 1, 2, 5]; LAM0 = 1.5; QMIN_C, TMAX_C = 2.0, 5000


def guard(mb=800):
    for _ in range(120):
        if psutil.virtual_memory().available / 2**20 > mb: return
        time.sleep(30)
    sys.exit("memory stayed short; stopped")


def run(day):
    d0 = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000); d1 = d0 + 86_400_000
    samp = set(); ICE = []; LAG = []
    tr = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).sort("ts")
    t_ts, t_sd, t_tk, t_sz = (tr[c].to_numpy() for c in ("ts", "side", "tick", "size")); ti = 0
    book = {1: {}, -1: {}}; chunks = {1: {}, -1: {}}                               # size per tick; deque of [size, t] per tick
    S_rows, C_rows, M_rows = [], [], []
    Q = {s: {"added": 0.0, "traded": 0.0, "cancelled": 0.0} for s in (1, -1)}
    dep = {1: deque(), -1: deque()}; depsum = {1: 0.0, -1: 0.0}; last_best = {1: None, -1: None}
    cand = {}; ice = {}; ice_chains = 0; ice_refills = 0; pend = {}
    next_min = (d0 // 60000) * 60000; prev_ct = None

    def best(s):
        b = book[s]
        return (max(b) if s == 1 else min(b)) if b else None

    def top(s, n):
        b = book[s]
        return heapq.nlargest(n, b) if s == 1 else heapq.nsmallest(n, b)

    def aged(s, p, t, tau):
        lim = t - tau * 1000; return sum(c[0] for c in chunks[s].get(p, ()) if c[1] <= lim)

    def i5(t, lam=None, tau=None, extra=None):
        """I5 over the best 5 levels; lam: distance weight; tau: only depth that has rested tau s; extra: (side, tick, size) taken out."""
        v = {}
        for s in (1, -1):
            lv = top(s, 5); b0 = lv[0]; tot = 0.0
            for p in lv:
                q = aged(s, p, t, tau) if tau else book[s][p]
                if extra and extra[0] == s and extra[1] == p: q = max(q - extra[2], 0.0) if not tau else q
                w = math.exp(-abs(p - b0) / lam) if lam else 1.0; tot += w * q
            v[s] = tot
        return (v[1] - v[-1]) / (v[1] + v[-1]) if v[1] + v[-1] > 0 else 0.0

    def apply(ct, rows):
        nonlocal ti, prev_ct, ice_chains, ice_refills, next_min
        traded = {}
        if prev_ct is not None:
            while ti < len(t_ts) and t_ts[ti] <= ct:
                if t_ts[ti] > prev_ct:
                    k = (-int(t_sd[ti]), int(t_tk[ti])); traded[k] = traded.get(k, 0.0) + float(t_sz[ti])  # a buy (+1) hits the asks (-1)
                ti += 1
        else:
            while ti < len(t_ts) and t_ts[ti] <= ct: ti += 1
        if rows[0][0] == 1:
            for s in (1, -1): book[s].clear(); chunks[s].clear()
            cand.clear()
        bb = {s: best(s) for s in (1, -1)}; new_c = []
        for sn, s, p, q in rows:
            old = book[s].get(p, 0.0); ch = chunks[s].setdefault(p, deque())
            tq = traded.get((s, p), 0.0)
            if q > old:
                ch.append([q - old, ct]); add = q - old
                if bb[s] is not None and sn == 0:
                    off = abs(p - bb[s])
                    pass
                    if p == bb[s]: Q[s]["added"] += add; dep_add(s, ct, -add)
                # iceberg: a level traded away and back within 1 s at a similar size
                k = (s, p)
                if k in pend and ct - pend[k][0] <= 1000 and abs(q - pend[k][1]) <= 0.2 * pend[k][1]: refill(k, ct)
                pend.pop(k, None)
            elif q < old:
                dec = old - q; take = min(dec, tq); canc = dec - take
                while take > 1e-12 and ch:
                    x = min(take, ch[0][0]); ch[0][0] -= x; take -= x
                    if ch[0][0] <= 1e-12: ch.popleft()
                while canc > 1e-12 and ch:
                    x = min(canc, ch[-1][0]); ch[-1][0] -= x; canc -= x
                    if ch[-1][0] <= 1e-12: ch.pop()
                if bb[s] is not None and p == bb[s] and sn == 0:
                    Q[s]["traded"] += min(dec, tq); Q[s]["cancelled"] += dec - min(dec, tq); dep_add(s, ct, dec)
                if tq >= 0.8 * old and old > 0:
                    if q == 0: pend[(s, p)] = (ct, old)
                    elif abs(q - old) <= 0.2 * old: refill((s, p), ct)
            if q == 0: book[s].pop(p, None); chunks[s].pop(p, None)
            else: book[s][p] = q
            c = cand.get((s, p))
            if c is not None:
                if tq > 0: c["traded"] = True
                if q <= c["base"] + 0.2 * c["add"]:
                    C_rows.append((c["t"], s, p, c["add"], c["off"], ct - c["t"], c["traded"], True, c["d_plain"], c["d_dist"], c["d_age"])); del cand[(s, p)]
        if not (book[1] and book[-1]):
            prev_ct = ct; return
        nb = {s: best(s) for s in (1, -1)}
        for s in (1, -1):
            if nb[s] != last_best[s]: dep[s].clear(); depsum[s] = 0.0; last_best[s] = nb[s]
            while dep[s] and dep[s][0][0] < ct - 1000: depsum[s] -= dep[s].popleft()[1]
        # spoof candidates: the change of I5 that the addition caused
        for s, p, add, off, old in new_c:
            if p in top(s, 5):
                ip = i5(ct); idl = i5(ct, lam=LAM0)                    # with tau, new depth counts zero: d_age = 0 by construction
                ip0 = i5(ct, extra=(s, p, add)); idl0 = i5(ct, lam=LAM0, extra=(s, p, add))
                cand[(s, p)] = dict(t=ct, add=add, off=off, base=old, traded=False, d_plain=ip - ip0, d_dist=idl - idl0, d_age=0.0)
            else:
                cand[(s, p)] = dict(t=ct, add=add, off=off, base=old, traded=False, d_plain=float("nan"), d_dist=float("nan"), d_age=float("nan"))
        for k in [k for k, c in cand.items() if ct - c["t"] > TMAX_C]:
            c = cand.pop(k); C_rows.append((c["t"], k[0], k[1], c["add"], c["off"], ct - c["t"], c["traded"], False, c["d_plain"], c["d_dist"], c["d_age"]))
        if ct in samp:
            r = [ct] + [i5(ct, lam=l) for l in LAMS] + [i5(ct, lam=LAM0, tau=t) for t in TAUS]
            for s in (1, -1):
                q = book[s][nb[s]]; r.append(q / depsum[s] if depsum[s] > 0 else float("inf"))
            S_rows.append(tuple(r))
        while ct >= next_min:
            if d0 <= next_min < d1:
                M_rows.append((next_min, sum(book[1][p] for p in top(1, 10)), sum(book[-1][p] for p in top(-1, 10)), nb[1], nb[-1]))
            next_min += 60000
        prev_ct = ct

    def dep_add(s, ct, x):
        dep[s].append((ct, x)); depsum[s] += x

    def refill(k, ct):
        nonlocal ice_chains, ice_refills
        ice_refills += 1; st = ice.get(k)
        if st is None or ct - st[0] > 10_000: st = [ct, 0]
        st[0] = ct; st[1] += 1; ice[k] = st
        if st[1] == 3: ice_chains += 1; ICE.append((ct, k[0], k[1]))

    pf = pq.ParquetFile(ROOT / "orderbook" / "BTCUSDT" / f"{day}.parquet"); cur = None; rows = []
    for batch in pf.iter_batches(batch_size=1_000_000, columns=["cts", "snap", "side", "tick", "size", "ts"]):
        ct_a, sn_a, sd_a, tk_a, sz_a, ts_a = (batch.column(i).to_numpy() for i in range(6))
        for ct, sn, sd, tk, sz, tt in zip(ct_a.tolist(), sn_a.tolist(), sd_a.tolist(), tk_a.tolist(), sz_a.tolist(), ts_a.tolist()):
            if ct != cur:
                if rows: apply(cur, rows)
                cur = ct; rows = []; LAG.append((ct, tt - ct))
            rows.append((sn, sd, tk, sz))
    if rows: apply(cur, rows)
    pl.DataFrame(ICE, schema=["t", "side", "tick"], orient="row").write_parquet(OUT / f"b3_ice_{day}.parquet")
    pl.DataFrame(LAG, schema=["cts", "lag"], orient="row").write_parquet(OUT / f"b3_lag_{day}.parquet")
    return len(ICE), len(LAG), ice_chains


for day in sys.argv[1:]:
    if (OUT / f"b3_lag_{day}.parquet").exists(): continue
    guard(); t0 = time.time(); n, w, c = run(day)
    print(day, f"{time.time() - t0:.0f} s, chains {n:,}/{c:,}, updates {w:,}, avail {psutil.virtual_memory().available // 2**20} MB", flush=True)
