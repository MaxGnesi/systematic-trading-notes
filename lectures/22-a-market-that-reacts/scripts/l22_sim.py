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
        self.players = []; self.trades = []; self.snaps = []; self.nsnap = 100; self.fair = float(start)

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
        """Size at each price within the band around the mid, by owner."""
        m = self.mid()
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
    """The hidden value of the asset: a random walk in ticks, `sigma` per step of `step` ms. No order comes from it; players may read m.fair, some of them late."""
    name = "fair value"

    def __init__(self, sigma=0.15, step=100):
        self.sigma, self.step = sigma, step; self.next_time = step

    def act(self, m, t):
        m.fair += float(m.rng.normal(0, self.sigma)); self.next_time = t + self.step


class MarketMaker(Player):
    """Quotes a ladder on both sides around its estimate of the value, which is the fair value as it stood at its last refresh, leaned against its position: `lean` ticks per BTC held. Every `refresh` ms it
    works out `levels` prices on each side, from `half` ticks off its centre, `size` BTC each. Orders already at a wanted price stay, keeping their place in the line; the rest are cancelled and the missing ones
    sent. It never crosses: a price the other side has already reached is skipped."""
    name = "market maker"

    def __init__(self, refresh=500, levels=5, half=1, size=0.5, lean=4.0):
        self.refresh, self.levels, self.half, self.size, self.lean = refresh, levels, half, size, lean
        self.mine = {}; self.pos = 0.0; self.cash = 0.0; self.next_time = refresh; self.path = []

    def act(self, m, t):
        c = m.fair - self.lean * self.pos
        want = {(1, int(np.floor(c) - self.half - k)) for k in range(self.levels)} | {(-1, int(np.ceil(c) + self.half + k)) for k in range(self.levels)}
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
    """Trades towards the hidden value: at rate `rate` per second it looks, and if the mid is more than `gap` ticks from the value it sends a market order towards it. This is what ties the price to the value."""
    name = "value"

    def __init__(self, rate=5.0, gap=1.0, size=0.1):
        self.rate, self.gap, self.size = rate, gap, size; self.next_time = 1; self.pos = 0.0

    def act(self, m, t):
        d = m.fair - m.mid()
        if abs(d) > self.gap:
            side = 1 if d > 0 else -1; fills, _ = m.market_order(side, self.size, self.name, t); self.pos += side * sum(z for _, z, _, _ in fills)
        self.next_time = t + max(1, int(m.rng.exponential(1000 / self.rate)))
