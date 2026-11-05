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
