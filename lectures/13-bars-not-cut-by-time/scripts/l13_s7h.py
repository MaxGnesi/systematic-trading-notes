"""Lecture 13 §7: seasonality as five hypotheses, tested on calendar slots fixed in advance by schedules.
Every slot instance: a window [T, T+L) with a window before it and one after it. Measures per instance:
  activity   dollars per minute in the window / the average minute of the past 28 days
  volatility the average size of one-minute moves (absolute returns) in the window / the same for the past 28 days
  flow       net aggressive buying / dollars in the window
  return     log return over the window (bp); before and after: the windows before and after
Each slot is compared with a control slot of the same length. Tests: Welch t on the means (activity, volatility, flow, return),
correlation of the return in the window with the return after it (follow-through). Benjamini-Hochberg across all tests."""
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy import stats
from pandas.tseries.holiday import USFederalHolidayCalendar
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, event_dates

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
m1 = pl.concat([pl.read_parquet(f, columns=["time", "close", "usd", "signed_usd"]) for f in sorted(D.glob("*/m1.parquet"))]).sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
grid = pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
grid = grid.with_columns(pl.col("close").forward_fill(), pl.col("usd").fill_null(0.0), pl.col("signed_usd").fill_null(0.0))
TIME = grid["time"]; LP = np.log(grid["close"].to_numpy()); USD = grid["usd"].to_numpy(); SU = grid["signed_usd"].to_numpy()
R2 = np.r_[0.0, np.abs(np.diff(LP))]                                    # size of each one-minute move
CU, CS, CR = np.r_[0, np.cumsum(USD)], np.r_[0, np.cumsum(SU)], np.r_[0, np.cumsum(R2)]
day_idx = np.arange(n) // 1440; nd = day_idx[-1] + 1                     # the grid starts at midnight
du = np.bincount(day_idx, USD, nd) / 1440; dr = np.bincount(day_idx, R2, nd) / 1440
past = lambda x: pl.Series(x).shift(1).rolling_mean(28, min_samples=7).to_numpy()
PU, PR = past(du), past(dr)                                              # the past 28 days' average minute, per day
DAYS = [(t0 + timedelta(days=int(i))).date() for i in range(nd)]
idx_of = lambda dt: int((dt - t0).total_seconds() // 60)


def inst(starts, L, B, A):
    """Per instance: activity, volatility, flow, return before, in and after the window."""
    s = np.array([i for i in starts if i - B - 1 >= 0 and i + L + A < n and not np.isnan(PU[day_idx[i]])], dtype=np.int64)
    d = day_idx[s]; u = CU[s + L] - CU[s]
    return dict(act=u / L / PU[d], vol=(CR[s + L] - CR[s]) / L / PR[d], flow=(CS[s + L] - CS[s]) / np.where(u > 0, u, np.nan),
                before=(LP[s - 1] - LP[s - 1 - B]) * 1e4, ret=(LP[s + L - 1] - LP[s - 1]) * 1e4, after=(LP[s + L + A - 1] - LP[s + L - 1]) * 1e4)


def local_starts(tz, hh, mm, weekdays=True):
    """Minute indices at which the local clock in tz shows hh:mm, on weekdays."""
    lt = TIME.dt.replace_time_zone("UTC").dt.convert_time_zone(tz)
    ok = (lt.dt.hour() == hh) & (lt.dt.minute() == mm) & ((lt.dt.weekday() <= 5) if weekdays else True)
    return np.nonzero(ok.to_numpy())[0]


utc = TIME.dt.hour().cast(pl.Int32).to_numpy() * 60 + TIME.dt.minute().cast(pl.Int32).to_numpy(); wd = TIME.dt.weekday().to_numpy()
hol = {d.date() for d in USFederalHolidayCalendar().holidays(DAYS[0], DAYS[-1])}
weekday_ord = [i for i in range(nd) if DAYS[i].weekday() < 5 and DAYS[i] not in hol]
mins_of = lambda cond: np.nonzero(cond & (wd <= 5))[0]
last_fri = lambda d: d.weekday() == 4 and (d + timedelta(days=7)).month != d.month
def at_ny(dates, hh, mm):
    out = []
    for x in dates:
        d = date.fromisoformat(x); i = local_starts_cache.get(d)
        out.append(idx_of(datetime.fromisoformat(f"{x}T00:00")) + (hh + (4 if us_dst(d) else 5)) * 60 + mm)   # New York = UTC-4 in summer, UTC-5 in winter
    return out
def us_dst(d):
    m = date(d.year, 3, 8); s = m + timedelta(days=(6 - m.weekday()) % 7); k = date(d.year, 11, 1); e = k + timedelta(days=(6 - k.weekday()) % 7)
    return s <= d < e
local_starts_cache = {}
hour_ctl = mins_of(utc % 60 == 0)                                           # every full hour of a weekday: the control for one-hour slots
rnd_ctl = mins_of(np.isin(utc % 60, [7, 17, 37, 47]))                       # minutes nobody schedules
day_start = lambda days: [i * 1440 for i in days]
fri = lambda kind: [i for i in range(nd) if DAYS[i].weekday() == 4 and ((kind == "q" and last_fri(DAYS[i]) and DAYS[i].month in (3, 6, 9, 12))
                                                                       or (kind == "m" and last_fri(DAYS[i]) and DAYS[i].month not in (3, 6, 9, 12)) or (kind == "w" and not last_fri(DAYS[i])))]
thu = [i for i in range(nd) if DAYS[i].weekday() == 3]

# (rhythm, slot, starts, control starts, window L, before B, after A), in minutes
SLOTS = [
    ("Time of day", "Tokyo opening hour (9:00 Tokyo)", local_starts("Asia/Tokyo", 9, 0), hour_ctl, 60, 60, 60),
    ("Time of day", "London opening hour (8:00 London)", local_starts("Europe/London", 8, 0), hour_ctl, 60, 60, 60),
    ("Time of day", "New York opening hour (9:30 New York)", local_starts("America/New_York", 9, 30), hour_ctl, 60, 60, 60),
    ("Time of day", "Around the New York close (15:30 New York)", local_starts("America/New_York", 15, 30), hour_ctl, 60, 60, 60),
    ("Time of day", "New York night (2:00 New York)", local_starts("America/New_York", 2, 0), hour_ctl, 60, 60, 60),
    ("Week", "Saturday", day_start([i for i in range(nd) if DAYS[i].weekday() == 5]), day_start(weekday_ord), 1440, 1440, 1440),
    ("Week", "Sunday", day_start([i for i in range(nd) if DAYS[i].weekday() == 6]), day_start(weekday_ord), 1440, 1440, 1440),
    ("Week", "Monday", day_start([i for i in weekday_ord if DAYS[i].weekday() == 0]), day_start(weekday_ord), 1440, 1440, 1440),
    ("Week", "Friday", day_start([i for i in weekday_ord if DAYS[i].weekday() == 4]), day_start(weekday_ord), 1440, 1440, 1440),
    ("Week", "US public holiday on a weekday", day_start([i for i in range(nd) if DAYS[i] in hol and DAYS[i].weekday() < 5]), day_start(weekday_ord), 1440, 1440, 1440),
    ("Round times", "First minute of the hour, funding (00, 08, 16 UTC)", mins_of(np.isin(utc, [0, 480, 960])), rnd_ctl, 1, 30, 30),
    ("Round times", "First minute of the hour, other hours", mins_of((utc % 60 == 0) & ~np.isin(utc, [0, 480, 960])), rnd_ctl, 1, 30, 30),
    ("Round times", "First minute of the half hour (:30)", mins_of(utc % 60 == 30), rnd_ctl, 1, 30, 30),
    ("Round times", "First minute of a quarter (:15, :45)", mins_of(np.isin(utc % 60, [15, 45])), rnd_ctl, 1, 30, 30),
    ("Round times", "Last minute of the hour (:59)", mins_of(utc % 60 == 59), rnd_ctl, 1, 30, 30),
    ("Releases", "US inflation release (CPI, 8:30 New York)", at_ny(event_dates.CPI, 8, 30), [i - 7 * 1440 for i in at_ny(event_dates.CPI, 8, 30)], 5, 30, 30),
    ("Releases", "Fed decision (14:00 New York)", at_ny(event_dates.FOMC, 14, 0), [i - 7 * 1440 for i in at_ny(event_dates.FOMC, 14, 0)], 5, 30, 30),
    ("Option expiries", "Quarterly expiry, settlement window (07:30-08:00 UTC)", [i * 1440 + 450 for i in fri("q")], [i * 1440 + 450 for i in thu], 30, 30, 30),
    ("Option expiries", "Monthly expiry, settlement window", [i * 1440 + 450 for i in fri("m")], [i * 1440 + 450 for i in thu], 30, 30, 30),
    ("Option expiries", "Weekly expiry, settlement window", [i * 1440 + 450 for i in fri("w")], [i * 1440 + 450 for i in thu], 30, 30, 30),
]


def summ(e, c):
    def ms(x): x = x[~np.isnan(x)]; return float(x.mean()), float(x.std() / np.sqrt(len(x)))
    out = dict(n=len(e["ret"]), n_ctl=len(c["ret"]))
    for k, sc in (("act", 1), ("vol", 1), ("flow", 100), ("ret", 1), ("before", 1)):
        a, b = e[k][~np.isnan(e[k])] * sc, c[k][~np.isnan(c[k])] * sc
        (ma, sa), (mb, sb) = ms(a), ms(b)
        out[k] = round(ma, 2); out[k + "_se"] = round(sa, 2); out[k + "_ctl"] = round(mb, 2); out[k + "_ctl_se"] = round(sb, 2)
        out[k + "_p"] = float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    for lab, x in (("", e), ("_ctl", c)):
        r, p = stats.pearsonr(x["ret"], x["after"]); nz = (x["ret"] != 0) & (x["after"] != 0)
        same = np.sign(x["ret"][nz]) == np.sign(x["after"][nz])
        out["follow" + lab] = round(float(r), 3); out["same" + lab] = round(float(same.mean()), 3)
        if lab == "": out["follow_p"] = float(p); out["same_p"] = float(stats.binomtest(int(same.sum()), int(nz.sum()), 0.5).pvalue)
    # follow-through against the control: Fisher z-test of the two correlations
    z = (np.arctanh(out["follow"]) - np.arctanh(out["follow_ctl"])) / np.sqrt(1 / (out["n"] - 3) + 1 / (out["n_ctl"] - 3))
    out["follow_vs_ctl_p"] = float(2 * stats.norm.sf(abs(z)))
    return out


if __name__ == "__main__":
    res = []
    for rhythm, slot, s, c, L, B, A in SLOTS:
        r = summ(inst(s, L, B, A), inst(c, L, B, A)); r.update(rhythm=rhythm, slot=slot, window=L); res.append(r)
        print(rhythm, "|", slot, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("rhythm", "slot")}, flush=True)

    # Benjamini-Hochberg across all tests of all hypotheses
    tests = [(i, k) for i in range(len(res)) for k in ("act_p", "vol_p", "flow_p", "ret_p", "before_p", "follow_vs_ctl_p")]
    p = np.array([res[i][k] for i, k in tests]); o = np.argsort(p); m = len(p)
    q = np.empty(m); q[o] = np.minimum.accumulate((p[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    for (i, k), qq in zip(tests, q): res[i][k.replace("_p", "_q")] = round(float(min(qq, 1.0)), 4)
    (L13_RESULTS / "l13_s7h.json").write_text(json.dumps(dict(tests=m, slots=res), indent=1))
    print("tests", m)
