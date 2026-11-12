"""Lecture 24: a two-sided quoting engine on Lecture 21's replay. A design says, for the current state (its open lots), which orders it wants and at
what price at every book update (a price path, NaN for none); the engine posts them, decides only on data published up to the decision, and lets each
order arrive L later. Fills of resting orders use Lecture 21's rules (queue rule Q2, cancellations split by a); a price with no message yet is an empty level,
our order first in line. A maker order that would trade on arrival is rejected (post-only); a closing order that would trade on arrival is filled there
as a taker. A cancelled order stays live until the cancellation arrives, L after the decision, and can still be filled. The day runs in half-hour windows;
at each boundary resting orders are sent again (they lose their place in line), open lots are kept."""
import io, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l21_mm as MM
L21 = L.L21; WIN = 1_800_000; INF = np.iinfo(np.int64).max


class Win(MM.Window):
    def __init__(self, day, a, b, side):
        """As Lecture 21's window, with the levels split by sorting instead of a group-by (the same arrays, faster)."""
        B, T, S = L21.window(day, a - MM.PRE, b + MM.POST, side=side); sg = side
        tk, c, z = B["tick"].to_numpy() * sg, B["cts"].to_numpy(), B["size"].to_numpy(); o = np.lexsort((c, tk))   # stable: by price, then time
        tk, c, z = tk[o], c[o], z[o]; u, i0 = np.unique(tk, return_index=True); e = np.r_[i0, len(tk)]
        self.lev = {int(u[j]): (c[e[j]:e[j + 1]], z[e[j]:e[j + 1]]) for j in range(len(u))}
        T = T.filter(pl.col("side") == -sg).with_columns(pl.col("tick") * sg).sort("ts")
        self.tt, self.tk, self.tz = (T[x].to_numpy() for x in ("ts", "tick", "size"))
        self.end = b + MM.POST

    def fill(self, p, ta, tend, rule="Q2", a=1.0):
        c, _ = self.lev.get(p, (None, None))
        if c is None or np.searchsorted(c, ta, side="right") - 1 < 0:                          # no message at this price yet: empty, we are first in line
            i, j = np.searchsorted(self.tt, ta, side="right"), np.searchsorted(self.tt, tend, side="right")
            tr = i + np.nonzero(self.tk[i:j] <= p if rule != "Q1" else self.tk[i:j] < p)[0]
            return int(self.tt[tr[0]]) if len(tr) else None
        return super().fill(p, ta, tend, rule, a)


class Arrays:
    """The day's book state after every update (Lecture 19), in ticks, with the microprice, the volatility of the last 60 s and the gap to Binance."""

    def __init__(self, day):
        S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask", "q_bid", "q_ask"]).sort("ts")
        self.ts = S["ts"].to_numpy(); self.bid = S["bid"].to_numpy().astype(float); self.ask = S["ask"].to_numpy().astype(float)
        qb, qa = S["q_bid"].to_numpy(), S["q_ask"].to_numpy(); self.mid = (self.bid + self.ask) / 2
        w = qb + qa; self.micro = np.where(w > 0, (self.bid * qa + self.ask * qb) / np.where(w > 0, w, 1), self.mid)
        g = np.arange((self.ts[0] // 1000 + 1) * 1000, self.ts[-1], 1000); m = self.mid[np.searchsorted(self.ts, g, side="right") - 1]
        d = np.r_[0.0, np.diff(m)]; c1, c2 = np.cumsum(d), np.cumsum(d * d); n = 60
        s1 = c1 - np.r_[np.zeros(n), c1[:-n]]; s2 = c2 - np.r_[np.zeros(n), c2[:-n]]; sd = np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0))
        j = np.searchsorted(g, self.ts, side="right") - 1; self.sig = np.where(j >= 0, sd[np.maximum(j, 0)], 0.0)
        with zipfile.ZipFile(L.BN_RAW / f"{L21.SYM}-aggTrades-{day}.zip") as z:
            B = pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), columns=["price", "transact_time"]).sort("transact_time")
        bt, bp = B["transact_time"].to_numpy(), B["price"].to_numpy(); del B
        j = np.searchsorted(bt, self.ts, side="right") - 1; m = self.mid * L21.TICK
        gap = np.where(j >= 0, (bp[np.maximum(j, 0)] - m) / m * 1e4, 0.0)
        gs = gap[np.searchsorted(self.ts, g, side="right") - 1]; c = np.cumsum(gs); avg = (c - np.r_[np.zeros(60), c[:-60]]) / np.minimum(np.arange(1, len(c) + 1), 60)
        jg = np.searchsorted(g, self.ts, side="left") - 1                                         # the average over the whole seconds before the update
        self.gap = gap - np.where(jg >= 0, avg[np.maximum(jg, 0)], gap)                           # the gap net of the slow difference between the two markets
        self.bp = m[len(m) // 2] / 1e4 / L21.TICK                                                 # ticks per bp, at the day's middle price

    def at(self, t):
        return max(int(np.searchsorted(self.ts, t, side="right")) - 1, 0)


class Order:
    __slots__ = ("key", "s", "p", "ta", "tend", "role", "lot", "cache")

    def __init__(self, key, s, p, ta, role, lot):
        self.key, self.s, self.p, self.ta, self.tend, self.role, self.lot, self.cache = key, s, p, ta, None, role, lot, (None, None)


class State:
    def __init__(self):
        self.lots = []; self.nid = 0; self.last = {1: -1, -1: -1}                                 # open lots: dict(id, s, p, t); the last fill time on each side

    @property
    def pos(self):
        return sum(l["s"] for l in self.lots)

    def add(self, s, p, t, role, lot):
        """A fill on side s: closes lot `lot` (a closing order), else the oldest opposite lot (netting), else opens a lot. A closing order filled after its
        lot was closed (a stop, then the cancelled maker order filled within the latency) is an ordinary fill, so the lots always add up to the fills."""
        self.last[s] = t
        if role == "close" and any(l["id"] == lot for l in self.lots):
            self.lots = [l for l in self.lots if l["id"] != lot]; return
        opp = [l for l in self.lots if l["s"] == -s]
        if opp: self.lots.remove(opp[0]); return
        self.nid += 1; self.lots.append(dict(id=self.nid, s=s, p=p, t=t))


def next_change(fn, k, p, n):
    """The first index after k at which the path fn differs from p (NaN counts as different; for p = NaN, the first index with a price), or n."""
    c = getattr(fn, "const", None)
    if c is not None: return n if c == p else min(k + 1, n)                                    # a fixed price never changes
    a, step = k + 1, 256
    while a < n:
        b = min(a + step, n); x = fn(a, b); d = np.nonzero(~np.isnan(x) if np.isnan(p) else np.isnan(x) | (x != p))[0]
        if len(d): return a + int(d[0])
        a, step = b, min(step * 4, 1 << 20)
    return n


def run_window(design, st, F, W, A, w0, b, rule, a, lat):
    """One design through one half-hour window; st (its open lots) and F (its fills) carry over to the next window."""
    n = len(A.ts); live, dying = {}, []; r = w0
    while r < b:
        k = A.at(r); want = design.slots(st, A, k)
        for key, o in list(live.items()):                                                     # cancel what is no longer wanted at its price
            if key not in want or want[key][1](k, k + 1)[0] != o.p:
                o.tend = r + lat; dying.append(o); del live[key]
        idle = []                                                                             # wanted sides with no order: when to look again
        for key, (s, fn, role, lot) in want.items():                                          # post what is wanted and not live
            if key in live: continue
            p = fn(k, k + 1)[0]
            if np.isnan(p): idle.append(next_change(fn, k, np.nan, n)); continue
            ta = r + lat; ka = A.at(ta); cross = (s == 1 and p >= A.ask[ka]) or (s == -1 and p <= A.bid[ka])
            if cross and role == "close":                                                     # a closing order that trades on arrival: taker
                px = A.ask[ka] if s == 1 else A.bid[ka]; F.append((ta, s, px, role, True)); st.add(s, px, ta, role, lot); want = None; break
            if cross: idle.append(min(ka + 1, n)); continue                                   # post-only: rejected, try at the next update
            live[key] = Order(key, s, p, ta, role, lot)
        if want is None: r = r + lat; continue
        ev = []
        for key, o in live.items():
            fn = want[key][1]; kc = next_change(fn, k, o.p, n); rc = int(A.ts[kc]) if kc < n else INF; tend = min(rc + lat, b)
            if o.cache[0] != tend: o.cache = (tend, W[o.s].fill(int(o.s * o.p), o.ta, tend, rule, a))
            tf = o.cache[1]; ev.append((tf, 0, o) if tf is not None else (rc, 1, o))
        for o in dying:
            tf = W[o.s].fill(int(o.s * o.p), o.ta, o.tend, rule, a)
            if tf is not None: ev.append((tf, 0, o))
        dying = [o for o in dying if o.tend > r]
        ev += [(int(A.ts[j]), 1, None) for j in idle if j < n]
        stop = design.stop(st, A, k, r)
        if stop: ev.append((stop[0], 2, stop[1]))
        if not ev: break
        t, kind, x = min(ev, key=lambda e: (e[0], e[1]))
        if t >= b: break
        if kind == 0:
            F.append((t, x.s, x.p, x.role, False)); st.add(x.s, x.p, t, x.role, x.lot)
            if x.key in live and live[x.key] is x: del live[x.key]
            if x in dying: dying.remove(x)
            for o in list(live.values()) + dying:                                             # the other order of a closed lot goes
                if x.role == "close" and o.lot == x.lot and o is not x: live.pop(o.key, None)
            r = max(t, r + 1)
        elif kind == 1:
            r = max(t, r + 1)
        else:                                                                                 # a stop: close the lot as a taker
            lot = x; ta = t + lat; ka = A.at(ta); s = -lot["s"]
            for key in [kk for kk, o in live.items() if o.lot == lot["id"]]: del live[key]
            px = A.ask[ka] if s == 1 else A.bid[ka]; F.append((ta, s, px, "stop", True)); st.add(s, px, ta, "close", lot["id"]); r = ta


def frame(F):
    return pl.DataFrame(F, schema=["t", "s", "p", "role", "taker"], orient="row") if F else pl.DataFrame(schema={"t": pl.Int64, "s": pl.Int64, "p": pl.Float64, "role": pl.Utf8, "taker": pl.Boolean})


def run_days(day, designs, rule="Q2", a=L.A, lat=L.LAT, A=None, windows=None):
    """Several designs through one day, each book window built once. windows: the half-hour windows to run (0 to 47), for samples and tests; a design's
    lots carry over between consecutive windows only, and it starts flat after a gap. Returns {name: fills} and the arrays."""
    A = A or Arrays(day); d0 = L21.ms(day); ws = list(range(48)) if windows is None else list(windows)
    st = {d.name: State() for d in designs}; F = {d.name: [] for d in designs}; prev = None
    for w in ws:
        if prev is not None and w != prev + 1: st = {d.name: State() for d in designs}
        w0 = d0 + w * WIN; W = {1: Win(day, w0, w0 + WIN, 1), -1: Win(day, w0, w0 + WIN, -1)}
        for d in designs: run_window(d, st[d.name], F[d.name], W, A, w0, w0 + WIN, rule, a, lat)
        del W; prev = w
    return {k: frame(v) for k, v in F.items()}, A


def run_day(day, design, rule="Q2", a=L.A, lat=L.LAT, A=None, hours=None):
    """One design (hours: (first, last) half-hour windows)."""
    R, A = run_days(day, [design], rule, a, lat, A, None if hours is None else range(*hours)); return R[design.name], A


def blocks(day, windows=None):
    """The runs of consecutive half-hour windows, as (start, end) in ms; the whole day when windows is None."""
    d0 = L21.ms(day); ws = list(range(48)) if windows is None else sorted(windows); out = []
    for w in ws:
        if out and out[-1][1] == d0 + w * WIN: out[-1][1] += WIN
        else: out.append([d0 + w * WIN, d0 + (w + 1) * WIN])
    return [tuple(b) for b in out]


def score(D, A, size=L.SIZE, B=None):
    """The day's measures from its fills: markouts, the result before the fee in bp of the value traded (the break-even maker fee), the part from the position.
    B: the blocks of windows run (blocks()); the engine starts each block flat, so the position open at a block's end is valued at the mid there."""
    if D.height == 0: return dict(fills=0)
    t, s, p = D["t"].to_numpy(), D["s"].to_numpy(), D["p"].to_numpy(); mk = {}
    for h in (1_000, 10_000, 60_000): mk[h] = s * (A.mid[np.searchsorted(A.ts, t + h, side="right") - 1] - p)
    B = B or [(int(t[0]), int(A.ts[-1]) + 1)]; total = 0.0; maxp = 0; endp = 0
    for b0, b1 in B:
        m = (t >= b0) & (t < b1)
        if not m.any(): continue
        pos = np.cumsum(s[m]); end = A.mid[max(int(np.searchsorted(A.ts, b1, side="left")) - 1, 0)]
        total += -np.sum(s[m] * p[m]) + pos[-1] * end; maxp = max(maxp, int(np.abs(pos).max())); endp = int(pos[-1])
    value = np.sum(p); spread10 = mk[10_000].sum()
    bp = lambda x: float(x / value * 1e4)
    return dict(fills=int(D.height), taker=int(D["taker"].sum()), mk1=float(mk[1_000].mean() / A.bp), mk10=float(mk[10_000].mean() / A.bp), mk60=float(mk[60_000].mean() / A.bp),
                result_bp=bp(total), position_bp=bp(total - spread10), value_usdt=float(value * L21.TICK * size), result_usdt=float(total * L21.TICK * size),
                max_pos=maxp, end_pos=endp)
