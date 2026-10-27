"""Lecture 16: plugging information from dollar bars into the hourly rule. Decisions stay at every hourly close, with the plain sizing, market orders,
buffer and funding of l16_buildup.py; only the trend measure changes. A: EWMAC on hourly closes. B: EWMAC on dollar bars (Lecture 13's bars, about 48 a
day; spans in bars = days x 48), its latest value read at the hourly close. C: dollar-bar prices averaged with weights that fade by elapsed time (an EMA
for irregular samples, weight of each step 1 - exp(-elapsed / tau), tau = span / 2 in calendar time), read at the hourly close. Each forecast is
divided by the volatility of its own price changes and scaled to an average size of 1 by its own past."""
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
import tape
import l16_buildup as B


DB = pl.concat([pl.read_parquet(f, columns=["end_ms", "close"]) for f in sorted((tape.ROOT / "interim" / "bars" / "BTCUSDT" / "dollar").glob("*.parquet"))]).sort("end_ms")
bt = DB["end_ms"].to_numpy(); bp = DB["close"].to_numpy(); PER_DAY = 48
hour_ms = B.H["t_close"].cast(pl.Datetime("ms")).cast(pl.Int64).to_numpy()
k = np.searchsorted(bt, hour_ms, side="right") - 1                               # latest dollar bar finished by each hourly close


def scale(raw):
    ok = np.isfinite(raw); return raw / (np.cumsum(np.where(ok, np.abs(raw), 0.0)) / np.maximum(np.cumsum(ok), 1))


def ema_time(x, t_ms, tau_ms):
    out = np.empty(len(x)); out[0] = x[0]
    a = 1 - np.exp(-np.diff(t_ms) / tau_ms)
    for i in range(1, len(x)): out[i] = out[i - 1] + a[i - 1] * (x[i] - out[i - 1])
    return out


sd_bar = pl.Series(np.r_[0.0, np.diff(bp)] ** 2).ewm_mean(span=36 * PER_DAY, min_samples=7 * PER_DAY).sqrt().to_numpy()
R = {}
SETS = {f"{fd} d": [fd] for fd in (0.5, 1, 2, 3, 5, 8, 13, 21)}; SETS["blend 1-2-3 d"] = [1, 2, 3]


def blend(raws):
    fcs = [scale(x) for x in raws]; return scale(sum(fcs) / len(fcs))


for name, fds in SETS.items():
    fd = fds[0]
    fA = B.forecast(B.dp_sd, fds)
    rB, rC = [], []
    for f in fds:
        span = f * PER_DAY
        rB.append((pl.Series(bp).ewm_mean(span=span, adjust=False).to_numpy() - pl.Series(bp).ewm_mean(span=4 * span, adjust=False).to_numpy()) / sd_bar)
        tau = f * 86_400_000 / 2                                                 # an EMA of span s has a centre of mass about s / 2 back
        rC.append((ema_time(bp, bt, tau) - ema_time(bp, bt, 4 * tau)) / sd_bar)
    sB, sC = blend(rB), blend(rC)
    fB = np.where(k >= 0, sB[np.maximum(k, 0)], np.nan); fC = np.where(k >= 0, sC[np.maximum(k, 0)], np.nan)
    R[name] = {}
    for lab, fc in (("A time bars", fA), ("B dollar bars, per bar", fB), ("C dollar bars, decay by time", fC)):
        net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=fc)
        R[name][lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
        R[name][lab]["corr_with_A"] = round(float(np.corrcoef(np.nan_to_num(fc[B.live]), np.nan_to_num(fA[B.live]))[0, 1]), 3)
(L16_RESULTS / "l16_plugin.json").write_text(json.dumps(R, indent=1))
print("\nSharpe 2021-2024 / 2025-2026, costs 2021-2024, correlation of the forecast with A")
for kk, v in R.items():
    print(f"{kk:>6} | " + " | ".join(f"{lab[:26]:26} {x['2021-2024']['sharpe']:+5.2f}/{x['2025-2026']['sharpe']:+5.2f} c {x['2021-2024']['cost']:4.1%} r {x['corr_with_A']:.2f}" for lab, x in v.items()))
