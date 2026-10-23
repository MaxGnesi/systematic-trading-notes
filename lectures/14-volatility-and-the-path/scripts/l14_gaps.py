"""Lecture 14 §4: what the path does at a level, measured with the right side of the book.
Levels every d below each day's open (and above, mirrored), on the price tick. For each first visit of a level:
- a sell stop at the level: triggered by the first trade at or below it (either side); filled at the following sell-aggressor trades:
  gap = level - first sell-aggressor price after the trigger, and the volume-weighted price of the next $1 million sold;
- a resting buy at the level: until the price trades a full step above it again, did sellers trade below it (filled for sure),
  only at it (queue decides), or did only buyers reach it (no fill)?
Mirrored for buy stops and resting sells above the open. Calm days: 120 random days of the calmer half; volatile: the most volatile 10%."""
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from numba import njit
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM; TICK = 0.1


@njit(cache=True)
def visits(p, sell, usd, levels, d):
    """For each level below the start: [gap_bp, vwap_gap_bp(1M), class] with class 0 through, 1 at only, 2 wrong side only, -1 never reached."""
    out = np.full((len(levels), 3), np.nan); n = len(p)
    for j in range(len(levels)):
        L = levels[j]; i = 0
        while i < n and p[i] > L: i += 1
        if i == n:
            out[j, 2] = -1; continue
        k = i                                                      # the trigger; first sell-aggressor trade from here
        while k < n and not sell[k]: k += 1
        if k < n:
            out[j, 0] = (L - p[k]) / L * 1e4
            s = 0.0; v = 0.0; m = k
            while m < n and s < 1e6:
                if sell[m]: s += usd[m]; v += usd[m] * p[m]
                m += 1
            if s > 0: out[j, 1] = (L - v / s) / L * 1e4
        up = L * (1 + d); through = False; at = False; m = i
        while m < n and p[m] < up:
            if sell[m]:
                if p[m] < L - 1e-9: through = True
                elif abs(p[m] - L) < 1e-9: at = True
            m += 1
        out[j, 2] = 0 if through else (1 if at else 2)
    return out


def day_trades(d0):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    return (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
              .select("price", "quantity", "is_buyer_maker").collect())


days = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).select("day", "rv_60").collect().drop_nulls().sort("day")
rv = days["rv_60"].to_numpy(); dl = days["day"].to_list()
calm_all = [dl[i] for i in np.where(rv <= np.percentile(rv, 50))[0]]; wild = [dl[i] for i in np.where(rv >= np.percentile(rv, 90))[0]]
calm = [calm_all[i] for i in sorted(np.random.default_rng(0).choice(len(calm_all), 120, replace=False))]
R = {}
for lab, sel in (("calm", calm), ("volatile", wild)):
    acc = {bp: [] for bp in (20, 50, 100)}
    for d0 in sel:
        tape.wait_for_memory(1.5)
        t = day_trades(d0)
        if t.height == 0: continue
        p = t["price"].to_numpy(); usd = (t["price"] * t["quantity"]).to_numpy(); sellf = t["is_buyer_maker"].to_numpy()   # buyer is maker = seller aggressed
        for bp in acc:
            d = bp / 1e4; o = p[0]
            dn = np.round(o * np.exp(-d * np.arange(1, 200)) / TICK) * TICK
            up = np.round(o * np.exp(d * np.arange(1, 200)) / TICK) * TICK
            a = visits(p, sellf, usd, dn, d)                                    # sell stops / resting buys below
            b = visits(-p, ~sellf, usd, -up, -d)                                # mirrored: buy stops / resting sells above (prices negated)
            b[:, 0:2] *= -1                                                     # gap measured as fill above the level
            for x in (a, b):
                x = x[x[:, 2] >= 0]; acc[bp].append(x)
    R[lab] = {}
    for bp, xs in acc.items():
        x = np.vstack(xs); g = x[:, 0][np.isfinite(x[:, 0])]; v = x[:, 1][np.isfinite(x[:, 1])]; c = x[:, 2]
        R[lab][bp] = dict(levels=int(len(x)), gap_median_bp=round(float(np.median(g)), 2), gap_p90=round(float(np.quantile(g, .9)), 2), gap_p99=round(float(np.quantile(g, .99)), 1),
                          gap_over_10bp=round(float((g > 10).mean()), 4), vwap1m_median=round(float(np.median(v)), 2), vwap1m_p90=round(float(np.quantile(v, .9)), 1),
                          vwap1m_p99=round(float(np.quantile(v, .99)), 1), vwap1m_p999=round(float(np.quantile(v, .999)), 1), vwap1m_max=round(float(v.max()), 1), gap_p999=round(float(np.quantile(g, .999)), 1), gap_max=round(float(g.max()), 1), through=round(float((c == 0).mean()), 3), at_only=round(float((c == 1).mean()), 3),
                          wrong_side_only=round(float((c == 2).mean()), 3))
        print(lab, bp, R[lab][bp], flush=True)
(L14_RESULTS / "l14_gaps.json").write_text(json.dumps(R, indent=1, default=str))
