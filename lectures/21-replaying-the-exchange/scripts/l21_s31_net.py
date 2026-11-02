"""Lecture 21 §3.1: what a 100 ms book hides at the best price. For every pair of consecutive book updates in which the best bid (ask) price stayed the
same: the change of its displayed size, and the size sold (bought) at that price by takers in between. The replay's inference (§2.1): trades first,
the rest of the change is cancelled (a decrease) or added (an increase). Where more was traded than the queue fell, size must have been added within
the same update without showing: a lower bound on the flow the book hides. Per day, from Lecture 19's book state and the trades.
Output: L21_OUT/s31/net_days.parquet. Usage: python l21_s31_net.py [DAY ...] (all days if none)."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
try:
    import psutil
except ImportError:
    psutil = None
OUT = L21.OUT / "s31"; OUT.mkdir(parents=True, exist_ok=True)


def wait_memory(gb=0.4):
    while psutil and psutil.virtual_memory().available / 2**30 < gb: time.sleep(5)


def side(ts, px, q, tt, tp, tz):
    """Intervals between consecutive updates with the same best price on one side: change of size, size traded at that price in between."""
    same = px[1:] == px[:-1]
    a, b, p = ts[:-1][same], ts[1:][same], px[1:][same]
    dq = q[1:][same] - q[:-1][same]
    # trades at the best price inside (a, b]: cumulative sums over trades sorted by time, per price via a joint key
    o = np.lexsort((tt, tp)); tt, tp, tz = tt[o], tp[o], tz[o]; cz = np.r_[0.0, np.cumsum(tz)]
    key = lambda price, t: np.searchsorted(tp * 10**13 + tt, price * 10**13 + t, side="right")
    tr = cz[key(p, b)] - cz[key(p, a)]
    added = np.maximum(dq + tr, 0.0); cancelled = np.maximum(-(dq + tr), 0.0)
    hidden = np.minimum(added, tr)                           # traded and refilled within the same update
    return dict(n=int(same.sum()), n_traded=int((tr > 0).sum()), n_hidden=int((hidden > 1e-9).sum()), traded=float(tr.sum()),
                hidden=float(hidden.sum()), added=float(added.sum()), cancelled=float(cancelled.sum()))


if __name__ == "__main__":
    days = sys.argv[1:] or sorted(p.stem for p in L21.STATE.glob("*.parquet"))
    rows = []
    for day in days:
        wait_memory(); t0 = time.time()
        S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask", "q_bid", "q_ask"]).sort("ts")
        T = pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"])
        ts = S["ts"].to_numpy()
        for nm, px, q, sd in (("bid", S["bid"].to_numpy(), S["q_bid"].to_numpy(), -1), ("ask", S["ask"].to_numpy(), S["q_ask"].to_numpy(), 1)):
            X = T.filter(pl.col("side") == sd)
            r = side(ts, px, q, X["ts"].to_numpy(), X["tick"].to_numpy(), X["size"].to_numpy())
            rows.append(dict(day=day, side=nm, **r))
        print(day, f"{time.time() - t0:.0f} s", flush=True); del S, T
    D = pl.DataFrame(rows); D.write_parquet(OUT / (("check_" if sys.argv[1:] else "") + "net_days.parquet"))
    A = D.group_by("side").agg(pl.col("traded", "hidden", "added", "cancelled", "n", "n_traded", "n_hidden").sum())
    print(A.with_columns((pl.col("hidden") / pl.col("traded")).alias("hidden_share_of_traded"), (pl.col("n_hidden") / pl.col("n_traded")).alias("share_intervals_hidden")))
