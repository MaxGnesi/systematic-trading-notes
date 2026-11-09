"""Lecture 22 §2: the teaching simulation, a small market on invented data. Nothing about the real market is concluded from it.
The book: limit orders by price, in time order at each price; a market order takes the best price first, the oldest order first. Prices in whole ticks,
sizes in BTC, time in ms. Every order carries its owner, which the public feed does not show. The feed publishes what Bybit publishes: the book every 100 ms
(size at each price, no owners) and the trades (time, price, size, side, no owners).
Players are objects with a next wake-up time and a method act(market, t); the market runs whichever wakes first. Added one at a time; each step has its chart script."""
import heapq
from collections import deque
import numpy as np, polars as pl


class Book:
    """One side each of bids and asks: price -> queue of [order id, owner, size]; side +1 is a bid, -1 an ask."""

    def __init__(self):
        self.lev = {1: {}, -1: {}}; self.where = {}; self.nid = 0

    def best(self, side):
        lv = self.lev[side]
        return (max(lv) if side == 1 else min(lv)) if lv else None

    def add(self, side, price, size, owner):
        """A resting order at the back of the line at its price; it must not cross the other side. Returns its id."""
        o = self.best(-side)
        assert o is None or (price < o if side == 1 else price > o), "a limit order that crosses must be sent as a market order"
        self.nid += 1; self.lev[side].setdefault(price, deque()).append([self.nid, owner, size]); self.where[self.nid] = (side, price)
        return self.nid

    def cancel(self, oid):
        """Remove a resting order if it is still there; returns the size removed."""
        if oid not in self.where: return 0.0
        side, price = self.where.pop(oid); q = self.lev[side][price]
        for i, o in enumerate(q):
            if o[0] == oid:
                del q[i]
                if not q: del self.lev[side][price]
                return o[2]
        raise AssertionError("order listed but not in its line")

    def take(self, side, size):
        """A market order: side +1 buys from the asks. Returns the fills [(price, size, resting owner, resting id)] and the size left unfilled, if the book ran out."""
        fills = []; lv = self.lev[-side]
        while size > 1e-12 and lv:
            p = min(lv) if side == 1 else max(lv); q = lv[p]
            while size > 1e-12 and q:
                o = q[0]; z = min(size, o[2]); fills.append((p, z, o[1], o[0])); size -= z; o[2] -= z
                if o[2] <= 1e-12: q.popleft(); del self.where[o[0]]
            if not q: del lv[p]
        return fills, size

    def depth(self, side):
        return {p: sum(o[2] for o in q) for p, q in self.lev[side].items()}


class Market:
    """The book, the clock, the players and what is recorded: the public book every 100 ms, with owners kept apart for the coloured charts, and the trades."""

    def __init__(self, seed=0, start=1_000_000, band=60):
        self.book = Book(); self.rng = np.random.default_rng(seed); self.t = 0; self.start = start; self.last = start; self.band = band
        self.players = []; self.trades = []; self.snaps = []; self.quotes = []; self.nsnap = 100; self.fair = float(start)

    def mid(self):
        b, a = self.book.best(1), self.book.best(-1)
        return (b + a) / 2 if b is not None and a is not None else float(self.last)

    def market_order(self, side, size, owner, t):
        fills, left = self.book.take(side, size)
        for p, z, maker, oid in fills:
            self.trades.append((t, p, z, side, owner, maker)); self.last = p
            for pl_ in self.players:
                if pl_.name == maker: pl_.on_fill(self, oid, z, t, -side, p)
        return fills, left

    def snapshot(self, t):
        """The best bid and ask, then the size at each price within the band around the mid, by owner."""
        m = self.mid(); self.quotes.append((t, self.book.best(1), self.book.best(-1)))
        for side in (1, -1):
            for p, q in self.book.lev[side].items():
                if abs(p - m) > self.band: continue
                by = {}
                for o in q: by[o[1]] = by.get(o[1], 0.0) + o[2]
                for w, z in by.items(): self.snaps.append((t, p, side, w, z))

    def run(self, ms, step=100):
        """Run to time ms: whichever player wakes first acts; the book is published every step ms."""
        heap = [(p.next_time, i) for i, p in enumerate(self.players)]; heapq.heapify(heap); ns = self.nsnap
        while heap and heap[0][0] <= ms:
            tw, i = heapq.heappop(heap)
            while ns <= tw: self.snapshot(ns); ns += step
            self.t = tw; p = self.players[i]; p.act(self, tw); heapq.heappush(heap, (p.next_time, i))
        while ns <= ms: self.snapshot(ns); ns += step
        self.nsnap = ns
        return self

    def public_trades(self):
        return pl.DataFrame(self.trades, schema=["t", "price", "size", "side", "taker", "maker"], orient="row") if self.trades else None

    def public_mid(self, every=1000):
        """The mid every `every` ms from the published best prices, the last quote in each interval."""
        Q = pl.DataFrame(self.quotes, schema=["t", "bid", "ask"], orient="row").drop_nulls()
        return Q.with_columns(((pl.col("t") - 1) // every * every + every).alias("t"), ((pl.col("bid") + pl.col("ask")) / 2).alias("mid")).group_by("t").agg(pl.col("mid").last()).sort("t")

    def public_book(self):
        return pl.DataFrame(self.snaps, schema=["t", "price", "side", "owner", "size"], orient="row")


class Player:
    name = "player"; next_time = 0

    def act(self, m, t): ...
    def on_fill(self, m, oid, size, t, side, price):
        """Our resting order was filled: side +1, we bought."""


class Noise(Player):
    """Zero intelligence: limit orders, market orders and cancellations at fixed rates, nothing else. Rates per second; a limit order lands d ticks behind the best on its side, d geometric with mean
    `depth`, or joins inside the spread if there is room; each resting order is cancelled at rate `cancel` per second; sizes are lognormal, floored at the minimum order. Nothing knows the price."""
    name = "noise"

    def __init__(self, limit=40.0, market=6.0, cancel=0.05, depth=6.0, size=0.05, sigma=1.2, min_size=0.001):
        self.limit, self.market, self.cancel_rate, self.depth, self.size, self.sigma, self.min_size = limit, market, cancel, depth, size, sigma, min_size
        self.mine = []; self.pos = {}; self.next_time = 1

    def draw_size(self, r):
        return max(round(float(r.lognormal(np.log(self.size), self.sigma)), 3), self.min_size)

    def act(self, m, t):
        r = m.rng; n = len(self.mine); rates = np.array([self.limit, self.market, self.cancel_rate * n]); total = rates.sum()
        kind = r.choice(3, p=rates / total); side = 1 if r.random() < 0.5 else -1
        if kind == 0:
            b = m.book.best(side); o = m.book.best(-side); d = int(r.geometric(1 / self.depth)) - 1
            if b is None: price = (o - side * (d + 1)) if o is not None else m.last - side * (d + 1)
            else: price = b - side * d
            if b is not None and o is not None and abs(o - b) > 1 and r.random() < 0.5: price = b + side
            if o is not None and (price >= o if side == 1 else price <= o): price = o - side
            oid = m.book.add(side, int(price), self.draw_size(r), self.name); self.pos[oid] = len(self.mine); self.mine.append(oid)
        elif kind == 1:
            m.market_order(side, self.draw_size(r), self.name, t)
        elif n:
            oid = self.mine[int(r.integers(n))]; m.book.cancel(oid); self.drop(oid)
        self.next_time = t + max(1, int(r.exponential(1000 / total)))

    def drop(self, oid):
        i = self.pos.pop(oid); last = self.mine.pop()
        if last != oid: self.mine[i] = last; self.pos[last] = i

    def on_fill(self, m, oid, size, t, side, price):
        if oid in self.pos and oid not in m.book.where: self.drop(oid)


class FairValue(Player):
    """The hidden value of the asset: a random walk in ticks, `sigma` per step of `step` ms, with jumps of `jump` ticks either way at rate `jump_rate` per second. No order comes from it; players may read m.fair, some of them late."""
    name = "fair value"

    def __init__(self, sigma=0.15, step=100, jump=0.0, jump_rate=0.0):
        self.sigma, self.step, self.jump, self.jump_rate = sigma, step, jump, jump_rate; self.next_time = step

    def act(self, m, t):
        m.fair += float(m.rng.normal(0, self.sigma)); self.next_time = t + self.step
        if self.jump_rate and m.rng.random() < self.jump_rate * self.step / 1000: m.fair += self.jump * (1 if m.rng.random() < 0.5 else -1)


class MarketMaker(Player):
    """Quotes a ladder on both sides around its estimate of the value, which is the fair value as it stood at its last refresh, leaned against its position: `lean` ticks per BTC held. Every `refresh` ms it
    works out `levels` prices on each side, from `half` ticks off its centre, `size` BTC each. Orders already at a wanted price stay, keeping their place in the line; the rest are cancelled and the missing ones
    sent. It never crosses: a price the other side has already reached is skipped. With widen > 0 it quotes `widen` ticks further out from `before` ms before each whole `period` to `after` ms after
    it, where it expects the bar-close traders. Kill switch: if, while quoting, it sees the mid move `kill_move` ticks or more within a second, it cancels all its quotes and stays out for `kill_pause` ms;
    `kills` keeps the times. Inventory limit: with a position of `kill_pos` BTC or more either way, it quotes only the side that reduces it."""
    name = "market maker"

    def __init__(self, refresh=500, levels=5, half=1, size=0.5, lean=4.0, widen=0, period=60_000, before=2000, after=5000, kill_move=0, kill_pos=0.0, kill_pause=5000):
        self.refresh, self.levels, self.half, self.size, self.lean = refresh, levels, half, size, lean; self.widen, self.period, self.before, self.after = widen, period, before, after
        self.kill_move, self.kill_pos, self.kill_pause = kill_move, kill_pos, kill_pause; self.out_until = -1; self.recent = deque(); self.kills = []
        self.mine = {}; self.pos = 0.0; self.cash = 0.0; self.next_time = refresh; self.path = []

    def act(self, m, t):
        if t < self.out_until:                                     # out: no quotes, and nothing seen while out counts against the return
            self.recent.clear()
            for oid in list(self.mine): m.book.cancel(oid)
            self.mine.clear(); self.path.append((t, self.pos, self.cash + self.pos * m.fair)); self.next_time = t + self.refresh
            return
        x = m.mid(); self.recent.append((t, x))
        while self.recent[0][0] < t - 1000: self.recent.popleft()
        if self.kill_move and max(abs(x - y) for _, y in self.recent) >= self.kill_move:
            self.kills.append(t); self.out_until = t + self.kill_pause
            for oid in list(self.mine): m.book.cancel(oid)
            self.mine.clear(); self.recent.clear(); self.path.append((t, self.pos, self.cash + self.pos * m.fair)); self.next_time = t + self.refresh
            return
        c = m.fair - self.lean * self.pos; ph = t % self.period; h = self.half + (self.widen if self.widen and (ph >= self.period - self.before or ph < self.after) else 0)
        want = {(1, int(np.floor(c) - h - k)) for k in range(self.levels)} | {(-1, int(np.ceil(c) + h + k)) for k in range(self.levels)}
        if self.kill_pos and abs(self.pos) >= self.kill_pos: want = {w for w in want if w[0] == (-1 if self.pos > 0 else 1)}
        for oid, key in list(self.mine.items()):
            if key not in want: m.book.cancel(oid); del self.mine[oid]
        have = set(self.mine.values())
        for side, p in sorted(want - have, key=lambda x: (x[0], -x[0] * x[1])):
            o = m.book.best(-side)
            if o is not None and (p >= o if side == 1 else p <= o): continue
            self.mine[m.book.add(side, p, self.size, self.name)] = (side, p)
        self.path.append((t, self.pos, self.cash + self.pos * m.fair)); self.next_time = t + self.refresh

    def on_fill(self, m, oid, size, t, side, price):
        self.pos += side * size; self.cash -= side * price * size
        if oid not in m.book.where: self.mine.pop(oid, None)


class Value(Player):
    """Trades towards the hidden value: at rate `rate` per second it looks, and if the mid is more than `gap` ticks from the value it sends a market order towards it. This is what ties the price to the value.
    With `max_pos` > 0 its capital is limited: it does not trade further once its position is `max_pos` BTC either way, and it unwinds only by trading back towards the value later."""
    name = "value"

    def __init__(self, rate=5.0, gap=1.0, size=0.1, max_pos=0.0):
        self.rate, self.gap, self.size, self.max_pos = rate, gap, size, max_pos; self.next_time = 1; self.pos = 0.0

    def act(self, m, t):
        d = m.fair - m.mid()
        if abs(d) > self.gap and not (self.max_pos and (1 if d > 0 else -1) * self.pos >= self.max_pos):
            side = 1 if d > 0 else -1; fills, _ = m.market_order(side, self.size, self.name, t); self.pos += side * sum(z for _, z, _, _ in fills)
        self.next_time = t + max(1, int(m.rng.exponential(1000 / self.rate)))


class Sniper(Player):
    """Sees the fair value at once and trades the gap between the mid and it. Looks every `look` ms: if the mid is `theta` or more ticks below the value it goes long `size` BTC at the market, if `theta` or more above it goes
    short, otherwise it holds, flipping through zero as in the band of Rabechini Amaral (2026). Marked at the fair value. Its orders do take the book's size, unlike the small trader of that paper."""
    name = "sniper"

    def __init__(self, theta=2.0, size=0.5, look=20):
        self.theta, self.size, self.look = theta, size, look
        self.pos = 0.0; self.cash = 0.0; self.next_time = look; self.n = 0; self.path = []; self.edge = {}

    def act(self, m, t):
        g = m.mid() - m.fair; want = self.size if g <= -self.theta else -self.size if g >= self.theta else self.pos; d = want - self.pos
        if abs(d) > 1e-12:
            side = 1 if d > 0 else -1; fills, _ = m.market_order(side, abs(d), self.name, t); self.n += 1
            for p, z, w, _ in fills: self.pos += side * z; self.cash -= side * p * z; self.edge[w] = self.edge.get(w, 0.0) + side * (m.fair - p) * z
        if t % 1000 < self.look: self.path.append((t, self.pos, self.cash + self.pos * m.fair))
        self.next_time = t + self.look


class Twap(Player):
    """Slices parent orders into equal market orders at a fixed interval, as an exchange's TWAP tool does (Bybit's default interval is 30 s, with an optional randomisation of the interval by up to 20%).
    Parents arrive at `rate` per minute, given as (from time ms, rate) so the mix can be changed during a run; each has a size from `sizes` BTC, a side at random and a duration from `minutes`.
    The slice is the parent's size over the number of slices, rounded to 0.001 BTC; the first is sent on arrival. `slices` keeps (time, parent, side, size), the truth that the public feed hides."""
    name = "twap"

    def __init__(self, rate=((0, 0.5),), interval=30_000, jitter=0.0, sizes=(1.0, 2.0, 3.0, 5.0), minutes=(5, 10, 20, 30)):
        self.rate, self.interval, self.jitter, self.sizes, self.minutes = sorted(rate), interval, jitter, sizes, minutes
        self.live = []; self.parents = []; self.slices = []; self.arrival = None; self.next_time = 1

    def gap(self, m, t):
        r = [x for t0, x in self.rate if t >= t0][-1]
        return max(1, int(m.rng.exponential(60_000 / r))) if r > 0 else 60_000

    def act(self, m, t):
        if self.arrival is None: self.arrival = t + self.gap(m, t)
        elif t >= self.arrival:
            side = 1 if m.rng.random() < 0.5 else -1; q = float(m.rng.choice(self.sizes)); n = max(2, int(float(m.rng.choice(self.minutes)) * 60_000 / self.interval)); z = round(q / n, 3)
            heapq.heappush(self.live, (t, len(self.parents), side, z, n)); self.parents.append((t, side, q, n, z)); self.arrival = t + self.gap(m, t)
        while self.live and self.live[0][0] <= t:
            _, pid, side, z, k = heapq.heappop(self.live); m.market_order(side, z, self.name, t); self.slices.append((t, pid, side, z))
            if k > 1: heapq.heappush(self.live, (t + int(self.interval * (1 + self.jitter * m.rng.uniform(-1, 1))), pid, side, z, k - 1))
        self.next_time = min(self.arrival, self.live[0][0]) if self.live else self.arrival


class TrendFollower(Player):
    """Follows the trend of the published mid. With clock=0 it reads the mid every `look` ms; with clock > 0 it reads it once per bar, at each close of a bar of `clock` ms (whole minutes, five
    minutes...), `lag` ms late at most (its computing time). When the average of the last `fast` readings is above the average of the last `slow` it wants to be long `size` BTC, when below short, and it
    gets there with one market order, so a crossing is a flip of twice its size. fast=1 is the last reading itself, the rule of H11. Flat until `slow` readings exist."""
    name = "trend"

    def __init__(self, fast=1, slow=3000, size=0.5, look=1000, clock=0, lag=0):
        self.fast, self.slow, self.size, self.look, self.clock, self.lag = fast, slow, size, look, clock, lag
        self.seen = deque(maxlen=slow); self.sum_slow = 0.0; self.pos = 0.0; self.cash = 0.0; self.next_time = clock or look; self.flips = []

    def act(self, m, t):
        x = m.mid()
        if len(self.seen) == self.slow: self.sum_slow -= self.seen[0]
        self.seen.append(x); self.sum_slow += x
        self.next_time = (t // self.clock + 1) * self.clock + (int(m.rng.integers(self.lag)) if self.lag else 0) if self.clock else t + self.look
        if len(self.seen) < self.slow: return
        f = sum(list(self.seen)[-self.fast:]) / self.fast if self.fast > 1 else x; want = self.size if f > self.sum_slow / self.slow else -self.size; d = want - self.pos
        if abs(d) > 1e-12:
            side = 1 if d > 0 else -1; fills, _ = m.market_order(side, abs(d), self.name, t); self.flips.append((t, side))
            for p, z, _, _ in fills: self.pos += side * z; self.cash -= side * p * z


class Scalper(Player):
    """Our own definition, since the literature has none. Flat, it joins the best bid or ask (side at random) with `size` BTC and follows the best if it moves. Once filled, it rests an exit `gain` ticks
    better than its entry, and closes at the market if the mid moves `stop` ticks against it or after `hold` ms. Looks every `look` ms. `trips` keeps (time in, time out, side, gain in ticks per BTC, how)."""
    name = "scalper"

    def __init__(self, size=0.05, gain=2, stop=3, hold=30_000, look=200):
        self.size, self.gain, self.stop, self.hold, self.look = size, gain, stop, hold, look
        self.entry = None; self.exit = None; self.pos = 0.0; self.cash = 0.0; self.t_in = None; self.p_in = None; self.cash_in = 0.0; self.trips = []; self.next_time = look

    def close(self, m, t, how):
        if self.exit: m.book.cancel(self.exit[0]); self.exit = None
        side = -1 if self.pos > 0 else 1; fills, _ = m.market_order(side, abs(self.pos), self.name, t)
        for p, z, _, _ in fills: self.pos += side * z; self.cash -= side * p * z
        self.done(t, how)

    def done(self, t, how):
        if abs(self.pos) < 1e-9:
            self.trips.append((self.t_in, t, self.side_in, (self.cash - self.cash_in) / self.size, how)); self.pos = 0.0; self.t_in = None

    def act(self, m, t):
        self.next_time = t + self.look
        if self.t_in is None:
            if self.entry and (self.entry[0] not in m.book.where or m.book.best(self.entry[1]) != self.entry[2]): m.book.cancel(self.entry[0]); self.entry = None
            if self.entry is None:
                side = 1 if m.rng.random() < 0.5 else -1; b = m.book.best(side)
                if b is not None: self.entry = (m.book.add(side, b, self.size, self.name), side, b)
            return
        if self.entry: m.book.cancel(self.entry[0]); self.entry = None
        d = 1 if self.pos > 0 else -1; mid = m.mid()
        if d * (mid - self.p_in) <= -self.stop: return self.close(m, t, "stop")
        if t - self.t_in >= self.hold: return self.close(m, t, "time")
        if self.exit is None or self.exit[0] not in m.book.where or abs(self.exit[1] - abs(self.pos)) > 1e-9:
            if self.exit: m.book.cancel(self.exit[0]); self.exit = None
            p = self.p_in + d * self.gain; o = m.book.best(d)
            if o is not None and (o >= p if d == 1 else o <= p): return self.close(m, t, "gain at market")
            self.exit = (m.book.add(-d, p, abs(self.pos), self.name), abs(self.pos))

    def on_fill(self, m, oid, size, t, side, price):
        self.pos += side * size; self.cash -= side * price * size
        if self.entry and oid == self.entry[0]:
            if self.t_in is None: self.t_in, self.p_in, self.side_in, self.cash_in = t, self.entry[2], side, self.cash + side * price * size
            if oid not in m.book.where: self.entry = None
        elif self.exit and oid == self.exit[0]:
            self.exit = (oid, abs(self.pos)) if oid in m.book.where else None
            self.done(t, "gain")


class Stops(Player):
    """Stop orders and forced liquidations, as a crowd: `density` BTC per tick rests on each side from `near` to `far` ticks from the mid, sell stops below and buy stops above. When the mid
    reaches a stop it becomes a market order in the direction of the move: a fall sets off selling. Each tick's stock grows back towards `density` at `renew` per second, so a cascade uses up the
    stops near the price and only a slow rebuild follows. Looks every `look` ms; `fired` keeps (time, side, size)."""
    name = "stops"

    def __init__(self, density=0.2, near=3, far=30, renew=0.01, look=100):
        self.density, self.near, self.far, self.renew, self.look = density, near, far, renew, look
        self.stock = {1: {}, -1: {}}; self.last = None; self.next_time = look; self.fired = []

    def act(self, m, t):
        x = m.mid(); dt = (t - self.last) / 1000 if self.last is not None else None; self.last = t; self.next_time = t + self.look
        for side, sgn in ((-1, -1), (1, 1)):                       # sell stops below the mid, buy stops above
            st = self.stock[side]; lo, hi = (int(np.ceil(x)) - self.far, int(np.floor(x)) - self.near) if side == -1 else (int(np.ceil(x)) + self.near, int(np.floor(x)) + self.far)
            for p in range(lo, hi + 1):
                if p not in st: st[p] = self.density if dt is None else 0.0
                elif dt: st[p] += (self.density - st[p]) * min(1.0, self.renew * dt)
            hit = [p for p in st if (p >= x if side == -1 else p <= x)]
            z = sum(st.pop(p) for p in hit)
            for p in [p for p in st if abs(p - x) > self.far + 5]: del st[p]
            if z > 1e-9: m.market_order(side, round(z, 3), self.name, t); self.fired.append((t, side, z))
