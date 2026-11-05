"""Check the book of l22_sim.py on cases known by hand, then on a noise run: time priority, the walk through prices, no crossed book, and each player knows its resting orders."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import l22_sim as Sim
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
