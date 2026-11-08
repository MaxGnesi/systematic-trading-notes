"""Lecture 22: the hybrid replay. The recorded Bybit book is the background; our market orders change it in layers, each estimated in sample (Section 3).
A, depletion: what our order took is gone from the levels near the best, at the same distance from the best. B, refill: it comes back along the measured curve (median share of the
depth an order met that stands within the same number of levels of the new best). C, impact: the mid is the recorded mid shifted by the measured response R(tau) to our size, held at its
300 s value afterwards and never reset to the record; the whole book moves with it. No double counting: R(tau) already contains everything the market did after real orders, so the mid
comes from C alone; the levels A and B empty only make our next walk dearer. Layer D (triggered trading) changes who trades against our resting orders and does not move the price; E
waits on H8. Prices in ticks of 0.1 USDT, sizes in BTC, times in ms (engine time)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L

VIEWER = L.ROOT / "viewer_cache" / L.SYM


def fit_response(path=L.RESULTS / "s3_response.json"):
    """R(tau) = c(tau) S^delta(tau), fitted in sample on the size classes (log of the mean net move on log of the mean size). Returns {tau: (c, delta)} in bp."""
    Q = json.loads(Path(path).read_text(encoding="utf-8"))["curves"]; cls = [k for k in Q if k.startswith("cls|")]
    S = np.array([Q[k]["S_mean"] for k in cls]); out = {}
    for i, tau in enumerate(L.TAUS):
        R = np.array([Q[k]["mean"][i] for k in cls]); ok = R > 0; d, lc = np.polyfit(np.log(S[ok]), np.log(R[ok]), 1); out[tau] = (float(np.exp(lc)), float(d))
    return out


def fit_refill(path=L.RESULTS / "s3_refill.json"):
    """The median share of the depth an order met that stands near the new best, at each probe time after it, by size class (1-5, 5-20, 20 BTC or more): larger orders refill more slowly.
    Returns {lower bound of the class in BTC: (probe times, shares)}; orders below 1 BTC use the 1-5 curve."""
    v = json.loads(Path(path).read_text(encoding="utf-8"))["refill"]
    return {lo: (np.array(v[c]["probe"], float), np.array(v[c]["near_med"], float)) for lo, c in ((0.0, "1-5"), (5.0, "5-20"), (20.0, "20+"))}


class Hybrid:
    """The book of one window, replayed with our orders. Start from the viewer's checkpoint before t_a, apply recorded updates; our market orders walk the book as it stands in the replay."""

    def __init__(self, day, t_a, t_b, layers="ABC", resp=None, refill=None, books=None):
        self.layers = set(layers); self.resp = resp or fit_response(); self.refill = refill if isinstance(refill, dict) else ({0.0: refill} if refill else fit_refill()); self.ours = []   # (time, side, size, depletion by distance)
        if books is not None:                                                         # a hand-made book for the checks: ({bids}, {asks}, updates [(t, 0, side, tick, size)])
            self.book = {1: dict(books[0]), -1: dict(books[1])}; self.u = np.array(books[2] if len(books) > 2 and books[2] else np.zeros((0, 5)), float); self.k = 0; self.t = t_a; return
        at = t_a // 60_000 * 60_000; cp = pl.read_parquet(VIEWER / f"{day}_checkpoints.parquet").filter(pl.col("at") == at)
        self.book = {1: {p: q for s, p, q in cp.select("side", "tick", "size").iter_rows() if s == 1}, -1: {p: q for s, p, q in cp.select("side", "tick", "size").iter_rows() if s == -1}}
        U = pl.scan_parquet(L.BOOK / f"{day}.parquet").filter((pl.col("cts") > at) & (pl.col("cts") <= t_b)).select("cts", "snap", "side", "tick", "size").collect()
        self.u = U.to_numpy(); self.k = 0; self.t = at; self.advance(t_a)

    def advance(self, t):
        """Apply the recorded updates up to time t."""
        u = self.u
        while self.k < len(u) and u[self.k, 0] <= t:
            cts, snap, s, p, q = (int(x) if i < 4 else float(x) for i, x in enumerate(u[self.k]))
            if snap == 1 and (self.k == 0 or u[self.k - 1, 0] != cts or u[self.k - 1, 1] != 1): self.book[1].clear(); self.book[-1].clear()
            b = self.book[int(s)]
            if q == 0: b.pop(int(p), None)
            else: b[int(p)] = float(q)
            self.k += 1
        self.t = t

    def record_mid(self):
        return (max(self.book[1]) + min(self.book[-1])) / 2

    def shift(self, t):
        """Layer C: the mid's shift in ticks at time t, the sum over our orders of R(tau) for their size, held at 300 s."""
        if "C" not in self.layers: return 0.0
        m = self.record_mid(); total = 0.0
        for t0, side, S, _ in self.ours:
            tau = t - t0
            if tau <= 0: continue
            taus = np.array(L.TAUS, float); c = np.array([self.resp[x][0] for x in L.TAUS]); d = np.array([self.resp[x][1] for x in L.TAUS])
            R = c * S ** d; r = float(np.interp(np.log(max(tau, taus[0])), np.log(taus), R))      # bp, flat before 0.1 s and after 300 s
            total += side * r * m / 1e4
        return total

    def missing(self, t, book_side, k):
        """Layers A and B: size still missing at distance k from the best on `book_side` (1 bids, -1 asks) at time t, from our earlier orders that took from that side."""
        if "A" not in self.layers: return 0.0
        out = 0.0
        for t0, s, S, dep in self.ours:
            if -s != book_side or t <= t0 or k >= len(dep): continue
            rt, rs = self.refill[max(lo for lo in self.refill if lo <= S)]
            back = float(np.interp(t - t0, rt, rs, left=0.0, right=rs[-1])) if "B" in self.layers else 0.0
            out += dep[k] * (1 - back)
        return out

    def levels(self, t, book_side):
        """The levels on `book_side` (-1 asks, which a buy takes; 1 bids) at time t: recorded levels moved by the shift, less what is still missing, best first."""
        self.advance(t); sh = int(round(self.shift(t))); b = self.book[book_side]
        prices = sorted(b) if book_side == -1 else sorted(b, reverse=True)
        return [(p + sh, max(b[p] - self.missing(t, book_side, k), 0.0)) for k, p in enumerate(prices)]

    def mid(self, t):
        self.advance(t); return self.record_mid() + self.shift(t)

    def market_order(self, t, side, S):
        """Walk the levels as they stand at t; record the depletion by distance from the best. side 1 buys. Returns the fills [(price, size)] and the size left."""
        lv = self.levels(t, -side); fills = []; left = S; dep = []
        for p, q in lv:
            if left <= 1e-12: break
            z = min(q, left); dep.append(z); left -= z                                   # depletion is kept by distance from the best, empty levels included
            if z > 1e-12: fills.append((p, z))
        self.ours.append((t, side, S - left, dep))
        return fills, left


def cost_bp(fills, side, mid0):
    z = sum(q for _, q in fills); return side * (sum(p * q for p, q in fills) / z - mid0) / mid0 * 1e4 if z else np.nan
