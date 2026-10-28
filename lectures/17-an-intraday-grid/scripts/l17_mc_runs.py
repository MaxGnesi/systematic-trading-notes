"""Lecture 17: Monte Carlo with run episodes (spikes in autocorrelation). Most of the time the price is a random walk; it switches into run
episodes (mean length 30 min) in which a hidden drift with a 10-minute half-life makes returns positively autocorrelated, and back.
Optionally the calm state has a reverting part (20 bp wobble, half-life 10 min). Varied: the share of time spent in runs.
Measured on each simulated path: the variance ratio of 1-hour to 1-minute returns (1 = random walk, above 1 = runs, below = swings),
realised daily volatility, and the grid's profit before costs (paired uniform grid, n = 5, step 25 bp, stop + restart, daily close)."""
import json
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
def day(seed, step, n, p_run, run_len_s, drift_sd, hl_drift, ou_sd, hl_ou):
    np.random.seed(seed)
    sig_s = SIG / np.sqrt(T)
    p_exit = 1.0 / run_len_s
    p_enter = p_exit * p_run / (1.0 - p_run) if p_run < 1 else 1.0
    a = np.exp(-np.log(2.0) / hl_drift); b = drift_sd * np.sqrt(1 - a * a)
    c = np.exp(-np.log(2.0) / hl_ou); e = ou_sd * np.sqrt(1 - c * c)
    run = np.random.random() < p_run
    w, d, y = 1.0, 0.0, 0.0
    r, q, cash, gap = 1.0, 0, 0.0, 0.0
    m1 = np.zeros(1440)
    for t in range(T):
        if run:
            if p_run < 1 and np.random.random() < p_exit: run = False
        elif np.random.random() < p_enter: run = True
        d = a * d + b * np.random.normal() if run else a * d       # drift decays away when the run ends
        w += d + sig_s * np.random.normal()
        if ou_sd > 0 and not run:
            y = c * y + e * np.random.normal()
        p = w + y
        if t % 60 == 59: m1[t // 60] = p
        while p <= r - step:
            if q >= n:
                cash += q * p; q = 0; r = p; break
            r -= step; q += 1; cash -= r; gap += r - p
        while p >= r + step:
            if q <= -n:
                cash += q * p; q = 0; r = p; break
            r += step; q -= 1; cash += r; gap += p - r
    cash += q * p
    r1 = np.diff(m1); r60 = m1[59::60][1:] - m1[59::60][:-1]
    return cash, gap, (r1 ** 2).sum(), (r60 ** 2).sum(), len(r1), len(r60), m1[-1] - 1.0


def run(p_run, ou_sd=0.0, drift_sd=7e-6, step=0.0025):
    res = np.array([day(5000 + i, step, 5, p_run, 1800.0, drift_sd, 600.0, ou_sd, 600.0) for i in range(N_DAYS)])
    pnl = res[:, 0] * 1e4
    vr = (res[:, 3].sum() / res[:, 5].sum()) / (res[:, 2].sum() / res[:, 4].sum()) / 60
    return dict(p_run=p_run, ou_sd=ou_sd, mean_bp=pnl.mean(), t=pnl.mean() / pnl.std(ddof=1) * np.sqrt(N_DAYS), vr=vr,
                vol_day=res[:, 6].std() * 100, gap_bp=res[:, 1].mean() * 1e4, worst1=np.percentile(pnl, 1))


if __name__ == "__main__":
    out = []
    for ou in (0.0, 0.002):
        for p in (0.0, 0.05, 0.1, 0.2, 0.35, 0.5):
            o = run(p, ou); out.append(o)
            print(f"calm state {'reverting' if ou else 'random walk':11s} | time in runs {p:4.0%} | VR(1h/1m) {o['vr']:.2f} | daily vol {o['vol_day']:.1f}% "
                  f"| grid {o['mean_bp']:7.1f} bp/day (t {o['t']:5.1f}) | gap {o['gap_bp']:5.1f} | worst 1% {o['worst1']:7.0f}")
    (L17_RESULTS / "l17_mc_runs.json").write_text(json.dumps(out, indent=1))
