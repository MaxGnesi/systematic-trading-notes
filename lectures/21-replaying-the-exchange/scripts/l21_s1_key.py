"""Lecture 21 §1, the key chart's data: one resting bid of 0.001 BTC at the best on 1 October 2025, 09:33:15 UTC, followed under the three fill
rules; and every 15 s of the same day, the same order (held up to 120 s, not re-posted), with its fill times and the mid 1 s and 10 s after each
fill. The moment is also followed with every cancellation put behind us (a = infinity), the other end of the unknown split. One hour of the book is
read at a time. Output: L21_OUT/key/ (moment_*.parquet, moment.json, day_orders.parquet).
Usage: python l21_s1_key.py [moment | day]; both if no argument (the day takes a few minutes)."""
import json, sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
DAY, HMS, HOLD = "2025-10-01", "09:33:15", 120_000
try:
    import psutil
except ImportError:
    psutil = None


def wait_memory(gb=0.6):
    while psutil and psutil.virtual_memory().available / 2**30 < gb: time.sleep(5)


def mid_after(S, t):
    st = S["ts"].to_numpy(); i = np.searchsorted(st, t, "right") - 1
    return (S["bid"][int(i)] + S["ask"][int(i)]) / 2


PARTS = sys.argv[1:] or ["moment", "day"]

# the moment
if "moment" in PARTS:
  t0 = L21.ms(DAY, HMS)
  B, T, S = L21.window(DAY, t0 - 600_000, t0 + HOLD + 20_000)
  o = L21.Bid(B, T, S, t0, hold=HOLD); oi = L21.Bid(B, T, S, t0, a=np.inf, hold=HOLD)
  fills = {r: getattr(o, r) for r in ("q0", "q2", "q1")}
  mk = {r: {h: (mid_after(S, t + 1000 * h) - o.p) / o.p * 1e4 for h in (1, 10)} for r, t in fills.items()}
  end = max(fills.values()) + 12_000
  S.filter(pl.col("ts").is_between(t0 - 3000, end)).select("ts", "bid", "ask").write_parquet(L21.KEY / "moment_book.parquet")
  T.filter(pl.col("ts").is_between(t0 - 3000, end)).write_parquet(L21.KEY / "moment_trades.parquet")
  pl.DataFrame(o.path, schema=["ts", "ahead", "level"], orient="row").write_parquet(L21.KEY / "moment_queue.parquet")
  pl.DataFrame(oi.path, schema=["ts", "ahead", "level"], orient="row").write_parquet(L21.KEY / "moment_queue_inf.parquet")
  (L21.KEY / "moment.json").write_text(json.dumps(dict(t0=t0, ta=o.ta, p=o.p, q=o.q, fills=fills, markout=mk, q2_inf=oi.q2), indent=1))
  print("moment: price", o.p * L21.TICK, "ahead", o.q, {r: (t - t0) / 1000 for r, t in fills.items()}, mk, "a = inf:", (oi.q2 - t0) / 1000)
  del B, T, S

# the day: the same order every 15 s
if "day" in PARTS:
  rows = []
  for h in range(24):
      wait_memory(); t_a = L21.ms(DAY) + h * 3600_000
      B, T, S = L21.window(DAY, t_a - 600_000, t_a + 3600_000 + HOLD + 20_000)
      for t0 in range(t_a, t_a + 3600_000, 15_000):
          o = L21.Bid(B, T, S, t0, hold=HOLD)
          if not o.ok: continue
          r = dict(t0=t0, p=o.p, q=o.q, q2i=L21.Bid(B, T, S, t0, a=np.inf, hold=HOLD).q2)    # q2i: the queue rule with a = infinity
          for k in ("q0", "q2", "q1", "q2i"):
              t = getattr(o, k) if k != "q2i" else r[k]; r[k] = t
              for hh in (1, 10): r[f"{k}_m{hh}"] = None if t is None else (mid_after(S, t + 1000 * hh) - o.p) / o.p * 1e4
          rows.append(r)
      print(h, len(rows), flush=True); del B, T, S
  D = pl.DataFrame(rows); D.write_parquet(L21.KEY / "day_orders.parquet")
  print(D.select([pl.col(k).is_not_null().mean().alias(f"filled_{k}") for k in ("q0", "q2", "q1", "q2i")] +
                 [pl.col(f"{k}_m{h}").mean().alias(f"{k}_m{h}") for k in ("q0", "q2", "q1", "q2i") for h in (1, 10)]))
