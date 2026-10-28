"""Lecture 17: Monte Carlo check of the core claim. On a price with no pattern (a martingale) a grid earns nothing before costs, with or without jumps.
One simulated day = 86,400 one-second steps of an arithmetic random walk (price starts at 1, daily volatility 3%, so drift-free by construction).
The grid: classic two-sided paired grid, uniform size (one unit per level), step s, n levels per side. In paired form its position is
-(r - c)/s, where r is the last level crossed: the price falling to r - s buys one unit at r - s, rising to r + s sells one at r + s.
Resting orders fill at their own level even if the price jumps through it; stops and the daily close fill at the market price.
Variants: hold at the cap (no stop) / stop one step beyond the last level, close all and restart at the price. Controls: a reverting
component (the grid should earn) and trend days (the grid should lose). Output: profit per day in bp of the starting price, per unit of size."""
import sys, json
from pathlib import Path
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
import numpy as np
from numba import njit

N_DAYS, T, SIG = 1000, 86_400, 0.03


@njit(cache=True)
def day(seed, step, n, stop, lam, jsd, ou_sd, hl_s, drift_sd):
    np.random.seed(seed)
    jump_var = lam * jsd * jsd
    sig_s = np.sqrt(max(SIG * SIG - jump_var, 0.0) / T)
    mu = np.random.normal() * drift_sd / T                       # trend day: a constant drift for the whole day (control)
    a = np.exp(-np.log(2.0) / hl_s) if hl_s > 0 else 0.0
    ou_e = ou_sd * np.sqrt(1 - a * a)
    w, y = 1.0, 0.0
    r, q, cash = 1.0, 0, 0.0
    trips, gap, stops = 0, 0.0, 0
    for t in range(T):
        w += mu + sig_s * np.random.normal()
        if lam > 0 and np.random.random() < lam / T:
            w += jsd * np.random.normal()
        if ou_sd > 0:
            y = a * y + ou_e * np.random.normal()
        p = w + y
        while p <= r - step:                                     # buy levels crossed (possibly several in one jump)
            if q >= n:
                if stop:
                    cash += q * p; q = 0; r = p; stops += 1      # ladder broken: close all at market, restart at the price
                break
            r -= step; q += 1; cash -= r; gap += r - p           # resting buy fills at its level; gap = paid above the market
            if q <= 0: trips += 1                                # this buy closed a short: one round trip
        while p >= r + step:
            if q <= -n:
                if stop:
                    cash += q * p; q = 0; r = p; stops += 1
                break
            r += step; q -= 1; cash += r; gap += p - r
            if q >= 0: trips += 1
    cash += q * p                                                # daily close at market
    return cash, trips, gap, stops


SCEN = {"random walk":               dict(lam=0.0, jsd=0.0, ou_sd=0.0, hl_s=0.0, drift_sd=0.0),
        "random walk + small jumps": dict(lam=10.0, jsd=0.004, ou_sd=0.0, hl_s=0.0, drift_sd=0.0),   # 10 a day, 40 bp: 18% of variance
        "random walk + large jumps": dict(lam=2.0, jsd=0.012, ou_sd=0.0, hl_s=0.0, drift_sd=0.0),    # 2 a day, 120 bp: 32% of variance
        "control: reverting part":   dict(lam=0.0, jsd=0.0, ou_sd=0.002, hl_s=600.0, drift_sd=0.0),  # 20 bp wobble, half-life 10 min
        "control: trend days":       dict(lam=0.0, jsd=0.0, ou_sd=0.0, hl_s=0.0, drift_sd=0.02)}     # daily drift sd 2%
if __name__ == "__main__":
    out = {}
    for step in (0.0025, 0.005):
        for stop in (False, True):
            for name, kw in SCEN.items():
                res = np.array([day(1000 + i, step, 5, stop, **kw) for i in range(N_DAYS)])
                pnl = res[:, 0] * 1e4
                m, se = pnl.mean(), pnl.std(ddof=1) / np.sqrt(N_DAYS)
                sk = ((pnl - m) ** 3).mean() / pnl.std() ** 3
                key = f"step {step*1e4:.0f} bp | {'stop+restart' if stop else 'hold at cap'} | {name}"
                out[key] = dict(mean_bp=m, se=se, t=m / se, skew=sk, worst1pct=np.percentile(pnl, 1), trips=res[:, 1].mean(),
                                gap_bp=res[:, 2].mean() * 1e4, stops=res[:, 3].mean(),
                                sum_se=(pnl + res[:, 2] * 1e4).std(ddof=1) / np.sqrt(N_DAYS))          # profit + gap: what the path's pattern earns
                o = out[key]
                print(f"{key:62s} mean {m:7.2f} bp (t {m/se:5.1f})  skew {sk:5.2f}  worst 1% {o['worst1pct']:7.1f}  trips {o['trips']:5.1f}  gap {o['gap_bp']:6.2f}  stops {o['stops']:.2f}")
    (L17_RESULTS / "l17_mc.json").write_text(json.dumps(out, indent=1))
