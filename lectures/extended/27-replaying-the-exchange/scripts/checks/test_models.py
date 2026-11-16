"""Our queue rule (l21.Bid) against the published update rules, written literally, on random event sequences at one price.
hftbacktest queue.rs: trade: front -= qty; cum += qty. Depth change: chg = prev - new - cum; cum = 0; if chg < 0: front = min(front, new);
else: prob = share BEHIND; est = front - (1 - prob) chg + min(back - prob chg, 0); front = min(est, new). RiskAverse: front = min(front, new).
Fill when a trade leaves front < 0. PowerProbQueueFunc3: prob = 1 - (front / (front + back)) ** n.
Rigtorp (2013): fills V = max(V + dQ, 0); other decreases V = max(V + p dQ, 0), p = f(V) / (f(V) + f(max(Q - S - V, 0))), f = identity."""
import sys, random, numpy as np, polars as pl
sys.path.insert(0, sys.argv[1]); import l21 as L21
P = 1_000_000


def hft(events, q0, n, after_trades=False):
    front, prev, cum = q0, q0, 0.0
    for t, kind, v in events:
        if kind == "t":
            front -= v; cum += v
            if front < -1e-12: return t
        else:
            chg = prev - v - cum; cum_seen = cum; cum = 0.0
            if chg < 0: front = min(front, v)
            else:
                back = prev - front - (cum_seen if after_trades else 0.0)
                if n == "ra": front = min(front, v)
                else:
                    prob = 1 - (front / (front + back)) ** n if front + back > 0 else 1.0
                    front = min(front - (1 - prob) * chg + min(back - prob * chg, 0), v)
            prev = v
    return None


def rigtorp(events, q0):
    """V: size ahead; Q: size displayed after the trades so far (our order not in it, so Q - S - V = Q - V)."""
    V, Q = q0, q0
    for t, kind, v in events:
        if kind == "t":
            if v > V + 1e-12: return t
            V = max(V - v, 0); Q -= v
        else:
            dQ = v - Q
            if dQ < 0:
                p = V / (V + max(Q - V, 0)) if Q > 0 else 1.0
                V = max(V + p * dQ, 0)
            Q = v
    return None


random.seed(1); bad = {1.0: 0, 2.0: 0, 5.0: 0, np.inf: 0, "rig": 0}; bad2 = {1.0: 0, 2.0: 0, 5.0: 0}; N = 3000
for k in range(N):
    q0 = round(random.uniform(0.2, 5), 3); level, t, ev = q0, 100, []
    for _ in range(random.randint(3, 25)):
        t += random.randint(1, 99)
        if random.random() < 0.5:
            s = round(random.uniform(0.001, 0.6) * random.choice([0.2, 1, 3]), 3); ev.append((t, "t", s)); level -= s
        else:
            t = (t // 100 + 1) * 100; level = max(round(level + random.uniform(-1.5, 1.2), 3), 0.0); ev.append((t, "u", level))
        if level < 0: break
    trades = [(t, s) for t, k_, s in ev if k_ == "t"]; ups = [(t, s) for t, k_, s in ev if k_ == "u"]
    B = pl.DataFrame({"cts": [0] + [t for t, _ in ups], "tick": [P] * (len(ups) + 1), "size": [q0] + [s for _, s in ups]}, schema={"cts": pl.Int64, "tick": pl.Int64, "size": pl.Float64})
    T = pl.DataFrame({"ts": [t for t, _ in trades], "side": [-1] * len(trades), "tick": [P] * len(trades), "size": [s for _, s in trades]},
                     schema={"ts": pl.Int64, "side": pl.Int64, "tick": pl.Int64, "size": pl.Float64})
    S = pl.DataFrame({"ts": [0], "bid": [P], "ask": [P + 1]})
    # keep only events up to the first level that the trades would push below zero (inconsistent data)
    for a in (1.0, 2.0, 5.0, np.inf):
        ours = L21.Bid(B, T, S, 40, L=10, a=a, hold=10_000).q2
        ref = hft(ev, q0, "ra" if a == np.inf else a)
        if ours != ref: bad[a] += 1
        if a != np.inf and ours != hft(ev, q0, a, after_trades=True): bad2[a] += 1
    if L21.Bid(B, T, S, 40, L=10, a=1.0, hold=10_000).q2 != rigtorp(ev, q0): bad["rig"] += 1
print(f"{N} random sequences; disagreements with the code as published:", bad)
print("with hftbacktest's size behind measured after the trades:", bad2)
