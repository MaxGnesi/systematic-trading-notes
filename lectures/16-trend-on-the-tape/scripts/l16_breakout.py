"""Lecture 16: a breakout rule on hourly closes against dollar bars (the check of §3 with a rule that uses price levels). Turtle breakout as in Lecture 11:
long when the close is above the highest close of the previous N bars, short below the lowest; a long is closed below the lowest close of the previous
N/2 bars, a short above the highest. A: on hourly closes, N = days x 24. B: on dollar bars, N = days x 48 (about the same span on average), the state of
the last finished bar read at each hourly close. Decisions hourly; plain sizing, buffer, market orders and funding of l16_buildup.py."""
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
bt, bp = DB["end_ms"].to_numpy(), DB["close"].to_numpy()
k = np.searchsorted(bt, B.H["t_close"].cast(pl.Datetime("ms")).cast(pl.Int64).to_numpy(), side="right") - 1


def breakout(p, n):
    m = max(n // 2, 2); s = pl.Series(p)
    hi, lo = s.rolling_max(n).shift(1).to_numpy(), s.rolling_min(n).shift(1).to_numpy()
    xhi, xlo = s.rolling_max(m).shift(1).to_numpy(), s.rolling_min(m).shift(1).to_numpy()
    out = np.zeros(len(p)); st = 0.0
    for i in range(len(p)):
        if np.isfinite(hi[i]):
            if st == 0:
                if p[i] > hi[i]: st = 1.0
                elif p[i] < lo[i]: st = -1.0
            elif st == 1 and p[i] < xlo[i]: st = 0.0
            elif st == -1 and p[i] > xhi[i]: st = 0.0
        out[i] = st
    return out


SETS = {f"{d} d": [d] for d in (1, 2, 3, 5, 8, 13)}; SETS["blend 1-2-3 d"] = [1, 2, 3]
R = {}
for name, ds in SETS.items():
    sA = sum(breakout(B.p, d * 24) for d in ds) / len(ds)
    sBbar = sum(breakout(bp, d * 48) for d in ds) / len(ds); sB = np.where(k >= 0, sBbar[np.maximum(k, 0)], 0.0)
    R[name] = {}
    for lab, st in (("A hourly closes", sA), ("B dollar bars", sB)):
        net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=st)
        R[name][lab] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS), "share_in_market": round(float((st != 0).mean()), 2)}
(L16_RESULTS / "l16_breakout.json").write_text(json.dumps(R, indent=1))
print("breakout: Sharpe 2021-2024 / 2025-2026, costs 2021-2024")
for name, v in R.items():
    print(f"{name:>14} | " + " | ".join(f"{lab}: {x['2021-2024']['sharpe']:+.2f}/{x['2025-2026']['sharpe']:+.2f} c {x['2021-2024']['cost']:.1%}" for lab, x in v.items()))
