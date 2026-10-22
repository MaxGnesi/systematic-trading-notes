"""Lecture 13 §6: does the horizon on which the flow's variance is measured matter? Fixed band with Q from 1-, 5- and 30-minute sums of signed dollars.
Each horizon gets its own fairness constant from the burn-in, October to December 2021 (as many bars as the dollar clock there), then runs on the two windows (W = 28 days, minimum length 0 and 5 s)."""
import json, sys
from datetime import date, timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, l13_s6 as m

HS = (60, 300, 1800); MS = (0, 5); W = 28


def q(o, h):
    b = (o["t"] - o["t"][0] // 86_400_000 * 86_400_000) // (h * 1000)
    return float(np.sum(np.bincount(b, o["s"]) ** 2))


def run(wname, start, end, K):
    days = [start - timedelta(days=W) + timedelta(days=i) for i in range((end - start).days + W + 1)]
    hist = {h: [] for h in HS}; clocks = {(h, mm): m.Clock(f"band_H{h}_m{mm}") for h in HS for mm in MS}; st = {key: (0.0, 0) for key in clocks}
    for d0 in days:
        tape.wait_for_memory(1.5)
        o = m.load_orders(d0)
        if d0 >= start:
            for (h, mm), c in clocks.items():
                thr = K[h] * np.sqrt(float(np.median(hist[h][-W:])) / m.N)
                ends, *s = m._band(o["s"], o["t"], thr, mm * 1000, *st[(h, mm)]); st[(h, mm)] = tuple(s); c.add(d0, o, ends)
        for h in HS: hist[h].append(q(o, h))
        if d0 >= start and d0.day == 1: print(wname, d0, tape.peak_private_gb(), "GB peak", flush=True)
    for c in clocks.values():
        if c.rows and wname != "calib": pl.concat(c.rows).write_parquet(m.OUT / f"{wname}_{c.name}.parquet")
    return {c.name: c.count for c in clocks.values()}


if __name__ == "__main__":
    cal = run("calib", date(2021, 11, 1), date(2021, 12, 31), {h: 1.0 for h in HS})   # October 2021 serves as the first 28 days of history
    import bars
    dpd = np.mean([pl.read_parquet(bars.bars_dir("BTCUSDT", "dollar") / f"{ym}.parquet").height for ym in ("2021-11", "2021-12")]) / 30.5
    K = {h: float(np.sqrt(np.mean(list(cal[f"band_H{h}_m0"].values())) / dpd)) for h in HS}
    print("fairness constants", K, flush=True)
    R = {"K": K, **{w: run(w, *m.WINDOWS[w], K) for w in m.WINDOWS}}
    (L13_RESULTS / "l13_s6_horizon_raw.json").write_text(json.dumps(R))
