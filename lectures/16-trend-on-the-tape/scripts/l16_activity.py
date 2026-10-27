"""Lecture 16: can next hour's activity be forecast? Activity of an hour = its dollar volume over a typical hour (the 28-day median daily volume / 24),
which is the number of dollar bars it will contain at one bar per typical hour. Forecasts of log activity, all known at the start of the hour:
M0 constant (a typical hour), M1 seasonal (mean of the same hour of the week over the past 4 weeks), M2 the last hour, M3 HAR (last hour, last 24 hours,
last week, seasonal), M4 M3 plus the CPI and Fed release hours (dates known in advance). Fitted 2021-2024, judged 2025-2026: R squared of log activity.
Then the bridge: next hour's realised variance (one-minute returns) forecast (a) by a HAR on hourly realised variance with the same terms, (b) as forecast
activity x risk per unit of activity (the 28-day median of realised variance over activity), (c) both; judged by QLIKE out of sample."""
import json, sys
from datetime import date, datetime, timedelta
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
import tape, event_dates

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close", "usd").collect().sort("time")
H = (m1.with_columns(pl.col("close").log().diff().alias("r"))
     .group_by_dynamic("time", every="1h").agg(pl.col("usd").sum(), (pl.col("r") ** 2).sum().alias("rv")).sort("time"))
H = pl.DataFrame({"time": pl.datetime_range(H["time"][0], H["time"][-1], "1h", eager=True)}).join(H, on="time", how="left").with_columns(pl.col("usd").fill_null(0.0), pl.col("rv").fill_null(0.0))
usd = H["usd"].to_numpy(); rv = H["rv"].to_numpy(); n = len(usd)
typ = pl.Series(usd).rolling_sum(24).rolling_median(28 * 24, min_samples=7 * 24).shift(1).to_numpy() / 24       # a typical hour, known before
A = usd / typ; la = np.log(np.maximum(A, 1e-3)); lrv = np.log(np.maximum(rv, 1e-12))
how = (H["time"].dt.weekday().to_numpy() - 1) * 24 + H["time"].dt.hour().to_numpy()                    # hour of the week, 0..167


def lagged_mean(x, k):
    """Mean of x over the k hours before each hour."""
    c = np.r_[0.0, np.cumsum(np.nan_to_num(x))]; out = np.full(len(x), np.nan); out[k:] = (c[k:len(x)] - c[:len(x) - k]) / k
    return out


def seasonal(x):
    """Mean of the same hour of the week in the four weeks before."""
    out = np.full(len(x), np.nan); out[4 * 168:] = sum(x[4 * 168 - 168 * w:len(x) - 168 * w] for w in range(1, 5)) / 4
    return out


rel = np.zeros(n)
def release_hour(x, hh, mm):
    d = date.fromisoformat(x); m = date(d.year, 3, 8); s0 = m + timedelta(days=(6 - m.weekday()) % 7); k = date(d.year, 11, 1); e0 = k + timedelta(days=(6 - k.weekday()) % 7)
    return datetime(d.year, d.month, d.day, hh + (4 if s0 <= d < e0 else 5), mm).replace(minute=0)
tm = H["time"].to_list(); idx = {t: i for i, t in enumerate(tm)}
for dates, hh, mm in ((event_dates.CPI, 8, 30), (event_dates.FOMC, 14, 0)):
    for x in dates:
        t = release_hour(x, hh, mm)
        if t in idx: rel[idx[t]] = 1.0


def har_terms(x):
    return np.column_stack([np.r_[np.nan, x[:-1]], lagged_mean(x, 24), lagged_mean(x, 168), seasonal(x)])


IS = (H["time"] < datetime(2025, 1, 1)).to_numpy(); START = 28 * 24 + 168 * 4
ok = np.zeros(n, bool); ok[START:] = True; ok &= np.isfinite(la)


def fit_predict(y, X):
    m = ok & np.all(np.isfinite(X), axis=1) & np.isfinite(y)
    Xc = np.column_stack([np.ones(n), X]); b = np.linalg.lstsq(Xc[m & IS], y[m & IS], rcond=None)[0]
    return Xc @ b, m, b


def r2(y, f, m):
    return float(1 - np.mean((y[m] - f[m]) ** 2) / np.mean((y[m] - y[m].mean()) ** 2))


T = har_terms(la); R = {"activity": {}}
fc = {"M0 constant": np.zeros(n), "M1 seasonal": T[:, 3], "M2 last hour": T[:, 0]}
fc["M3 HAR"], m3, b3 = fit_predict(la, T)
fc["M4 HAR + releases"], m4, b4 = fit_predict(la, np.column_stack([T, rel]))
mm_ = m4 & np.all(np.isfinite(T), axis=1)
for k, f in fc.items():
    R["activity"][k] = {s: round(r2(la, f, mm_ & sel), 3) for s, sel in (("2021-2024", IS), ("2025-2026", ~IS))}
R["activity"]["coefficients M4"] = [round(float(x), 3) for x in b4]
R["activity"]["release hours"] = {"n": int(rel.sum()), "mean log activity": round(float(la[rel == 1].mean()), 2)}
# how often the forecast is within a factor of 1.5 of the outcome, out of sample
R["activity"]["within x1.5, M4, 2025-2026"] = round(float(np.mean(np.abs(la[mm_ & ~IS] - fc["M4 HAR + releases"][mm_ & ~IS]) < np.log(1.5))), 3)

# the bridge: forecast next hour's realised variance
ratio = lrv - la                                                                # log of risk per unit of activity
ratio_typ = pl.Series(np.where(np.isfinite(ratio), ratio, np.nan)).rolling_median(28 * 24, min_samples=7 * 24).shift(1).to_numpy()
fa = fc["M4 HAR + releases"] + ratio_typ                                        # (b) activity route, log variance
TR = har_terms(lrv)
fr, mr, _ = fit_predict(lrv, np.column_stack([TR, rel]))                        # (a) HAR on hourly realised variance
fb, mb, _ = fit_predict(lrv, np.column_stack([TR, rel, fa]))                    # (c) both
fq, mq, _ = fit_predict(ratio, np.column_stack([har_terms(ratio), rel]))         # risk per unit of activity, forecast with the same terms
fd = fc["M4 HAR + releases"] + fq                                               # (d) both parts forecast: activity + risk per unit of activity
sel = mr & mb & mq & mm_ & np.isfinite(fa) & np.isfinite(fd) & (rv > 0)


def qlike(f_log, s):
    # forecasts are of log variance; turn into variance forecasts with the bias correction exp(mean residual) estimated on 2021-2024 only
    corr = np.log(np.mean(np.exp(lrv[sel & IS] - f_log[sel & IS])))
    v = np.exp(f_log + corr); return float(np.mean(rv[s] / v[s] - np.log(rv[s] / v[s]) - 1))


R["volatility"] = {}
R["ratio_forecast_r2"] = {smp: round(r2(ratio, fq, mq & mm_ & msk), 3) for smp, msk in (("2021-2024", IS), ("2025-2026", ~IS))}
for k, f in (("(a) HAR on hourly realised variance", fr), ("(b) activity forecast x risk per unit of activity", fa), ("(c) both", fb), ("(d) activity x risk per unit of activity, both forecast", fd)):
    R["volatility"][k] = {smp: dict(qlike=round(qlike(f, sel & msk), 4), r2_log=round(r2(lrv, f, sel & msk), 3)) for smp, msk in (("2021-2024", IS), ("2025-2026", ~IS))}
(L16_RESULTS / "l16_activity.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R, indent=1))

# decomposition: log realised variance = log activity + log risk per unit of activity; how the variance of the first splits
m = mm_ & np.isfinite(ratio) & (rv > 0)
va, vr, cv = np.var(la[m]), np.var(ratio[m]), np.cov(la[m], ratio[m])[0, 1]
R["decomposition"] = dict(var_log_rv=round(float(np.var(lrv[m])), 3), var_log_activity=round(float(va), 3), var_log_risk_per_activity=round(float(vr), 3),
                          two_cov=round(float(2 * cv), 3), corr=round(float(cv / np.sqrt(va * vr)), 3))
(L16_RESULTS / "l16_activity.json").write_text(json.dumps(R, indent=1))
print(R["decomposition"])
