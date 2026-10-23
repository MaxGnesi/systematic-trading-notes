"""Lecture 14 §5: which measure forecasts the risk of the next bars best? Hourly bars.
Target: realised variance of the next 1, 4 and 24 hours, from one-minute returns.
Each measure over the past 24 hours, times the time-of-day factor of the hours ahead (median share of each hour, past 28 days), times one constant
fitted on the training period (October 2021 to June 2023; minimising QLIKE: a = mean(target / raw forecast)). Scored out of sample (July 2023 on)
with QLIKE = mean(target/forecast - log(target/forecast) - 1), robust to the noise of the target (Patton, 2011); differences against realised
variance at one minute with a Newey-West standard error (Diebold-Mariano)."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"; LN2 = np.log(2)
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "high", "low", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
       .with_columns(pl.col("close").forward_fill()).with_columns(pl.col("high").fill_null(pl.col("close")), pl.col("low").fill_null(pl.col("close"))))
nh = n // 60; c = np.log(g["close"].to_numpy())[: nh * 60]; hi = g["high"].to_numpy()[: nh * 60].reshape(nh, 60); lo = g["low"].to_numpy()[: nh * 60].reshape(nh, 60)
r1 = np.diff(np.r_[c[0], c]).reshape(nh, 60)                               # one-minute returns, by hour
C = c.reshape(nh, 60)
hour = {"rv1m": (r1 ** 2).sum(1),
        "rv5m": (np.diff(np.c_[np.r_[c[0], C[:-1, -1]], C[:, 4::5]], axis=1) ** 2).sum(1),
        "bv1m": np.pi / 2 * (np.abs(r1[:, 1:]) * np.abs(r1[:, :-1])).sum(1),
        "range1h": np.log(hi.max(1) / lo.min(1)) ** 2 / (4 * LN2),
        "r1h": (C[:, -1] - np.r_[c[0], C[:-1, -1]]) ** 2}
import bars                                                                # duration measure: range bars closing in each hour x R^2 / 2 (R: the day's threshold, past 28 days)
th = bars.thresholds("BTCUSDT").select("day", "range")
rb = pl.scan_parquet(sorted(bars.bars_dir("BTCUSDT", "range").glob("*.parquet"))).select("end_ms").collect()
hcount = np.bincount(((rb["end_ms"].to_numpy() - int(np.datetime64(t0, "ms").astype(np.int64))) // 3_600_000).clip(0, nh - 1), minlength=nh)[:nh].astype(float)
Rday = dict(zip(th["day"].to_list(), th["range"].to_list()))
hdays = pl.datetime_range(t0, t0 + timedelta(hours=nh - 1), "1h", eager=True).dt.date().to_list()
hour["dur"] = hcount * np.array([Rday.get(d, np.nan) for d in hdays]) ** 2 / 2
LAB = {"dur": "duration (range-bar count)", "r1h": "squared hourly returns", "range1h": "hourly ranges (Parkinson)", "rv5m": "realised, 5 min", "rv1m": "realised, 1 min", "bv1m": "bipower, 1 min"}
hod = np.arange(nh) % 24; times = pl.datetime_range(t0, t0 + timedelta(hours=nh - 1), "1h", eager=True)
split = int(np.searchsorted(times.to_numpy(), np.datetime64("2023-07-01")))

# time-of-day factor: share of each hour of the day in the past 28 days' variance (median), times 24
rv = hour["rv1m"]; fac = np.full((nh, 24), np.nan)
days = nh // 24; dayshare = (rv[: days * 24].reshape(days, 24) / rv[: days * 24].reshape(days, 24).sum(1, keepdims=True)) * 24
for d in range(28, days):
    f = np.median(dayshare[d - 28: d], axis=0); fac[d * 24:(d + 1) * 24] = f / f.mean()

past = {k: np.convolve(v, np.ones(24), "full")[: nh] for k, v in hour.items()}      # sum over the past 24 hours, ending with hour i
H5 = hi.reshape(nh, 12, 5).max(2); L5 = lo.reshape(nh, 12, 5).min(2)
TARGETS = {"realised, 1 min": rv, "realised, 5 min": hour["rv5m"], "range of 5-min bars": (np.log(H5 / L5) ** 2).sum(1) / (4 * LN2)}
TNAME = sys.argv[1] if len(sys.argv) > 1 else "realised, 1 min"; tser = TARGETS[TNAME]
R = {"target": TNAME}
for H in (1, 4, 24):
    tgt = np.array([tser[i + 1: i + 1 + H].sum() if i + 1 + H <= nh else np.nan for i in range(nh)])
    seas = np.array([np.nansum(fac[i + 1: i + 1 + H, (hod[i] + 1 + np.arange(H)) % 24].diagonal()) if i + 1 + H <= nh else np.nan for i in range(nh)]) / 24 if H < 24 else np.ones(nh)
    ok = np.isfinite(tgt) & np.isfinite(seas) & (np.arange(nh) >= 24 * 29) & (tgt > 0)
    loss = {}
    for k in hour:
        raw = past[k] * seas * (H / 24 if H < 24 else 1)
        good = ok & (raw > 0)
        a = np.mean(tgt[good & (np.arange(nh) < split)] / raw[good & (np.arange(nh) < split)])
        f = a * raw; q = tgt / f - np.log(tgt / f) - 1
        loss[k] = np.where(good & (np.arange(nh) >= split), q, np.nan)
    # the split: diffusive part (bipower) and jumps (RV - bipower), each with its own weight, fitted on the training period
    C_, J_ = past["bv1m"] * seas * (H / 24 if H < 24 else 1), np.clip(past["rv1m"] - past["bv1m"], 0, None) * seas * (H / 24 if H < 24 else 1)
    tr = ok & (np.arange(nh) < split) & (C_ > 0)
    from scipy.optimize import minimize                                    # weights fitted for the loss they are scored on (QLIKE), as the single measures
    ql = lambda lw: np.mean((lambda f: tgt[tr] / f - np.log(tgt[tr] / f) - 1)(np.exp(lw[0]) * C_[tr] + np.exp(lw[1]) * J_[tr]))
    a0 = np.mean(tgt[tr] / C_[tr]); w = np.exp(minimize(ql, np.log([a0, a0]), method="Nelder-Mead").x)
    f = w[0] * C_ + w[1] * J_; good = ok & (f > 0) & (np.arange(nh) >= split)
    loss["split"] = np.where(good, tgt / f - np.log(tgt / f) - 1, np.nan); LAB["split"] = "split: diffusive + jumps"
    R.setdefault("weights", {})[f"next {H} h"] = [round(float(w[0]), 3), round(float(w[1]), 3)]
    base = loss["rv1m"]; row = {}
    for k in list(hour) + ["split"]:
        x = loss[k]; m = np.isfinite(x) & np.isfinite(base); dlt = x[m] - base[m]
        L = H * 2; dc = dlt - dlt.mean(); v = dc @ dc / len(dc) + 2 * sum((1 - l / (L + 1)) * (dc[l:] @ dc[:-l]) / len(dc) for l in range(1, L + 1))
        row[LAB[k]] = dict(qlike=round(float(np.nanmean(x)), 4), vs_rv1m=round(float(dlt.mean()), 4), t=round(float(dlt.mean() / np.sqrt(v / len(dc))), 1))
    R[f"next {H} h"] = row; print(f"next {H} h", row, flush=True)
fname = "l14_forecast_" + TNAME.replace(" ", "_").replace(",", "") + ".json"
(L14_RESULTS / fname).write_text(json.dumps(R, indent=1))
