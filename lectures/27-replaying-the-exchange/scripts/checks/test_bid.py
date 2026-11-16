"""Check the replay (l21.Bid) on the invented example of cards 2.1 and 2.3, where the answers are known by hand."""
import sys, numpy as np, polars as pl
sys.path.insert(0, sys.argv[1]); import l21 as L21
P = 1_000_000                                                           # USD 100,000.0 in ticks
B = pl.DataFrame({"cts": [0, 100, 200, 300], "tick": [P] * 4, "size": [2.0, 1.2, 1.6, 0.6]})
T = pl.DataFrame({"ts": [30, 70, 130, 250, 340, 420], "side": [-1] * 6, "tick": [P] * 5 + [P - 1], "size": [0.3, 0.2, 0.4, 0.2, 0.5, 0.3]})
S = pl.DataFrame({"ts": [0, 100, 200, 300], "bid": [P] * 4, "ask": [P + 1] * 4})
expect = {1.0: 340, 2.0: 340, np.inf: 420}
for a, tf in expect.items():
    o = L21.Bid(B, T, S, 10, L=50, a=a, hold=1000)
    path = [(t, round(v, 3)) for t, v, _ in o.path]
    print(f"a={a}: joined behind {o.q} (hand: 1.7), q0 {o.q0} (hand: 70), q2 {o.q2} (hand: {tf}), q1 {o.q1} (hand: 420)", path)
