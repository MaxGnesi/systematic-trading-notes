"""Lecture 14 §4: after a stop level is crossed, what did the sellers who followed get? For each first crossing of a level (levels every d
from each day's open, below and mirrored above): within 0.1, 0.5, 1, 2, 5 and 10 seconds of the trigger: the average and the worst price of the
sell-aggressor trades (bp below the level), the dollars they sold, and the drift (the last price of the window, below the level). Pooled into percentiles, calm and volatile days.
A stand-in for what a stop-market might get, not a fill: the order book at the trigger is not on the tape."""
import json, sys
from datetime import datetime, timezone
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
WIN = np.array([100, 500, 1000, 2000, 5000, 10000])                         # time windows after the trigger, milliseconds (short: depth, little drift)


@njit(cache=True)
def fan(p, ts, sell, usd, levels, win, sgn):
    """Per level and window after the trigger: average and worst price of the sellers who followed (bp below the level), and dollars they sold."""
    out = np.full((len(levels), len(win), 4), np.nan); n = len(p)
    for j in range(len(levels)):
        L = levels[j]; i = 0
        while i < n and p[i] > L: i += 1
        if i == n: continue
        for k in range(len(win)):
            s = 0.0; v = 0.0; worst = -1e9; m = i
            while m < n and ts[m] - ts[i] <= win[k]:
                if sell[m]:
                    s += usd[m]; v += usd[m] * p[m]; worst = max(worst, sgn * (L - p[m]) / L * 1e4)
                m += 1
            if s > 0: out[j, k, 0] = sgn * (L - v / s) / L * 1e4; out[j, k, 1] = worst; out[j, k, 2] = s
            out[j, k, 3] = sgn * (L - p[m - 1]) / L * 1e4                    # drift: the last price of the window, beyond the level
    return out


def day_trades(d0):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    return (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
              .select("transact_time", "price", "quantity", "is_buyer_maker").collect())


if __name__ == "__main__":
    days = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).select("day", "rv_60").collect().drop_nulls().sort("day")
    rv = days["rv_60"].to_numpy(); dl = days["day"].to_list()
    calm_all = [dl[i] for i in np.where(rv <= np.percentile(rv, 50))[0]]; wild = [dl[i] for i in np.where(rv >= np.percentile(rv, 90))[0]]
    calm = [calm_all[i] for i in sorted(np.random.default_rng(0).choice(len(calm_all), 120, replace=False))]
    R = {"windows_ms": WIN.tolist()}
    for lab, sel in (("calm", calm), ("volatile", wild)):
        acc = []
        for d0 in sel:
            tape.wait_for_memory(1.5)
            t = day_trades(d0)
            if t.height == 0: continue
            p = t["price"].to_numpy(); ts = t["transact_time"].to_numpy(); usd = (t["price"] * t["quantity"]).to_numpy(); sellf = t["is_buyer_maker"].to_numpy()
            for bp in (20, 50, 100):
                d = bp / 1e4; o = p[0]
                dn = np.round(o * np.exp(-d * np.arange(1, 200)) / TICK) * TICK; up = np.round(o * np.exp(d * np.arange(1, 200)) / TICK) * TICK
                acc.append(fan(p, ts, sellf, usd, dn, WIN, 1.0))
                acc.append(fan(-p, ts, ~sellf, usd, -up, WIN, -1.0))      # mirrored: buy stops above (prices negated, so the distance changes sign)
        A = np.concatenate(acc)
        np.save(tape.ROOT / "interim" / f"l14_stopfan_{lab}.npy", A)               # every trigger: [level, window, (average, worst, dollars, drift)]
        R[lab] = {}
        for k, w in enumerate(WIN):
            x = A[:, k, :]; x = x[np.isfinite(x[:, 0])]
            R[lab][f"{int(w)}ms"] = dict(n=int(len(x)), **{f"avg_bp_p{q}": round(float(np.quantile(x[:, 0], q / 100)), 2) for q in (50, 90, 99, 99.9)},
                                         **{f"worst_bp_p{q}": round(float(np.quantile(x[:, 1], q / 100)), 2) for q in (50, 80, 90, 95, 99, 99.9)}, worst_bp_max=round(float(x[:, 1].max()), 1),
                                         **{f"usd_p{q}": round(float(np.quantile(x[:, 2], q / 100))) for q in (10, 50, 90)},
                                         **{f"drift_bp_p{q}": round(float(np.quantile(x[:, 3], q / 100)), 2) for q in (50, 90, 99)})
        print(lab, json.dumps(R[lab]), flush=True)
    (L14_RESULTS / "l14_stopfan.json").write_text(json.dumps(R, indent=1))
