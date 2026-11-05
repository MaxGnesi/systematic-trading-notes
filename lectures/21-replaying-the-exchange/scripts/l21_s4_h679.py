"""Lecture 21 §4 and §5: the jobs behind H6, H7 and H9. Usage: python l21_s4_h679.py h7|h9|h6 [DAY ...].
h7: real taker orders (trades with the same ms and side, as in Lecture 19), out of sample: all of 5 BTC or more, and a random 500 a day of each smaller class. Gap: the average
    price paid minus the price predicted by walking the last book before the order, signed so that positive is a cost, in bp of the mid. L21_OUT/s4/h7/<day>.parquet.
h9: resting orders 10 bp from the mid (Lecture 17's smallest step), out of sample, the half-hours of §3.3, one order a minute on each side, held up to 10 min. Fill times under Q1
    and Q2 (a = 1) and the mid 10 s after the fill. A price with no message in the window counts as an empty level: our order is first in line. L21_OUT/s4/h9/<day>.parquet.
h6: the test resting order and the once-a-second quoter (Q2, a = 1, L = 50 ms, 0.001 BTC) in the window of the cascade, 20:50-22:50 UTC, on every day. L21_OUT/s4/h6/<day>.parquet."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21, l21_mm as MM
from l21_ladder import ladders
from l21_s32_latency import walk
CLS = [0, 0.01, 0.1, 1, 5, np.inf]; LAB = ["< 0.01", "0.01-0.1", "0.1-1", "1-5", ">= 5"]
ALL = sorted(p.stem for p in L21.STATE.glob("*.parquet")); OOS = [d for d in ALL if d >= "2025-10-11"]


def h7(day):
    rng = np.random.default_rng(int(day.replace("-", "")))
    T = (pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).group_by("ts", "side")
         .agg(pl.col("size").sum().alias("q"), ((pl.col("tick") * pl.col("size")).sum() / pl.col("size").sum()).alias("p")).sort("ts"))
    q = T["q"].to_numpy(); c = np.searchsorted(CLS, q, side="right") - 1; keep = np.zeros(len(q), bool)
    for k in range(len(LAB)):
        i = np.nonzero(c == k)[0]; keep[i if k == len(LAB) - 1 or len(i) <= 500 else rng.choice(i, 500, replace=False)] = True
    T = T.filter(keep); t, sd, p, q = (T[x].to_numpy() for x in ("ts", "side", "p", "q")); c = np.searchsorted(CLS, q, side="right") - 1
    S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts"); ts = S["ts"].to_numpy(); bid, ask = S["bid"].to_numpy(), S["ask"].to_numpy()
    k = np.searchsorted(ts, t, side="left") - 1; ok = k >= 0; t, sd, p, q, c, k = t[ok], sd[ok], p[ok], q[ok], c[ok], k[ok]      # the last update before the order
    need = np.unique(ts[k]); Lb = ladders(day, need, K=200); row = np.searchsorted(need, ts[k]); pred = np.full(len(t), np.nan)
    for s, pk, zk in ((1, "ask_px", "ask_sz"), (-1, "bid_px", "bid_sz")):
        m = sd == s
        for Q in np.unique(q[m]):
            j = np.nonzero(m & (q == Q))[0]; pred[j] = walk(Lb[pk][row[j]].astype(float), Lb[zk][row[j]], float(Q))
    mid = (bid[k] + ask[k]) / 2
    return pl.DataFrame({"t": t, "side": sd, "q": q, "cls": [LAB[x] for x in c], "gap_bp": sd * (p - pred) / mid * 1e4, "day": [day] * len(t)})


def with_empty(W, p):
    """Give a price with no message before the window's start an empty level, so that our order is first in line there."""
    c, z = W.lev.get(p, (np.array([], dtype=np.int64), np.array([], dtype=float)))
    if not len(c) or c[0] > W.ts[0]: W.lev[p] = (np.r_[W.ts[0] - 1, c], np.r_[0.0, z])


def h9(day):
    d0 = L21.ms(day); rng = np.random.default_rng(int(day.replace("-", ""))); halves = np.sort(rng.choice(48, 8, replace=False)); rows = []
    for side in (1, -1):
        for hh in halves:
            a0 = d0 + int(hh) * MM.WIN; MM.wait_memory(); W = MM.Window(day, a0, a0 + MM.WIN, side)
            for t in range(a0, a0 + MM.WIN, 60_000):
                ta = t + 50; k = W.at(ta)
                if k < 0: continue
                m = abs(W.mid[k]); p = int(np.floor(m * (1 - 10e-4))); p = p if side == 1 else -int(np.ceil(m * (1 + 10e-4)))    # 10 bp from the mid, a whole tick
                with_empty(W, p)
                for rule, a in (("Q1", None), ("Q2", 1.0)):
                    tf = W.fill(p, ta, min(ta + 600_000, W.end), rule, a)
                    rows.append((side, t, p, rule, tf, W.mid[W.at(tf + 10_000)] if tf else np.nan))
            del W
    return pl.DataFrame(rows, schema=["side", "sent", "price", "rule", "fill", "mid10"], orient="row").with_columns(pl.lit(day).alias("day"))


def h6(day):
    a0, b0 = L21.ms(day, "20:50:00"), L21.ms(day, "22:50:00"); rows = []
    for side in (1, -1):
        MM.wait_memory(); W = MM.Window(day, a0, b0, side)
        for q in ("instant", "1s"):
            MM.chain(W, a0, b0, q, 50, "Q2", 1.0, rows, (q, "Q2 a=1", 50, side))
        del W
    return pl.DataFrame(rows, schema=["quoter", "rule", "L", "side", "sent", "arrival", "price", "end", "filled", "adverse", "mid1", "mid10"], orient="row").with_columns(pl.lit(day).alias("day"))


if __name__ == "__main__":
    job = sys.argv[1]; fn = dict(h7=h7, h9=h9, h6=h6)[job]; OUT = L21.OUT / "s4" / job; OUT.mkdir(parents=True, exist_ok=True)
    days = sys.argv[2:] or (ALL if job == "h6" else OOS)
    for day in days:
        f = OUT / f"{day}.parquet"
        if f.exists() and not sys.argv[2:]: continue
        t0 = time.time(); MM.wait_memory(); D = fn(day); D.write_parquet(f); print(job, day, f"{time.time() - t0:.0f} s", D.height, flush=True)
