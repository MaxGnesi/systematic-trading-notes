"""Lecture 15 §6: choosing the cut-off of a resting order, from the tick tape. Every 10th day from November 2021 to September 2026; a decision every 7th
minute, a buy and a mirrored sell. The order rests one tick ($0.10) or 2 bp inside the last trade price; filled when a later trade goes strictly through it;
if not filled by the cut-off (5 s, 10 s, 30 s, 1, 10, 60 min), it becomes a market (taker) order at the last trade price then. Cost against a market order
sent at the decision, in bp (positive = the resting order did worse): per cut-off the mean, the 95th and 99th percentile over all orders, the mean of the
worst 5%, the share chased and the 95th percentile among the chased."""
import json, sys, time
from datetime import date, datetime, timedelta, timezone
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

SYM = "BTCUSDT"
TAKER, MAKER, HALF, TICK = 5.0, 2.0, 0.04, 0.1
CUTS = {"5 s": 5_000, "10 s": 10_000, "30 s": 30_000, "1 min": 60_000, "10 min": 600_000, "60 min": 3_600_000}
DAYS = [date(2021, 11, 1) + timedelta(days=10 * k) for k in range(200) if date(2021, 11, 1) + timedelta(days=10 * k) <= date(2026, 9, 29)]


def day_trades(d):
    a = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000); b = a + 86_400_000 + 3_700_000
    fs = sorted({tape.source(SYM, x.strftime("%Y-%m")) for x in (d, d + timedelta(days=1))}); fs = [f for f in fs if Path(f).exists()]
    t = (pl.scan_parquet(fs).filter(pl.col("transact_time").is_between(a - 60_000, b)).select("transact_time", "price").collect().sort("transact_time"))
    return a, t["transact_time"].to_numpy(), t["price"].to_numpy()


rows = []; t0 = time.time()
for d in DAYS:
    tape.wait_for_memory(1.5)
    a, ts, px = day_trades(d)
    if len(ts) < 1000: continue
    dec = a + np.arange(0, 86_400_000, 7 * 60_000)
    k = np.searchsorted(ts, dec, side="right") - 1; ok = k >= 0; dec = dec[ok]; p0 = px[k[ok]]
    for side in (1, -1):
        for lab, off in (("1 tick", lambda p: TICK), ("2 bp", lambda p: p * 2e-4)):
            lim = p0 - side * off(p0)
            ft = first_through(ts, px, dec, lim, side, max(CUTS.values()))
            fill_cost = side * np.log(lim / p0) * 1e4 + MAKER
            for cl, T in CUTS.items():
                pT = px[np.searchsorted(ts, dec + T, side="right") - 1]
                filled = (ft >= 0) & (ft <= T)
                cost = np.where(filled, fill_cost, side * np.log(pT / p0) * 1e4 + TAKER + HALF) - (TAKER + HALF)
                rows.append(pl.DataFrame({"day": [str(d)] * len(dec), "side": side, "offset": lab, "cut": cl, "filled": filled, "cost": cost}))
    if len(rows) % 240 == 0: print(d, f"{time.time() - t0:.0f}s", tape.peak_private_gb(), "GB", flush=True)
X = pl.concat(rows)
out = []
for (off, cl), g in X.group_by("offset", "cut", maintain_order=True):
    c = g["cost"].to_numpy(); f = g["filled"].to_numpy(); q95, q99 = np.quantile(c, [0.95, 0.99]); worst = np.sort(c)[-max(1, len(c) // 20):]
    dm = g.group_by("day").agg(pl.col("cost").mean())["cost"].to_numpy()
    out.append(dict(offset=off, cut=cl, n=len(c), filled=round(float(f.mean()), 3), mean=round(float(c.mean()), 2), t=round(float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), 1),
                    p95=round(float(q95), 1), p99=round(float(q99), 1), es95=round(float(worst.mean()), 1),
                    chased=round(float(1 - f.mean()), 3), chased_p95=round(float(np.quantile(c[~f], 0.95)), 1) if (~f).any() else None))
(L15_RESULTS / "l15_resting_tail.json").write_text(json.dumps(out, indent=1))
print("days", X["day"].n_unique(), "decisions per side and offset", X.filter((pl.col("side") == 1) & (pl.col("offset") == "1 tick") & (pl.col("cut") == "1 min")).height)
for r in out:
    print(f"{r['offset']:7}{r['cut']:7} filled {r['filled']:.2f}  mean {r['mean']:+5.2f} (t {r['t']:+6.1f})  p95 {r['p95']:+6.1f}  p99 {r['p99']:+6.1f}  worst-5% mean {r['es95']:+6.1f}  "
          f"chased {r['chased']:.2f}  chased p95 {r['chased_p95']}")
