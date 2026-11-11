"""Lecture 24's designs (results/hypotheses.md). Each returns, for the open lots, the orders it wants: key -> (side, price path, role, lot); prices in ticks,
NaN for no order. stop() gives the next taker exit, if the design has one."""
import numpy as np
from l24 import LIMIT


class Quoter:
    """The baseline (theta=None, k=0), the Binance guard (theta in bp) and quoting k ticks behind the best (H1, H3)."""

    def __init__(self, theta=None, k=0):
        self.theta, self.k = theta, k; self.name = "baseline" if theta is None and k == 0 else (f"guard_{theta:g}" if theta is not None else f"behind_{k}")

    def slots(self, st, A, i):
        q = st.pos; out = {}
        def side(s):
            def fn(a, b):
                p = A.bid[a:b] - self.k if s == 1 else A.ask[a:b] + self.k
                if self.theta is not None: p = np.where(s * A.gap[a:b] <= -self.theta, np.nan, p)
                return p
            return fn
        if q < LIMIT: out[("e", 1)] = (1, side(1), "entry", None)
        if q > -LIMIT: out[("e", -1)] = (-1, side(-1), "entry", None)
        return out

    def stop(self, st, A, i, r):
        return None


class AS:
    """H2: quotes at r +- h, r = microprice - kappa x position (ticks per lot), h = max(half a tick, c x sigma); rounded away from r, never crossing."""

    def __init__(self, kappa, c):
        self.kappa, self.c = kappa, c; self.name = f"as_{kappa:g}_{c:g}"

    def slots(self, st, A, i):
        q = st.pos; out = {}
        def side(s):
            def fn(a, b):
                r = A.micro[a:b] - self.kappa * q; h = np.maximum(0.5, self.c * A.sig[a:b])
                return np.minimum(np.floor(r - h), A.ask[a:b] - 1) if s == 1 else np.maximum(np.ceil(r + h), A.bid[a:b] + 1)
            return fn
        if q < LIMIT: out[("e", 1)] = (1, side(1), "entry", None)
        if q > -LIMIT: out[("e", -1)] = (-1, side(-1), "entry", None)
        return out

    def stop(self, st, A, i, r):
        return None


class PingPong:
    """H4. entry: 0 (at the best) or 1 (a tick behind); exit: 'a' (at the best, re-posted), ('b', k) a target k ticks from entry, ('c', k, m, T) a target with
    a stop m ticks against or after T ms; switch: ('n', n) fills on a side, or ('x', x) bp of excursion against the side's average entry."""

    def __init__(self, entry, exit, switch):
        self.entry, self.exit, self.switch = entry, exit, switch
        ex = exit if isinstance(exit, str) else "".join(str(v) for v in exit[:2])
        self.name = f"pp_e{entry}_{ex}_{switch[0]}{switch[1]:g}"
        if not isinstance(exit, str) and exit[0] == "c" and (exit[2] != exit[1] or exit[3] != 60_000):    # stops other than H4's: stop in ticks, time limit in s
            self.name += f"_s{exit[2]}_t{'inf' if exit[3] >= 10**12 else exit[3] // 1000}"

    def slots(self, st, A, i):
        out = {}
        for s in (1, -1):
            mine = [l for l in st.lots if l["s"] == s]
            if any(l["s"] == -s for l in st.lots) or abs(st.pos) >= LIMIT: continue          # the other side has open lots: only closing orders there
            if self.switch[0] == "n" and len(mine) >= self.switch[1]: continue
            avg = np.mean([l["p"] for l in mine]) if mine else None; xt = self.switch[1] * A.bp if self.switch[0] == "x" else None
            def fn(a, b, s=s, avg=avg, xt=xt):
                p = A.bid[a:b] - self.entry if s == 1 else A.ask[a:b] + self.entry
                if avg is not None and xt is not None: p = np.where(s * (A.mid[a:b] - avg) <= -xt, np.nan, p)
                return p
            out[("e", s)] = (s, fn, "entry", None)
        for l in st.lots:                                                                          # one closing order per lot, on the other side
            s = -l["s"]
            if self.exit == "a":
                fn = (lambda a, b: A.bid[a:b]) if s == 1 else (lambda a, b: A.ask[a:b])
            else:
                tgt = float(l["p"] + l["s"] * self.exit[1]); fn = lambda a, b, tgt=tgt: np.full(b - a, tgt); fn.const = tgt   # a fixed price
            out[("c", l["id"])] = (s, fn, "close", l["id"])
        return out

    def stop(self, st, A, i, r):
        if self.exit == "a" or self.exit[0] != "c": return None
        best = None
        for l in st.lots:
            t = l["t"] + self.exit[3]; ie = int(np.searchsorted(A.ts, t, side="right"))              # time stop; a price stop before it
            j = np.nonzero(l["s"] * (A.mid[i:ie] - l["p"]) <= -self.exit[2])[0]
            if len(j): t = min(t, int(A.ts[i + j[0]]))
            t = max(t, r + 1)
            if best is None or t < best[0]: best = (t, l)
        return best


def grid_pingpong(bp_ticks=110):
    """The 56 variants of H4 (110 ticks is about 1 bp at 110,000 USDT)."""
    out = []
    for e in (0, 1):
        for x in ("a", ("b", 1), ("b", bp_ticks), ("c", bp_ticks, bp_ticks, 60_000)):
            for sw in (("n", 1), ("n", 2), ("n", 3), ("n", 5), ("x", 2), ("x", 5), ("x", 10)):
                out.append(PingPong(e, x, sw))
    return out


def grid_stops(bp_ticks=110):
    """The stop of ping-pong exit (c) widened (hypotheses.md, 2026-11-11): target 1 bp, stop 1 to 10 bp against, time limit 60 s, 300 s or none;
    entry at the best, switch-off after 2 fills on a side. The 1 bp / 60 s variant is H4's chosen one, run before."""
    return [PingPong(0, ("c", bp_ticks, m * bp_ticks, T), ("n", 2)) for m in (1, 2, 3, 5, 10) for T in (60_000, 300_000, 10**12)
            if (m, T) != (1, 60_000)]


def grid_as():
    return [AS(k, c) for k in (0, 0.5, 1, 2, 5) for c in (0, 0.5, 1, 2)]


class Kill:
    """A design with the kill switch of results/hypotheses.md (10 October): no entry quotes for 30 s after the mid has moved x bp or more within 1 s;
    closing orders keep working. Uses only moves known at the decision."""

    def __init__(self, inner, x=10, ms=1_000, off=30_000):
        self.inner, self.x, self.ms, self.off = inner, x, ms, off; self.mask = None
        self.name = inner.name + "_kill" + ("" if (x, off) == (10, 30_000) else f"_{x:g}_{off // 1000}")

    def killed(self, A):
        if self.mask is None or self.mask[0] is not A:
            j = np.searchsorted(A.ts, A.ts - self.ms, side="right") - 1; j = np.maximum(j, 0)
            trig = np.abs(A.mid - A.mid[j]) >= self.x * A.bp; tt = A.ts[trig]
            k = np.searchsorted(tt, A.ts, side="right") - 1
            self.mask = (A, (k >= 0) & (A.ts - tt[np.maximum(k, 0)] < self.off))
        return self.mask[1]

    def slots(self, st, A, i):
        out = self.inner.slots(st, A, i); m = self.killed(A)
        for key, (s, fn, role, lot) in list(out.items()):
            if role == "entry": out[key] = (s, lambda a, b, fn=fn: np.where(m[a:b], np.nan, fn(a, b)), role, lot)
        return out

    def stop(self, st, A, i, r):
        return self.inner.stop(st, A, i, r)

class Stop:
    """A design with a stop on every open lot (hypotheses.md, 2026-11-11): the lot is closed as a taker once the mid is `width` against its entry, on a touch
    (hold=0) or only after the mid has stayed beyond the level for `hold` ms. width: m bp (fixed) or k times the 1-minute volatility of the hour before the
    entry (scaled). No time limit. Uses only prices known at the decision."""

    def __init__(self, inner, m=None, k=None, hold=0):
        self.inner, self.m, self.k, self.hold = inner, m, k, hold; self.cache = {}; self.vol = None
        self.name = inner.name + (f"_stop{m:g}" if m is not None else f"_stopk{k:g}") + (f"_h{hold // 1000}" if hold else "")

    def noise(self, A):
        """1-minute volatility over the past hour, in ticks, at every update: from the mid once a second."""
        if self.vol is None or self.vol[0] is not A:
            g = np.arange((A.ts[0] // 1000 + 1) * 1000, A.ts[-1], 1000); m = A.mid[np.searchsorted(A.ts, g, side="right") - 1]
            d2 = np.r_[np.zeros(60), (m[60:] - m[:-60]) ** 2]; c = np.cumsum(d2); n = 3600
            v = np.sqrt((c - np.r_[np.zeros(n), c[:-n]]) / np.minimum(np.arange(1, len(c) + 1), n))
            j = np.searchsorted(g, A.ts, side="right") - 1; self.vol = (A, np.where(j >= 0, v[np.maximum(j, 0)], 0.0))
        return self.vol[1]

    def trigger(self, A, l):
        """The first time the lot's stop fires, from its entry on (computed once per lot)."""
        key = (id(A), l["id"], l["t"], l["p"])
        if key in self.cache: return self.cache[key]
        i0 = A.at(l["t"]); w = self.m * A.bp if self.m is not None else self.k * self.noise(A)[i0]
        n = len(A.ts); a, step, last_ok = i0, 4096, l["t"]; out = None
        while a < n and out is None:
            b = min(a + step, n); c = l["s"] * (A.mid[a:b] - l["p"]) <= -w; ts = A.ts[a:b]
            okt = np.where(~c, ts, -1); lo = np.maximum.accumulate(np.r_[last_ok, okt])[1:]      # time of the last update not beyond the level
            hit = np.nonzero(c & (ts - lo >= self.hold))[0]
            if len(hit): out = int(ts[hit[0]])
            else: last_ok = int(lo[-1]); a, step = b, min(step * 4, 1 << 20)
        self.cache[key] = out; return out

    def slots(self, st, A, i):
        return self.inner.slots(st, A, i)

    def stop(self, st, A, i, r):
        best = self.inner.stop(st, A, i, r)
        for l in st.lots:
            t = self.trigger(A, l)
            if t is None: continue
            t = max(t, r + 1)
            if best is None or t < best[0]: best = (t, l)
        return best


def grid_stop_all():
    """The stop on three designs: fixed 5, 10, 20 bp or 2, 3 times the hour's 1-minute volatility; on a touch or held 5 s."""
    inner = [Quoter, lambda: AS(5, 2), lambda: PingPong(0, "a", ("n", 2))]
    return [Stop(f(), m=m, k=k, hold=h) for f in inner for (m, k) in ((5, None), (10, None), (20, None), (None, 2), (None, 3)) for h in (0, 5_000)]
