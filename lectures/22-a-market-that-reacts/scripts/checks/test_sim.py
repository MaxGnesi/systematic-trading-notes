"""Check the book of l22_sim.py on cases known by hand, then on a noise run: time priority, the walk through prices, no crossed book, and each player knows its resting orders."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import polars as pl, l22_sim as Sim
B = Sim.Book()
a = B.add(-1, 101, 0.5, "x"); b = B.add(-1, 101, 0.3, "y"); c = B.add(-1, 102, 1.0, "z")
f, left = B.take(1, 0.6)
assert [(p, round(z, 6), w) for p, z, w, _ in f] == [(101, 0.5, "x"), (101, 0.1, "y")] and left == 0, "oldest first at the best price"
f, left = B.take(1, 0.7)
assert [(p, round(z, 6), w) for p, z, w, _ in f] == [(101, 0.2, "y"), (102, 0.5, "z")], "the rest of the line, then the next price"
assert B.best(-1) == 102 and round(B.depth(-1)[102], 6) == 0.5
assert B.cancel(c) == 0.5 and B.best(-1) is None and B.cancel(c) == 0.0
f, left = B.take(1, 1.0); assert f == [] and left == 1.0, "an empty book fills nothing"
try:
    B.add(1, 100, 1.0, "x"); B.add(-1, 100, 1.0, "y"); raise SystemExit("a crossing limit order was accepted")
except AssertionError as e:
    assert "crosses" in str(e)
print("hand cases hold")

m = Sim.Market(seed=1); n = Sim.Noise(); m.players.append(n); added = {"crossed": 0}
for T in range(10_000, 120_001, 10_000):
    m.run(T); b, o = m.book.best(1), m.book.best(-1)
    if b is not None and o is not None and b >= o: added["crossed"] += 1
assert added["crossed"] == 0, "the book crossed"
assert set(m.book.where) == set(n.mine), "the player lost track of its resting orders"
for side in (1, -1):
    for p, q in m.book.lev[side].items(): assert q, "an empty line was left in the book"
print("noise run: no crossed book,", len(m.trades), "trades,", len(m.book.where), "orders resting")

m = Sim.Market(seed=2); mm = Sim.MarketMaker(); m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(), mm]; m.run(120_000)
T = m.public_trades().filter(pl.col("maker") == "market maker")
buys, sells = T.filter(pl.col("side") == -1)["size"].sum(), T.filter(pl.col("side") == 1)["size"].sum()
assert abs((buys - sells) - mm.pos) < 1e-9, "the market maker's position does not match its fills"
assert set(mm.mine) <= set(m.book.where), "the market maker lost track of its resting orders"
print("market maker: position", round(mm.pos, 3), "matches its", T.height, "fills")

m = Sim.Market(seed=2); sn = Sim.Sniper(theta=2.0); m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(jump=5.0, jump_rate=0.1), Sim.Value(), Sim.MarketMaker(), sn]; m.run(120_000)
T = m.public_trades().filter(pl.col("taker") == "sniper"); q = T.filter(pl.col("side") == 1)["size"].sum() - T.filter(pl.col("side") == -1)["size"].sum()
assert abs(q - sn.pos) < 1e-9, "the sniper's position does not match its trades"
assert abs(sn.pos) <= sn.size + 1e-9, "the sniper went past its position limit"
print("sniper: position", round(sn.pos, 3), "matches its", T.height, "fills")

import numpy as np, l22_styles as St
m = Sim.Market(seed=4); tw = Sim.Twap(rate=((0, 2.0),)); m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(), Sim.MarketMaker(), tw]; m.run(600_000)
for pid, (t0, side, q, n, z) in enumerate(tw.parents):
    s = [x for x in tw.slices if x[1] == pid]; assert all(x[2] == side and x[3] == z for x in s), "a slice changed side or size"
    assert len(s) <= n and np.allclose(np.diff([x[0] for x in s]), 30_000), "slices not 30 s apart"
    if t0 + (n - 1) * 30_000 <= 600_000: assert len(s) == n, "a parent lost slices"
O = pl.DataFrame({"t": [0, 30_000, 60_000, 90_000, 120_000, 500, 61_000], "side": [1] * 6 + [-1], "q": [0.2] * 5 + [0.3, 0.2]}).sort("t"); R, lab = St.runs(O, min_n=5)
assert R.height == 1 and R["n"][0] == 5 and lab.tolist() == [0, -1, 0, 0, -1, 0, 0], "the run rule on a hand case: another size or side stays out"
print("twap:", len(tw.parents), "parents,", len(tw.slices), "slices; run rule holds on a hand case")

Q = pl.DataFrame({"t": list(range(0, 300_001, 100)), "bid": [100 + (t >= 180_000) * 10 for t in range(0, 300_001, 100)], "ask": [102 + (t >= 180_000) * 10 + 2 * (178_100 <= t <= 180_000) for t in range(0, 300_001, 100)]})
O = pl.DataFrame({"t": [181_000, 181_500, 200_000], "side": [1, -1, 1], "q": [0.5, 0.2, 4.0]}); X = St.marks(O, Q, slow=3)
r = X.filter(pl.col("t") == 180_000).row(0, named=True)
assert r["trend"] == 1 and abs(r["w0"] - 0.3) < 1e-9 and abs(r["g0"] - 0.7) < 1e-9 and abs(r["wc"] - 4.0 * 3 / 40) < 1e-9, "the flow at a mark on a hand case"
assert abs(r["sb"] - 4.0) < 1e-9 and abs(r["sc"] - 2.0) < 1e-9, "the spread before a mark on a hand case"
print("marks: flow and spread hold on a hand case")
X5 = St.marks(O, Q, slow=3, offset=5000); r5 = X5.filter(pl.col("t") == 185_000).row(0, named=True)
assert abs(r5["w0"]) < 1e-9 and abs(r5["wc"] - r["wc"]) < 1e-9, "a fake mark keeps its minute's quiet seconds"
print("fake marks: compared with their minute's quiet seconds")

m = Sim.Market(seed=3); sc = Sim.Scalper(); m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(gap=3.0), Sim.MarketMaker(), sc]; m.run(300_000)
T = m.public_trades(); q = T.filter(pl.col("taker") == "scalper").select((pl.col("side") * pl.col("size")).sum()).item() - T.filter(pl.col("maker") == "scalper").select((pl.col("side") * pl.col("size")).sum()).item()
assert abs(q - sc.pos) < 1e-9 and abs(sc.pos) <= sc.size + 1e-9, "the scalper's position does not match its fills or passed its size"
print("scalper: position", round(sc.pos, 3), "matches its fills;", len(sc.trips), "round trips")

import l22_hybrid as H
flat = {tau: (0.0, 1.0) for tau in (100, 1_000, 10_000, 60_000, 300_000)}; none = (np.array([100.0, 60_000.0]), np.array([0.0, 0.0]))
h = H.Hybrid(None, 0, 0, layers="A", resp=flat, refill=none, books=({99: 1.0}, {101: 1.0, 102: 1.0, 103: 2.0}))
f, left = h.market_order(0, 1, 1.5); assert f == [(101, 1.0), (102, 0.5)] and left == 0, "a buy walks the asks from the best"
f, left = h.market_order(1000, 1, 1.0); assert f == [(102, 0.5), (103, 0.5)], "what we took is gone for our next order (layer A)"
h = H.Hybrid(None, 0, 0, layers="AB", resp=flat, refill=(np.array([100.0, 1000.0]), np.array([0.5, 1.0])), books=({99: 1.0}, {101: 1.0, 102: 1.0, 103: 2.0}))
h.market_order(0, 1, 1.5); assert h.levels(100, -1)[:2] == [(101, 0.5), (102, 0.75)] and h.levels(1000, -1)[:2] == [(101, 1.0), (102, 1.0)], "it comes back along the refill curve (layer B)"
h = H.Hybrid(None, 0, 0, layers="C", resp={tau: (10.0, 0.5) for tau in flat}, refill=none, books=({999_999: 10.0}, {1_000_001: 10.0}))
h.market_order(0, 1, 4.0); assert abs(h.mid(500) - (1_000_000 + 20.0 * 1_000_000 / 1e4)) < 1e-6 and h.levels(500, -1)[0][0] == 1_000_001 + 2000, "the mid and the book move by R for our size (layer C)"
h.market_order(600, -1, 4.0); assert abs(h.shift(700)) < 1e-6, "an opposite order of the same size cancels the shift"
print("hybrid replay: walk, depletion, refill and shift hold on hand cases")
