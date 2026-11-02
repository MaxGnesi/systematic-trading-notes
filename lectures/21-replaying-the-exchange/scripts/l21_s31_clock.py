"""Lecture 21 §3.1: does the trade clock line up with the book's clock? For five days spread over the sample, the share of the size sold at the best
bid that must have been refilled within the same update (l21_s31_net.py), with the trades shifted by -100 to +100 ms against the book. If the two
clocks agree, the share is smallest at no shift: a misplaced trade looks like a refill that never happened.
Output: L21_OUT/s31/clock_shift.parquet. Usage: python l21_s31_clock.py [DAY ...]"""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
import l21_s31_net as N                                                     # side(): the same measure as §3.1
DAYS = sys.argv[1:] or ["2025-09-24", "2025-10-01", "2025-10-15", "2025-10-22", "2025-10-29"]
SHIFTS = [-100, -50, -20, -10, -5, -2, 0, 2, 5, 10, 20, 50, 100]
rows = []
for day in DAYS:
    N.wait_memory()
    S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "q_bid"]).sort("ts")
    T = pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"]).filter(pl.col("side") == -1)
    for d in SHIFTS:
        r = N.side(S["ts"].to_numpy(), S["bid"].to_numpy(), S["q_bid"].to_numpy(), T["ts"].to_numpy() + d, T["tick"].to_numpy(), T["size"].to_numpy())
        rows.append(dict(day=day, shift_ms=d, hidden_share=r["hidden"] / r["traded"]))
    print(day, flush=True); del S, T
D = pl.DataFrame(rows); D.write_parquet(N.OUT / "clock_shift.parquet")
print(D.pivot(on="day", index="shift_ms", values="hidden_share"))
