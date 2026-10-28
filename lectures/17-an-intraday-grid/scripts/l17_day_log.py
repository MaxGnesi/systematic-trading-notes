"""Lecture 17 §1: one day of the grid, fill by fill. A plain-Python copy of l17_grid.simulate (always on, no skew, stop + restart, daily close)
that logs every event, so the worked day can be followed step by step; its day totals are checked against the simulator."""
import sys
from pathlib import Path
import numpy as np, polars as pl
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


def log_day(data, date, step_bp=50, n=4, maker=2e-4, taker=5e-4):
    s, hb, ls, last, fs, fr = data
    d0 = int(np.datetime64(date, "D").astype(np.int64)); m = (s // 86400) == d0
    s, hb, ls, last = s[m], hb[m], ls[m], last[m]
    p0 = last[0]; step = step_bp * 1e-4 * p0; u = 1.0 / n / p0
    r = centre = p0; q = 0; cash = 0.0; fee_m = fee_t = fund = 0.0; trips = stops = 0; ev = []; fi = np.searchsorted(fs, s[0])
    Q = np.zeros(len(s)); C = np.zeros(len(s)); TR = np.zeros(len(s))          # per second: position, cash, round trips so far
    for k in range(len(s)):
        while fi < len(fs) and fs[fi] <= s[k]:
            fund -= q * u * last[k - 1 if k else k] * fr[fi]; fi += 1
        down = ls[k] == ls[k] and ls[k] < r - step; up = hb[k] == hb[k] and hb[k] > r + step
        if down and up:
            if last[k] < r: up = False
            else: down = False
        if down:
            while ls[k] < r - step:
                if q >= n:
                    cash += q * u * ls[k]; fee_t += q * u * ls[k] * taker; ev.append((s[k], "stop", ls[k], 0, centre)); q = 0; stops += 1
                    r = centre = last[k]; ev.append((s[k], "restart", r, 0, centre)); break
                r -= step; trips += q < 0; q += 1; cash -= u * r; fee_m += u * r * maker; ev.append((s[k], "buy", r, q, centre))
        elif up:
            while hb[k] > r + step:
                if q <= -n:
                    cash += q * u * hb[k]; fee_t += -q * u * hb[k] * taker; ev.append((s[k], "stop", hb[k], 0, centre)); q = 0; stops += 1
                    r = centre = last[k]; ev.append((s[k], "restart", r, 0, centre)); break
                r += step; trips += q > 0; q -= 1; cash += u * r; fee_m += u * r * maker; ev.append((s[k], "sell", r, q, centre))
        Q[k], C[k], TR[k] = q, cash, trips
    k = len(s) - 1
    if q: px = ls[k] if q > 0 else hb[k]; px = px if px == px else last[k]; cash += q * u * px; fee_t += abs(q) * u * last[k] * taker; ev.append((s[k], "daily close", px, 0, centre))
    E = pl.DataFrame(ev, schema=["s", "event", "price", "position", "centre"], orient="row")
    tot = dict(gross=cash * 100, trips_income=trips * step * u * 100, inventory=(cash - trips * step * u) * 100, maker_fee=fee_m * 100,
               taker_fee=fee_t * 100, funding=fund * 100, net=(cash - fee_m - fee_t + fund) * 100, trips=trips, stops=stops)
    return E, tot, dict(s=s, last=last, step=step, p0=p0, u=u, q=Q, cash=C, trips=TR)


if __name__ == "__main__":
    data = g.load("2024-03", "2024-03")
    E, tot, _ = log_day(data, "2024-03-12")
    ref = g.run(data, 50, n=4).filter(pl.col("day") == np.datetime64("2024-03-12", "D").astype(np.int64)).to_dicts()[0]
    for k, v in tot.items(): print(f"{k:13} log {v:+.6f}  simulator {ref[k]:+.6f}")
    pl.Config.set_tbl_rows(100)
    print(E.with_columns(pl.from_epoch("s", time_unit="s").dt.time().alias("time")).select("time", "event", "price", "position", "centre"))
