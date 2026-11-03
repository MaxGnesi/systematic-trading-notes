"""Lecture 21 §3.2: what our taker orders meet after the latency gap. Decision moments: one at a random millisecond inside every 10 s of the day
(8,640 a day, seeded by the day). At each moment t, for a buy and a sell of each size S, the order is priced twice:
  expected: walking the book as published at t (the book we decide on);
  paid:     walking the book our order meets at t + L: the last update at or before t + L, less the size taken by the trades at each price since
            that update (§2.1; trades stamped in the same millisecond as the update are already in it).
An immediate-or-cancel (IOC) order at the best price seen at t takes what stands at that price or better at t + L; a limit order takes the same
and rests with the remainder. Afterwards: the move of the mid from t over 1 s and 10 s, signed for the order (positive: in its favour), and the
realised volatility of the hour (1-s mid returns). Prices are in bp of the mid at t; slippage = paid - expected, positive is a cost.
The book is read to all 200 levels Bybit publishes; where these hold less than S (thin books, or a sweep through them just before t + L),
the price is left empty (NaN) and counted, not filled in. A walk that ends within K levels does not depend on K: --complete recomputes only
the moments left empty by an earlier run with fewer levels, which gives the same result as a full run with 200.
Output: L21_OUT/s32/orders/<day>.parquet, one row per moment, side, L and S. Usage: python l21_s32_latency.py [--complete] [DAY ...] (all days if none)."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from l21_ladder import ladders
try:
    import psutil
except ImportError:
    psutil = None
OUT = L21.OUT / "s32" / "orders"; OUT.mkdir(parents=True, exist_ok=True)
SIZES = (0.001, 0.01, 0.1, 1.0, 5.0); LATS = (10, 50, 100); K = 200; STEP = 10_000


def wait_memory(gb=0.4):
    while psutil and psutil.virtual_memory().available / 2**30 < gb: time.sleep(5)


def walk(P, Z, S):
    """Average price (ticks) of S walking levels P with sizes Z, row by row; NaN where the K levels hold less than S."""
    cz = np.cumsum(Z, axis=1); take = np.minimum(np.maximum(S - (cz - Z), 0.0), Z)
    avg = (take * P).sum(axis=1) / S
    return np.where(cz[:, -1] >= S - 1e-12, avg, np.nan)


def day_orders(day, t=None):
    S0 = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts")
    ts, bid, ask = (S0[c].to_numpy() for c in ("ts", "bid", "ask")); mid = (bid + ask) / 2
    T = pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).sort("ts")
    d0 = L21.ms(day); rng = np.random.default_rng(int(day.replace("-", "")))
    if t is None: t = d0 + np.arange(0, 86_400_000 - STEP, STEP) + rng.integers(0, STEP, 86_400_000 // STEP - 1)
    t = t[t >= ts[0]]
    at = lambda x: np.searchsorted(ts, x, side="right") - 1                       # last update at or before x
    m0 = mid[at(t)]
    ret = {h: (mid[at(t + h)] - m0) / m0 * 1e4 for h in (1000, 10_000)}
    # realised volatility of each hour: 1-s mid returns, in bp
    g = d0 + np.arange(0, 86_400_001, 1000); mg = mid[np.maximum(at(g), 0)]; r1 = np.diff(mg) / mg[:-1] * 1e4
    vol_h = np.sqrt((r1.reshape(24, 3600) ** 2).sum(axis=1)); vol = vol_h[(t - d0) // 3_600_000]
    # the books: at t, and at the last update at or before t + L
    need = np.unique(np.r_[t, *(t + L for L in LATS)])
    Lb = ladders(day, need, K=K, best=(bid[at(need)], ask[at(need)]))
    row = lambda x: np.searchsorted(need, x)
    rows = []
    for sd, px_k, sz_k, tside in ((1, "ask_px", "ask_sz", 1), (-1, "bid_px", "bid_sz", -1)):   # a buy walks the asks, taken by taker buys
        i0 = row(t); P0, Z0 = Lb[px_k][i0].astype(float), Lb[sz_k][i0]
        X = T.filter(pl.col("side") == tside); tt, tk, tz = (X[c].to_numpy() for c in ("ts", "tick", "size"))
        exp = {S: walk(P0, Z0, S) for S in SIZES}
        best0 = Lb[px_k][i0, 0]
        for L in LATS:
            iL = row(t + L); P, Z = Lb[px_k][iL].astype(float), Lb[sz_k][iL].copy()
            u = ts[at(t + L)]                                                       # the update our order meets
            a, b = np.searchsorted(tt, u, side="right"), np.searchsorted(tt, t + L, side="right")
            for j in np.nonzero(b > a)[0]:                                          # trades since that update take size from its levels
                for p, z in zip(tk[a[j]:b[j]], tz[a[j]:b[j]]):
                    k = np.nonzero(Lb[px_k][iL[j]] == p)[0]
                    if len(k): Z[j, k[0]] = max(Z[j, k[0]] - z, 0.0)
            reach = (P <= best0[:, None]) if sd == 1 else (P >= best0[:, None])      # levels at the seen best price or better
            avail = (Z * reach * (P > 0)).sum(axis=1)
            for S in SIZES:
                paid = walk(P, Z, S)
                rows.append(pl.DataFrame({
                    "t": t, "side": np.full(len(t), sd, np.int8), "L": np.full(len(t), L, np.int16), "S": np.full(len(t), S, np.float32),
                    "exp_bp": (sd * (exp[S] - m0) / m0 * 1e4).astype(np.float32), "paid_bp": (sd * (paid - m0) / m0 * 1e4).astype(np.float32),
                    "ioc_fill": (np.minimum(avail, S) / S).astype(np.float32), "spread_bp": ((ask[at(t)] - bid[at(t)]) / m0 * 1e4).astype(np.float32),
                    "ret1_bp": (sd * ret[1000]).astype(np.float32), "ret10_bp": (sd * ret[10_000]).astype(np.float32), "vol_h": vol.astype(np.float32)}))
    return pl.concat(rows)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--complete"]; complete = "--complete" in sys.argv
    days = args or sorted(p.stem for p in L21.STATE.glob("*.parquet"))
    if complete:
        for day in days:
            f = OUT / f"{day}.parquet"; D = pl.read_parquet(f)
            redo = np.unique(D.filter(pl.col("exp_bp").is_nan() | pl.col("paid_bp").is_nan())["t"].to_numpy())
            if not len(redo): continue
            wait_memory(); t0 = time.time(); N = day_orders(day, redo)
            D = pl.concat([D.filter(~pl.col("t").is_in(redo)), N]).sort("t", "side", "L", "S"); D.write_parquet(f)
            print(day, len(redo), "moments redone", f"{time.time() - t0:.0f} s", "still empty", D.filter(pl.col("paid_bp").is_nan()).height, flush=True)
        sys.exit()
    for day in days:
        f = OUT / f"{day}.parquet"
        if f.exists() and not sys.argv[1:]: continue
        wait_memory(); t0 = time.time()
        D = day_orders(day); D.write_parquet(f)
        g = D.filter(pl.col("L") == 50).group_by("S").agg((pl.col("paid_bp") - pl.col("exp_bp")).mean().alias("slip"),
                                                          (pl.col("ioc_fill") < 1).mean().alias("ioc_short"), pl.col("paid_bp").is_nan().mean().alias("deep")).sort("S")
        print(day, f"{time.time() - t0:.0f} s", g.rows(), flush=True); del D
