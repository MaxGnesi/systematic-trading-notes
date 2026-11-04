"""Lecture 21 §4: quoting once a second against quoting at every book update (results/hypotheses.md, "Quoting once a second"). One order of
0.001 BTC on each side, run through the day as a chain: the order joins at the best price standing when it arrives; at each decision moment
(every whole second, or every book update for the instant quoter) it is kept if the best price on its side is still its price, otherwise a
cancellation is sent and a new order with it, both arriving L later; after a fill the next order is sent at the next decision moment. Fills
under Q0, Q1 and Q2 (a = 1 and a = infinity), each rule its own chain, by the rules of l21.Bid. The ask side is the bid side with prices negated.
The day is read in half-hour windows (with the 5 minutes before and 10 after), the chain carried from one window to the next.
Output: L21_OUT/mm/<day>.parquet, one row per order: quoter, rule, L, side, sent, arrival, price, end (fill or cancellation), filled, adverse
(the best price on our side moved through ours at the first book update after the fill), mid 1 s and 10 s after the fill.
Usage: python l21_mm.py [DAY ...] (the eight days of results/hypotheses.md if none); python l21_mm.py --tests: the instant quoter (the test resting
order) at L = 50 ms under Q0, Q1 and Q2 with a = 1, the other out-of-sample days, for H1 and H2."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
try:
    import psutil
except ImportError:
    psutil = None
OUT = L21.OUT / "mm"; OUT.mkdir(parents=True, exist_ok=True)
LATS = (10, 50, 100); RULES = (("Q0", None), ("Q1", None), ("Q2", 1.0), ("Q2", np.inf)); WIN = 1_800_000; PRE, POST = 300_000, 600_000
DAYS = ("2025-10-11", "2025-10-12", "2025-10-13", "2025-10-14", "2025-10-15", "2025-10-22", "2025-10-28", "2025-11-01")   # out of sample


def wait_memory(gb=0.4):
    while psutil and psutil.virtual_memory().available / 2**30 < gb: time.sleep(5)


class Window:
    """One side of one window, as a bid: book levels by price, the sells (trades at or below a price) and the best price after every update."""

    def __init__(self, day, a, b, side):
        B, T, S = L21.window(day, a - PRE, b + POST, side=1 if side == 1 else -1)
        sg = 1 if side == 1 else -1                                               # the ask side: prices negated, buys become sells
        B = B.with_columns(pl.col("tick") * sg).sort("cts", maintain_order=True)
        self.lev = {int(k[0]): (g["cts"].to_numpy(), g["size"].to_numpy()) for k, g in B.group_by("tick")}
        T = T.filter(pl.col("side") == -sg).with_columns(pl.col("tick") * sg).sort("ts")
        self.tt, self.tk, self.tz = (T[c].to_numpy() for c in ("ts", "tick", "size"))
        S = S.sort("ts"); self.ts = S["ts"].to_numpy()
        self.best = (S["bid"] if side == 1 else -S["ask"]).to_numpy(); self.mid = sg * (S["bid"] + S["ask"]).to_numpy() / 2
        ch = np.r_[np.nonzero(np.diff(self.best))[0] + 1, len(self.best)]           # index of the next change of the best price
        self.nxt = ch[np.searchsorted(ch, np.arange(len(self.best)), side="right")]
        self.end = b + POST

    def at(self, x):
        return np.searchsorted(self.ts, x, side="right") - 1

    def fill(self, p, ta, tend, rule, a):
        """Fill time of a bid at p from ta to tend under the rule, or None (l21.Bid's rules)."""
        c, z = self.lev.get(p, (None, None))
        if c is None: return None
        k0 = np.searchsorted(c, ta, side="right") - 1
        if k0 < 0: return None
        i, j = np.searchsorted(self.tt, ta, side="right"), np.searchsorted(self.tt, tend, side="right")
        tr = i + np.nonzero(self.tk[i:j] <= p)[0]
        if rule == "Q0": return int(self.tt[tr[0]]) if len(tr) else None
        if rule == "Q1":
            th = tr[self.tk[tr] < p]; return int(self.tt[th[0]]) if len(th) else None
        h = np.searchsorted(self.tt, c[k0], side="right")
        pre = float(self.tz[h:i][self.tk[h:i] == p].sum())
        V, qlev, tsum = max(float(z[k0]) - pre, 0.0), float(z[k0]), pre
        u1 = k0 + 1 + np.searchsorted(c[k0 + 1:], tend, side="right")
        ev = sorted([(self.tt[q], 0, q) for q in tr] + [(c[u], 1, u) for u in range(k0 + 1, u1)])
        for t, kind, q in ev:
            if kind == 0:
                if self.tk[q] < p or self.tz[q] > V: return int(t)
                V -= self.tz[q]; tsum += self.tz[q]
            else:
                new = float(z[q]); d = qlev - tsum - new
                if d > 0:
                    x = min(V / max(qlev - tsum, 1e-12), 1.0)
                    behind = (1 - x ** a) * d if a != np.inf else d
                    behind = min(behind if x < 1 else 0.0, qlev - tsum - V)
                    V = max(V - (d - behind), 0.0)
                qlev, tsum = new, 0.0
        return None

    def cancel_moment(self, p, ta, quoter):
        """The first decision moment after ta at which the best price is no longer p."""
        k = self.at(ta)
        while True:
            k = self.nxt[k] if self.best[k] == p else k
            if k >= len(self.ts): return None
            r = int(self.ts[k]) if quoter == "instant" else (int(self.ts[k]) // 1000 + 1) * 1000 if self.ts[k] % 1000 else int(self.ts[k])
            k = self.at(r)
            if self.best[k] != p: return r


def chain(W, r, b, quoter, L, rule, a, rows, meta):
    """Run one quoter's chain from decision moment r while decisions fall before b; returns the next decision moment."""
    while r < b:
        ta = r + L; k = W.at(ta)
        if ta > W.end: return r
        if k < 0: r = int(W.ts[0]); continue                                      # before the first update of the window: wait for it
        p = int(W.best[k]); rc = W.cancel_moment(p, ta, quoter)
        tend = W.end if rc is None else rc + L
        tf = W.fill(p, ta, tend, rule, a)
        if tf is not None:
            kf = W.at(tf); adv = W.best[min(kf + 1, len(W.best) - 1)] < p
            m1, m10 = W.mid[W.at(tf + 1000)], W.mid[W.at(tf + 10_000)]
            rows.append((*meta, r, ta, p, tf, True, bool(adv), m1, m10))
            r = tf if quoter == "instant" else (tf // 1000 + 1) * 1000
        else:
            rows.append((*meta, r, ta, p, tend, False, False, np.nan, np.nan))
            if rc is None: return W.end
            r = rc
    return r


def day_mm(day, quoters=("1s", "instant"), lats=LATS, rules=RULES):
    d0 = L21.ms(day); rows = []
    for side in (1, -1):
        nxt = {}
        for a0 in range(d0, d0 + 86_400_000, WIN):
            wait_memory(); W = Window(day, a0, a0 + WIN, side)
            for quoter in quoters:
                for L in lats:
                    for rule, a in rules:
                        key = (quoter, L, rule, a)
                        nxt[key] = chain(W, nxt.get(key, a0), a0 + WIN, quoter, L, rule, a,
                                         rows, (quoter, rule if a is None else f"Q2 a={a:g}", L, side))
            del W
    D = pl.DataFrame(rows, schema=["quoter", "rule", "L", "side", "sent", "arrival", "price", "end", "filled", "adverse", "mid1", "mid10"], orient="row")
    return D.with_columns(pl.lit(day).alias("day"))


if __name__ == "__main__":
    if "--tests" in sys.argv:
        for day in (p.stem for p in sorted(L21.STATE.glob("*.parquet")) if p.stem >= "2025-10-11" and p.stem not in DAYS):
            f = OUT / f"{day}.parquet"
            if f.exists(): continue
            t0 = time.time(); D = day_mm(day, ("instant",), (50,), RULES[:3]); D.write_parquet(f)
            print(day, f"{time.time() - t0:.0f} s", D.group_by("rule").agg(pl.col("filled").sum()).sort("rule").rows(), flush=True)
        sys.exit()
    days = sys.argv[1:] or DAYS
    for day in days:
        f = OUT / f"{day}.parquet"
        if f.exists() and not sys.argv[1:]: continue
        t0 = time.time(); D = day_mm(day); D.write_parquet(f)
        print(day, f"{time.time() - t0:.0f} s", D.group_by("quoter", "rule").agg(pl.col("filled").sum()).sort("quoter", "rule").rows(), flush=True)
