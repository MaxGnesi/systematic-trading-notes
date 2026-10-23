"""Lecture 14 §6: the bias of the duration measure (range-bar count x R^2 / 2), taken apart.
1. Simulation, where the truth is known: a random walk in steps of 0.1 s, read once a second, 48 bars a day; then the market's features added one at
   a time (busy and quiet hours, fat-tailed moves, a component that turns back over about ten minutes, the clock's averaged price). Truth: variance
   from one-minute returns, as on the tape.
2. The tape: the five-year ratio to one-minute realised variance, raw and corrected for discrete sampling (R -> R + 2*0.5826*s, s the one-second
   move implied by the count itself; Broadie, Glasserman and Kou's shift, applied to both ends of a range)."""
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
import tape, bars

N = 86400 * 10; DAYS = 30; B2 = 2 * 0.5826
HOURS = np.repeat(np.array([0.6, 0.5, 0.45, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.0, 1.0, 1.1, 1.4, 2.0, 1.8, 1.5, 1.3, 1.1, 1.0, 0.9, 0.8, 0.7, 0.65]), N // 24)


@njit(cache=True)
def fading(n, phi, sd, seed):
    np.random.seed(seed); e = np.zeros(n)
    for i in range(1, n): e[i] = phi * e[i - 1] + np.random.randn() * sd
    return e


def simulate(features, seed, rng):
    z = rng.standard_t(3, N) / np.sqrt(3) if "fat tails" in features else rng.standard_normal(N)
    w = np.sqrt(HOURS / HOURS.mean()) if "hours" in features else 1.0
    x = np.cumsum(z * w)
    if "turning back" in features: x = x + fading(N, np.exp(-1 / (10 * 600)), 3.0, seed)
    return x / np.sqrt(np.sum(np.diff(x[::600]) ** 2)) * 0.03                  # true variance from one-minute returns: 0.03^2


R = {"simulation": {}}
rng = np.random.default_rng(2)
STEPS = [("a random walk", ()), ("+ busy and quiet hours", ("hours",)), ("+ fat-tailed moves", ("hours", "fat tails")),
         ("+ turning back over minutes, averaged price", ("hours", "fat tails", "turning back", "averaged"))]
for lab, feat in STEPS:
    out = []
    for d in range(DAYS):
        x = simulate(feat, d, rng); tv = 0.03 ** 2
        y = x[: len(x) // 10 * 10].reshape(-1, 10).mean(1) if "averaged" in feat else x[::10]   # one price per second
        Rr = np.sqrt(tv / 48); out.append(len(bars._range_ends(y, Rr)) * Rr ** 2 / 2 / tv)
    R["simulation"][lab] = round(float(np.mean(out)), 3); print(lab, R["simulation"][lab], flush=True)

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
th = bars.thresholds("BTCUSDT").select("day", pl.col("range").alias("R"))
rb = pl.scan_parquet(sorted(bars.bars_dir("BTCUSDT", "range").glob("*.parquet"))).select("end_ms").collect()
cnt = rb.group_by(pl.from_epoch("end_ms", time_unit="ms").dt.date().alias("day")).len()
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time").with_columns(pl.col("close").log().diff().alias("r"), pl.col("time").dt.date().alias("day"))
rv = m1.group_by("day").agg((pl.col("r") ** 2).sum().alias("rv"), pl.len().alias("n")).filter(pl.col("n") == 1440)
x = cnt.join(th, on="day").join(rv, on="day").sort("day")
n = x["len"].to_numpy().astype(float); Rd = x["R"].to_numpy(); RV = x["rv"].to_numpy()
s = np.sqrt((n + 0.5) / 2) * Rd / (np.sqrt(86400.0) - B2 * np.sqrt((n + 0.5) / 2))
raw = n * Rd ** 2 / 2 / RV; corr = (n + 0.5) * (Rd + B2 * s) ** 2 / 2 / RV
yr = x["day"].dt.year().to_numpy()
R["tape"] = dict(raw_median=round(float(np.median(raw)), 3), raw_p10=round(float(np.quantile(raw, .1)), 2), raw_p90=round(float(np.quantile(raw, .9)), 2),
                 corrected_median=round(float(np.median(corr)), 3), corrected_by_year={int(y): round(float(np.median(corr[yr == y])), 3) for y in np.unique(yr)})
(L14_RESULTS / "l14_duration_sim.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R["tape"], indent=1))
