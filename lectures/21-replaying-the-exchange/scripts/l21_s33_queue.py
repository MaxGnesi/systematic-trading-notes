"""Lecture 21 §3.3 and §3.4: resting orders in the queue on data (results/hypotheses.md, "The sample of §3.3 and §3.4"). On each day, eight
half-hours drawn at random (seeded by the day), bids and asks; in each, an order of 0.001 BTC sent every 15 s, joining at the best price standing
at t + 50 ms and held up to 120 s without re-posting. Fill times under Q0, Q1 and Q2 (a in {1, 2, 5, 20, infinity}) by the rules of l21.Bid, through
l21_mm.Window (asks as bids with prices negated). Per order and rule: the size ahead and the size displayed at joining, the fill time (null if not
filled within 120 s), whether the fill was adverse (the best price on our side moved through ours at the first book update after it) and the mid
1 s and 10 s after it, in the same negated units for asks.
Output: L21_OUT/s33/<day>.parquet. Usage: python l21_s33_queue.py [DAY ...] (all days if none)."""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21, l21_mm as MM
OUT = L21.OUT / "s33"; OUT.mkdir(parents=True, exist_ok=True)
L, HOLD, EVERY, SIZE = 50, 120_000, 15_000, 0.001
RULES = (("Q0", None), ("Q1", None)) + tuple(("Q2", a) for a in (1.0, 2.0, 5.0, 20.0, np.inf))


def joined(W, p, ta):
    """Size ahead of us when we join at p at ta (the last update less the trades at p since) and the size displayed then."""
    c, z = W.lev.get(p, (None, None))
    if c is None: return np.nan, np.nan
    k0 = np.searchsorted(c, ta, side="right") - 1
    if k0 < 0: return np.nan, np.nan
    h, i = np.searchsorted(W.tt, c[k0], side="right"), np.searchsorted(W.tt, ta, side="right")
    pre = float(W.tz[h:i][W.tk[h:i] == p].sum())
    return max(float(z[k0]) - pre, 0.0), float(z[k0])


def day_queue(day):
    d0 = L21.ms(day); rng = np.random.default_rng(int(day.replace("-", "")))
    halves = np.sort(rng.choice(48, 8, replace=False)); rows = []
    for side in (1, -1):
        for hh in halves:
            a0 = d0 + int(hh) * MM.WIN; MM.wait_memory(); W = MM.Window(day, a0, a0 + MM.WIN, side)
            for t in range(a0, a0 + MM.WIN, EVERY):
                ta = t + L; k = W.at(ta)
                if k < 0: continue
                p = int(W.best[k]); ahead, shown = joined(W, p, ta)
                for rule, a in RULES:
                    tf = W.fill(p, ta, ta + HOLD, rule, a)
                    if tf is None:
                        rows.append((side, t, ta, p, ahead, shown, rule if a is None else f"Q2 a={a:g}", None, None, np.nan, np.nan)); continue
                    kf = W.at(tf); adv = bool(W.best[min(kf + 1, len(W.best) - 1)] < p)
                    rows.append((side, t, ta, p, ahead, shown, rule if a is None else f"Q2 a={a:g}", tf, adv, W.mid[W.at(tf + 1000)], W.mid[W.at(tf + 10_000)]))
            del W
    return pl.DataFrame(rows, schema=["side", "sent", "arrival", "price", "ahead", "shown", "rule", "fill", "adverse", "mid1", "mid10"],
                        orient="row").with_columns(pl.lit(day).alias("day"))


if __name__ == "__main__":
    days = sys.argv[1:] or sorted(p.stem for p in L21.STATE.glob("*.parquet"))
    for day in days:
        f = OUT / f"{day}.parquet"
        if f.exists() and not sys.argv[1:]: continue
        t0 = time.time(); D = day_queue(day); D.write_parquet(f)
        print(day, f"{time.time() - t0:.0f} s", D.group_by("rule").agg(pl.col("fill").is_not_null().mean().round(3)).sort("rule").rows(), flush=True)
