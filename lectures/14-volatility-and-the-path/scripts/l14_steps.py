"""Lecture 14 §3: after the price moves one step of size d, does it move another step the same way (continue) or turn back?
A ladder of levels d apart in log price, over five years of one-minute closes; a random walk continues half the time."""
import json, sys
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

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"


@njit(cache=True)
def steps(lp, d):
    """The sequence of steps of size d (+1 up, -1 down) and the minute at which each was completed."""
    out = np.empty(len(lp) * 2, np.int8); idx = np.empty(len(lp) * 2, np.int64); k = 0; ref = lp[0]
    for i in range(1, len(lp)):
        while lp[i] >= ref + d:
            ref += d; out[k] = 1; idx[k] = i; k += 1
        while lp[i] <= ref - d:
            ref -= d; out[k] = -1; idx[k] = i; k += 1
    return out[:k], idx[:k]


if __name__ == "__main__":
    m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
    lp = np.log(m1["close"].to_numpy()); yr = m1["time"].dt.year().to_numpy()
    R = {}
    for bp in (10, 20, 50, 100, 200, 500):
        s, ix = steps(lp, bp / 1e4); c = s[1:] == s[:-1]; y = yr[ix[1:]]
        R[bp] = dict(steps=int(len(s)), cont=round(float(c.mean()), 4), se=round(float(np.sqrt(0.25 / len(c))), 4),
                     by_year={int(v): round(float(c[y == v].mean()), 3) for v in np.unique(y)})
        print(bp, "bp", R[bp], flush=True)
    (L14_RESULTS / "l14_steps.json").write_text(json.dumps(R, indent=1))
