"""Lecture 16: sizing by the risk over the rule's own holding period. For each speed (fast span d days), the variance of the next d days is forecast by
a HAR on one-minute realised variance (last hour, last day, last week), fitted on 2021-2024, smoothed over a day as in l16_buildup.py; compared with the
plain rule (past 36 days' volatility) and with the next-day forecast. Market orders, funding, buffer as in l16_buildup.py."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l16_buildup as B                                                           # data, forecasts, simulate and stats; its own runs are repeated on import

c = np.r_[0.0, np.cumsum(B.rv)]; n = B.n


def horizon_sigma(h):
    fwd = np.full(n, np.nan); fwd[:-h] = (c[h + 1:] - c[1:-h]) / h               # mean hourly rv over the next h hours
    y = np.log(fwd); ok = np.all(np.isfinite(B.X), axis=1) & np.isfinite(y) & B.live
    b = np.linalg.lstsq(B.X[ok & B.IS], y[ok & B.IS], rcond=None)[0]; corr = np.mean(np.exp(y[ok & B.IS] - B.X[ok & B.IS] @ b))
    s = np.sqrt(np.exp(B.X @ b) * corr * B.PY)
    return np.sqrt(pl.Series(s ** 2).fill_nan(None).ewm_mean(span=24, min_samples=1, ignore_nulls=True).to_numpy().astype(float))


R = {}
SETS = {f"{fd} d": [fd] for fd in (0.5, 1, 2, 3, 5, 8, 13, 21)}; SETS["blend 1-2-3 d"] = [1, 2, 3]
for name, fds in SETS.items():
    fc = B.forecast(B.dp_sd, fds); R[name] = {}; h = int(round(24 * sum(fds) / len(fds)))           # holding horizon: the (mean) fast span
    for lab, sig in (("plain: past 36 days", B.sig_plain), ("next-day forecast, raw", B.sig_har), ("next-day forecast", B.sig_smooth), ("holding-period forecast", horizon_sigma(h))):
        net, parts = B.simulate(sig, B.TAKER + B.HALF, False, fc=fc)
        R[name][lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
(L16_RESULTS / "l16_horizon.json").write_text(json.dumps(R, indent=1))
print("\nSharpe 2021-2024 / 2025-2026, worst day (typical daily moves), monthly risk spread, costs")
for k, v in R.items():
    print(f"{k:>6} | " + " | ".join(f"{lab[:18]:18} {x['2021-2024']['sharpe']:+5.2f}/{x['2025-2026']['sharpe']:+5.2f} wd {x['2021-2024']['worst_day']:+5.1f} cv {x['2021-2024']['vol_cv']:.2f} c {x['2021-2024']['cost']:4.1%}" for lab, x in v.items()))
