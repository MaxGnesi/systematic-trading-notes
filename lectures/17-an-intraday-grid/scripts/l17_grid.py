"""Lecture 17: the grid simulator on the tape. Runs on the per-second table of l17_seconds.py.

The grid (classic two-sided paired grid, uniform size): reference price r = the last level filled (the day's first price at the start).
A resting buy sits one step below r, a resting sell one step above; in paired form the position is -(r - centre)/step units.
Fills, conservative (Lecture 14 §4): a resting buy at L fills only if an aggressive seller received less than L in that second (trade-through),
a resting sell only if an aggressive buyer paid more. All levels below (above) r are resting, so a sweep fills several in one second; an order
re-armed by a fill is live only from the next second. If both sides trade through in one second (order unknown, Lecture 14 §2), the side the
second closed on is taken and the second is counted as ambiguous.
Exits at market (taker): the stop, one step beyond the last level (position at the cap n and the price trades through once more), closes all
at the worst aggressive price of that second; the daily close sells (buys) at the last second of the UTC day, so no inventory is held at the
00:00 funding snapshot. After a stop: restart at the price (restart=0) or off for the rest of the day (restart=1).
Money: capital 1; one unit = 1/n of capital at the day's first price, so a full ladder is 1x capital. Fees: maker on every resting fill, taker on
stops and closes. Funding: inventory x price x rate at each snapshot (08:00 and 16:00; 00:00 is always flat). All results per day, in % of capital.
Parts, adding up to the gross result: round trips x step x unit, and the inventory result (what units closed at stops and daily closes made or lost,
the gaps included). The shuffled path (shuffle=True) permutes the day's minutes: the same minutes, the same within-minute trading, no order."""
import sys
from pathlib import Path
import numpy as np, polars as pl
from numba import njit
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
import tape

SEC = tape.ROOT / "interim" / "l17" / "seconds"
FUND = tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet"
# per-day output columns
COLS = ["day", "gross", "trips_income", "inventory", "maker_fee", "taker_fee", "funding", "net", "trips", "stops", "ambiguous", "max_units", "off_share", "gap"]          # gap: what resting fills paid above the market (the second's last price)


def load(start, end):
    """Seconds of the months start..end (YYYY-MM) as numpy arrays; the funding snapshots as (second, rate)."""
    d = pl.concat([pl.read_parquet(SEC / f"{ym}.parquet") for ym in tape.months(start, end)]).sort("s")
    hb = d["hi_buy"].fill_null(np.nan).to_numpy(); ls = d["lo_sell"].fill_null(np.nan).to_numpy()
    fr = pl.read_parquet(FUND).select((pl.col("fundingTime") // 1000 + 30) // 60 * 60, "fundingRate")      # snapshot rounded to the minute
    return d["s"].to_numpy(), hb, ls, d["last"].to_numpy(), fr["fundingTime"].to_numpy(), fr["fundingRate"].to_numpy()


@njit(cache=True)
def shuffle_days(s, hb, ls, last, seed):
    """Within each UTC day, permute the minutes: each minute keeps its own moves relative to the previous minute's last price."""
    np.random.seed(seed)
    n = len(s); S = s.copy(); H = np.empty(n); L = np.empty(n); P = np.empty(n)
    i = 0
    while i < n:
        day = s[i] // 86400; j = i
        while j < n and s[j] // 86400 == day: j += 1
        mins = (s[i:j] % 86400) // 60
        starts = [i]                                               # block boundaries (one block per minute with trades)
        for k in range(i + 1, j):
            if mins[k - i] != mins[k - i - 1]: starts.append(k)
        starts.append(j)
        nb = len(starts) - 1
        ref = np.empty(nb)                                         # each block's reference: the last price before it
        ref[0] = last[i]
        for b in range(1, nb): ref[b] = last[starts[b] - 1]
        perm = np.random.permutation(nb)
        out = i; price = last[i]
        for b in range(nb):
            a, z = starts[perm[b]], starts[perm[b] + 1]
            f = price / ref[perm[b]]
            for k in range(a, z):
                S[out] = day * 86400 + b * 60 + (s[k] % 60) if b < 1440 else s[k]
                H[out] = hb[k] * f; L[out] = ls[k] * f; P[out] = last[k] * f; out += 1
            price = last[z - 1] * f
        i = j
    return S, H, L, P


@njit(cache=True)
def simulate(s, hb, ls, last, fs, fr, on, qmax, qmin, step_bp, n, maker, taker, stop, restart, w):
    """qmax/qmin: per second, the most long / short units allowed (skew); at n / -n the stop applies, inside it the side simply pauses.
    w[k], k = 1..n: the size at the k-th level from the centre, in units (average 1 = uniform); the unit bought at level -k is sold at -(k-1)
    in the same size, so the position q (levels filled) holds cum[|q|] = w[1] + ... + w[|q|] units."""
    ndays = s[-1] // 86400 - s[0] // 86400 + 1
    out = np.zeros((ndays, 14)); d0 = s[0] // 86400
    cum = np.zeros(n + 1)
    for k in range(1, n + 1): cum[k] = cum[k - 1] + w[k]
    fi = 0
    i = 0
    while i < len(s):
        day = s[i] // 86400; j = i
        while j < len(s) and s[j] // 86400 == day: j += 1
        o = out[day - d0]; o[0] = day
        p0 = last[i]; step = step_bp * 1e-4 * p0; u = 1.0 / n / p0
        r = p0; q = 0; cash = 0.0; live = on[i]; dead = False; offn = 0
        while fi < len(fs) and fs[fi] < s[i]: fi += 1
        for k in range(i, j):
            hold = cum[q] if q >= 0 else -cum[-q]                  # units held
            while fi < len(fs) and fs[fi] <= s[k]:                 # funding snapshot: the position held into it pays (long) or receives
                o[6] -= hold * u * last[k - 1 if k > i else k] * fr[fi]; fi += 1
            if dead: offn += 1; continue
            if live and not on[k]:                                 # switched off: close at market, pause
                if q > 0: cash += hold * u * (ls[k] if ls[k] == ls[k] else last[k])
                elif q < 0: cash += hold * u * (hb[k] if hb[k] == hb[k] else last[k])
                o[5] += abs(hold) * u * last[k] * taker; q = 0; live = False
            elif not live and on[k]:
                live = True; r = last[k]
            if not live: offn += 1; continue
            if q > qmax[k] or q < qmin[k]:                         # the skew turned against the inventory: close at market, restart
                if q > 0: cash += hold * u * (ls[k] if ls[k] == ls[k] else last[k])
                else: cash += hold * u * (hb[k] if hb[k] == hb[k] else last[k])
                o[5] += abs(hold) * u * last[k] * taker; q = 0; r = last[k]
            down = ls[k] == ls[k] and ls[k] < r - step
            up = hb[k] == hb[k] and hb[k] > r + step
            if down and up:
                o[10] += 1
                if last[k] < r: up = False
                else: down = False
            if down:
                while ls[k] < r - step:
                    if q >= qmax[k] and qmax[k] < n: break
                    if q >= n:
                        if stop:
                            cash += cum[q] * u * ls[k]; o[5] += cum[q] * u * ls[k] * taker; q = 0; o[9] += 1
                            if restart == 0: r = last[k]
                            else: dead = True
                        break
                    r -= step
                    sz = w[q + 1] if q >= 0 else w[-q]                # opening the next level below, or closing the short unit one step up
                    if q < 0: o[8] += 1; o[2] += sz * step * u
                    q += 1; cash -= sz * u * r; o[4] += sz * u * r * maker; o[13] += sz * u * (r - last[k])
            elif up:
                while hb[k] > r + step:
                    if q <= qmin[k] and qmin[k] > -n: break
                    if q <= -n:
                        if stop:
                            cash -= cum[-q] * u * hb[k]; o[5] += cum[-q] * u * hb[k] * taker; q = 0; o[9] += 1
                            if restart == 0: r = last[k]
                            else: dead = True
                        break
                    r += step
                    sz = w[-q + 1] if q <= 0 else w[q]
                    if q > 0: o[8] += 1; o[2] += sz * step * u
                    q -= 1; cash += sz * u * r; o[4] += sz * u * r * maker; o[13] += sz * u * (last[k] - r)
            if abs(q) > o[11]: o[11] = abs(q)
        k = j - 1                                                  # daily close at the day's last second
        hold = cum[q] if q >= 0 else -cum[-q]
        if q > 0: cash += hold * u * (ls[k] if ls[k] == ls[k] else last[k])
        elif q < 0: cash += hold * u * (hb[k] if hb[k] == hb[k] else last[k])
        o[5] += abs(hold) * u * last[k] * taker
        o[1] = cash; o[3] = cash - o[2]
        o[7] = o[1] - o[4] - o[5] + o[6]; o[12] = offn / (j - i)
        i = j
    return out


def shape(name, n):
    """Size at levels 1..n from the centre (index 0 unused), average 1. Lecture 16, §8: uniform; V-shaped, more further out; bell-shaped, more near
    the centre; bimodal, two bells, one on each side of the price, peaking a few levels away from it; distances scaled so that the shapes look alike for any number of levels."""
    x = 4.0 * np.arange(1, n + 1) / n
    v = {"uniform": np.ones(n), "V-shaped": 0.4 + 0.3 * x, "bell-shaped": np.exp(-(x / 2.2) ** 2) * 1.6 + 0.1,
         "bimodal": np.exp(-((x - 1.6) / 0.9) ** 2) * 1.6 + 0.1}[name]   # one bell on each side, peaking a little away from the price
    return np.r_[0.0, v / v.mean()]


def run(data, step_bp, n=5, maker=2e-4, taker=5e-4, stop=True, restart=0, on=None, shuffle=False, seed=0, qmax=None, qmin=None, sizes="uniform"):
    s, hb, ls, last, fs, fr = data
    if shuffle: s, hb, ls, last = shuffle_days(s, hb, ls, last, seed)
    if on is None: on = np.ones(len(s), dtype=np.bool_)
    qmax = np.full(len(s), n, dtype=np.int64) if qmax is None else qmax
    qmin = np.full(len(s), -n, dtype=np.int64) if qmin is None else qmin
    out = simulate(s, hb, ls, last, fs, fr, on, qmax, qmin, step_bp, n, maker, taker, stop, restart, shape(sizes, n))
    df = pl.DataFrame(out, schema=COLS).filter(pl.col("day") > 0)
    return df.with_columns([(pl.col(c) * 100) for c in ("gross", "trips_income", "inventory", "maker_fee", "taker_fee", "funding", "net", "gap")])
