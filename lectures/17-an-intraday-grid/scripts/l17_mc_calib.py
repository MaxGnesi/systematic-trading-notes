"""Lecture 17: run-episode Monte Carlo calibrated to the tape, and the value of switching the grid off in runs.
Model as l17_mc_runs.py: calm state = random walk + reverting part (half-life 10 min); run episodes (mean 30 min) with a hidden drift (half-life 10 min).
Calibration, for each share of time in runs: the reverting part is sized so that the variance ratio of 1-hour to 1-minute returns is 0.90
(Lecture 14 §3, tape), then every component is scaled together so that daily volatility is 3% (the ratio is unchanged by the scaling).
So every model below has the tape's volatility and the tape's average reversion; they differ only in how it is split between swing and run time.
Grid: paired, uniform, n = 5, step 25 bp, stop + restart, daily close, no costs. Switch: when a run is detected the grid closes at market and
pauses; when the run's end is detected it restarts at the price. Detection: perfect (lag 0) or the true state seen with a lag of 5, 15, 30 min."""
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

T, RUN_LEN, HL = 86_400, 1800.0, 600.0
VR_TAPE, VOL_TAPE = 0.90, 0.03


@njit(cache=True)
def day(seed, step, n, sig_d, p_run, drift_sd, ou_sd, switch, lag):
    np.random.seed(seed)
    sig_s = sig_d / np.sqrt(T)
    p_exit = 1.0 / RUN_LEN
    p_enter = p_exit * p_run / (1.0 - p_run)
    a = np.exp(-np.log(2.0) / HL); b = drift_sd * np.sqrt(1 - a * a); e = ou_sd * np.sqrt(1 - a * a)
    run = np.random.random() < p_run
    prev, t_chg = run, -1e9
    w, d, y = 1.0, 0.0, 0.0
    r, q, cash, on, off_time = 1.0, 0, 0.0, True, 0
    m1 = np.zeros(1440)
    for t in range(T):
        if run:
            if np.random.random() < p_exit: prev = run; run = False; t_chg = t
        elif np.random.random() < p_enter: prev = run; run = True; t_chg = t
        d = a * d + b * np.random.normal() if run else a * d
        w += d + sig_s * np.random.normal()
        if not run: y = a * y + e * np.random.normal()
        p = w + y
        if t % 60 == 59: m1[t // 60] = p
        if switch:
            seen = run if t - t_chg >= lag else prev                 # the state as it is known `lag` seconds later
            if on and seen:
                cash += q * p; q = 0; on = False                       # run detected: close at market, pause
            elif not on and not seen:
                on = True; r = p                                       # run over: restart centred on the price
            if not on:
                off_time += 1; continue
        while p <= r - step:
            if q >= n:
                cash += q * p; q = 0; r = p; break
            r -= step; q += 1; cash -= r
        while p >= r + step:
            if q <= -n:
                cash += q * p; q = 0; r = p; break
            r += step; q -= 1; cash += r
    cash += q * p
    r1 = np.diff(m1); r60 = m1[59::60][1:] - m1[59::60][:-1]
    return cash, (r1 ** 2).mean(), (r60 ** 2).mean(), m1[-1] - 1.0, off_time / T


def stats(n_days, seed0, sig_d, p_run, drift_sd, ou_sd, switch=False, lag=0, step=0.0025):
    res = np.array([day(seed0 + i, step, 5, sig_d, p_run, drift_sd, ou_sd, switch, lag) for i in range(n_days)])
    return res, res[:, 2].mean() / res[:, 1].mean() / 60, res[:, 3].std()


def calibrate(p_run, drift_rel=0.07):
    """drift_rel: the run drift's sd per second relative to the random walk's per-second sd (fixed run strength).
    Bisect the reverting part for VR = 0.90, then scale everything for 3% daily volatility."""
    sig = VOL_TAPE; drift = drift_rel * sig / np.sqrt(T)
    lo, hi = 0.0, 0.05
    for _ in range(14):
        mid = (lo + hi) / 2
        _, vr, _ = stats(300, 7000, sig, p_run, drift, mid)
        lo, hi = (mid, hi) if vr > VR_TAPE else (lo, mid)
    ou = (lo + hi) / 2
    _, vr, vol = stats(600, 8000, sig, p_run, drift, ou)
    k = VOL_TAPE / vol
    return dict(p_run=p_run, sig=sig * k, drift=drift * k, ou=ou * k, vr=vr)


if __name__ == "__main__":
    out = []
    for p in (0.0, 0.02, 0.05, 0.10, 0.20):
        c = calibrate(p)
        res, vr, vol = stats(1000, 1, c["sig"], p, c["drift"], c["ou"])
        row = dict(**c, vr_check=vr, vol_check=vol * 100, grid=res[:, 0].mean() * 1e4,
                   t=res[:, 0].mean() / res[:, 0].std(ddof=1) * np.sqrt(len(res)), worst1=np.percentile(res[:, 0], 1) * 1e4)
        print(f"runs {p:4.0%} | reverting part {c['ou']*1e4:5.1f} bp | VR {vr:.2f} | vol {vol*100:.2f}% | grid always on {row['grid']:7.1f} bp/day (t {row['t']:5.1f}) worst 1% {row['worst1']:6.0f}")
        if p > 0:
            for lag in (0, 300, 900, 1800):
                rs, _, _ = stats(1000, 1, c["sig"], p, c["drift"], c["ou"], True, lag)
                row[f"switch_{lag}"] = rs[:, 0].mean() * 1e4; row[f"switch_{lag}_t"] = rs[:, 0].mean() / rs[:, 0].std(ddof=1) * np.sqrt(len(rs))
                row[f"switch_{lag}_off"] = rs[:, 4].mean(); row[f"switch_{lag}_worst1"] = np.percentile(rs[:, 0], 1) * 1e4
                print(f"      switch, lag {lag//60:2d} min: {row[f'switch_{lag}']:7.1f} bp/day (t {row[f'switch_{lag}_t']:5.1f}), off {rs[:, 4].mean():.0%} of the time, worst 1% {row[f'switch_{lag}_worst1']:6.0f}")
        out.append(row)
    (L17_RESULTS / "l17_mc_calib.json").write_text(json.dumps(out, indent=1))
