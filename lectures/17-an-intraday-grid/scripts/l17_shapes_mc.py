"""Lecture 17 §4: which size profile wins in which regime, on simulated prices where the regime is known. The tape simulator of l17_grid run on
simulated one-second paths (the same price as the highest buyer, lowest seller and last price of each second, so a level fills when the path crosses it).
Regimes, each on a random walk with 3% daily volatility: none; swings (a reverting part of 20 bp, half-life 10 min); runs (20% of the time in run
episodes of 30 min on average with a hidden drift, half-life 10 min, as in l17_mc_runs); large jumps (2 a day, 120 bp, variance matched as in l17_mc);
trend days (a drift for the whole day, 2% on average). Grid: 8 levels a side, steps 25 and 50 bp, stop + restart, daily close, no costs.
300 days per regime, in chunks of 50 days. Output: gross result per day, % of capital, by regime, shape and step."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from scipy.signal import lfilter
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import l17_grid as g

T, SIG, A = 86_400, 0.03, np.exp(-np.log(2) / 600)
SHAPES = sys.argv[1:] or ["uniform", "V-shaped", "bell-shaped", "bimodal"]; STEPS = [25, 50]; N = 8; DAYS, CHUNK = 300, 50


def paths(regime, D, rng):
    sig_s = SIG / np.sqrt(T)
    if regime == "large jumps": sig_s = np.sqrt(SIG ** 2 - 2 * 0.012 ** 2) / np.sqrt(T)
    x = np.cumsum(rng.standard_normal((D, T)) * sig_s, axis=1)
    if regime == "swings":
        x += lfilter([0.002 * np.sqrt(1 - A * A)], [1, -A], rng.standard_normal((D, T)), axis=1)
    if regime == "runs":
        run = np.zeros((D, T), bool); p_out = 1 / 1800; p_in = p_out * 0.2 / 0.8
        for d in range(D):
            t, on = 0, rng.random() < 0.2
            while t < T:
                L = rng.geometric(p_out if on else p_in); run[d, t:t + L] = on; t += L; on = not on
        drift = lfilter([1.0], [1, -A], 7e-6 * np.sqrt(1 - A * A) * rng.standard_normal((D, T)) * run, axis=1)
        x += np.cumsum(drift, axis=1)
    if regime == "large jumps":
        for d in range(D):
            k = rng.poisson(2); at = rng.integers(0, T, k)
            for a in at: x[d, a:] += 0.012 * rng.standard_normal()
    if regime == "trend days":
        x += (rng.standard_normal(D)[:, None] * 0.02) * (np.arange(T)[None, :] / T)
    return 1.0 + x


rows = []
for regime in ("random walk", "swings", "runs", "large jumps", "trend days"):
    rng = np.random.default_rng(17)
    for c in range(DAYS // CHUNK):
        P = paths(regime, CHUNK, rng).ravel()
        s = (np.arange(CHUNK * T, dtype=np.int64) + (c * CHUNK + 1) * T)
        data = (s, P, P, P, np.array([0], dtype=np.int64), np.array([0.0]))
        for st in STEPS:
            for sh in SHAPES:
                r = g.run(data, st, n=N, maker=0.0, taker=0.0, sizes=sh)
                rows.append(r.select("gross", "trips_income", "inventory").with_columns(pl.lit(regime).alias("regime"), pl.lit(st).alias("step"), pl.lit(sh).alias("shape")))
        del P, s, data
    print(regime, "done", flush=True)
R = pl.concat(rows)
out = R.group_by("regime", "step", "shape").agg(pl.col("gross").mean().alias("gross"), (pl.col("gross").std() / pl.len().sqrt()).alias("se"),
                                                pl.col("trips_income").mean(), pl.col("inventory").mean(), pl.len().alias("days"))
J = L17_RESULTS / "l17_shapes_mc.json"
old = [r for r in (json.loads(J.read_text()) if J.exists() else []) if r["shape"] not in SHAPES]   # keep the other shapes
J.write_text(json.dumps(old + out.to_dicts(), indent=1))
pl.Config.set_tbl_rows(50); pl.Config.set_tbl_width_chars(200); pl.Config.set_float_precision(3)
print(out.sort("step", "regime", "shape"))
