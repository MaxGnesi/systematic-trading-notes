"""Lecture 15 §6: a resting order that is re-posted. Same sample as l15_resting_tail.py (every 10th day, a decision every 7th minute, buy and mirrored sell).
The order rests one tick inside the last trade price; if not filled within STEP seconds, it is cancelled and re-posted one tick inside the last trade price
at that moment; this repeats until it is filled or the maximum wait is reached, when it becomes a market order. Cost against a market order sent at the
decision, in bp (positive = worse): mean, percentiles over all orders, average of the worst 5%, number of re-posts."""
import json, sys, time
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from l15_resting_fn import first_through
from datetime import date, datetime, timezone

SYM = "BTCUSDT"; TAKER, MAKER, HALF, TICK = 5.0, 2.0, 0.04, 0.1                # as in l15_resting_tail.py
DAYS = [date(2021, 11, 1) + timedelta(days=10 * k) for k in range(200) if date(2021, 11, 1) + timedelta(days=10 * k) <= date(2026, 9, 29)]


def day_trades(d):
    a = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000); b = a + 86_400_000 + 3_700_000
    fs = sorted({tape.source(SYM, x.strftime("%Y-%m")) for x in (d, d + timedelta(days=1))}); fs = [f for f in fs if Path(f).exists()]
    t = pl.scan_parquet(fs).filter(pl.col("transact_time").is_between(a - 60_000, b)).select("transact_time", "price").collect().sort("transact_time")
    return a, t["transact_time"].to_numpy(), t["price"].to_numpy()


VARIANTS = [(5_000, 30_000), (5_000, 60_000), (5_000, 300_000), (5_000, 3_600_000), (10_000, 60_000), (10_000, 300_000)]   # (re-post every, market order after)
rows = []; t0 = time.time()
for d in DAYS:
    tape.wait_for_memory(1.5)
    a, ts, px = day_trades(d)
    if len(ts) < 1000: continue
    dec = a + np.arange(0, 86_400_000, 7 * 60_000)
    k = np.searchsorted(ts, dec, side="right") - 1; ok = k >= 0; dec = dec[ok]; p0 = px[k[ok]]
    for side in (1, -1):
        for step, tmax in VARIANTS:
            cost = np.full(len(dec), np.nan); reposts = np.zeros(len(dec), np.int64); open_ = np.ones(len(dec), bool); s = 0
            while open_.any() and s * step < tmax:
                tk = dec + s * step; idx = np.nonzero(open_)[0]
                ps = px[np.searchsorted(ts, tk[idx], side="right") - 1]; lim = ps - side * TICK
                ft = first_through(ts, px, tk[idx], lim, side, min(step, tmax - s * step))
                hit = ft >= 0
                cost[idx[hit]] = side * np.log(lim[hit] / p0[idx[hit]]) * 1e4 + MAKER
                open_[idx[hit]] = False; reposts[idx[~hit]] += 1; s += 1
            idx = np.nonzero(open_)[0]                                           # still open at the maximum wait: market order
            pT = px[np.searchsorted(ts, dec[idx] + tmax, side="right") - 1]
            cost[idx] = side * np.log(pT / p0[idx]) * 1e4 + TAKER + HALF
            rows.append(pl.DataFrame({"day": [str(d)] * len(dec), "variant": f"re-post every {step // 1000} s, market order after {tmax // 1000} s",
                                      "cost": cost - (TAKER + HALF), "chased": open_, "reposts": reposts}))
X = pl.concat(rows); out = []
for (v,), g in X.group_by("variant", maintain_order=True):
    c = g["cost"].to_numpy(); q95, q99 = np.quantile(c, [0.95, 0.99]); worst = np.sort(c)[-max(1, len(c) // 20):]
    dm = g.group_by("day").agg(pl.col("cost").mean())["cost"].to_numpy()
    out.append(dict(variant=v, mean=round(float(c.mean()), 2), t=round(float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), 1), p95=round(float(q95), 1), p99=round(float(q99), 1),
                    es95=round(float(worst.mean()), 1), chased=round(float(g["chased"].mean()), 3), mean_reposts=round(float(g["reposts"].mean()), 2)))
(L15_RESULTS / "l15_resting_repost.json").write_text(json.dumps(out, indent=1))
for r in out:
    print(f"{r['variant']:46} mean {r['mean']:+5.2f} (t {r['t']:+6.1f})  p95 {r['p95']:+5.1f}  p99 {r['p99']:+6.1f}  worst-5% {r['es95']:+6.1f}  chased {r['chased']:.3f}  re-posts {r['mean_reposts']}")
