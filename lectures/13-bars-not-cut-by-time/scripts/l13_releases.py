"""Lecture 13 §7.3-§7.4: US inflation releases (CPI, 8:30 New York) and Fed decisions (14:00 New York) by period.
First move: the return over the first five minutes; follow-through: its correlation with the next 30 minutes.
Drift before Fed decisions: the return over the 30 minutes and the 24 hours before, against the same window a week earlier."""
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy import stats
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
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
grid = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
          .with_columns(pl.col("close").forward_fill()))
LP = np.log(grid["close"].to_numpy())
PERIODS = (("2021–2022", ("2021", "2022")), ("2023", ("2023",)), ("2024–2026", ("2024", "2025", "2026")))


def us_dst(d):
    m = date(d.year, 3, 8); s = m + timedelta(days=(6 - m.weekday()) % 7); k = date(d.year, 11, 1); e = k + timedelta(days=(6 - k.weekday()) % 7)
    return s <= d < e


def at_ny(x, hh, mm):
    """Minute index of hh:mm New York time on day x (New York is UTC-4 in summer, UTC-5 in winter)."""
    d = date.fromisoformat(x)
    return int((datetime(d.year, d.month, d.day) - t0).total_seconds() // 60) + (hh + (4 if us_dst(d) else 5)) * 60 + mm


ret = lambda i, a, b: (LP[i + b - 1] - LP[i + a - 1]) * 1e4               # return from the close of minute i+a-1 to the close of minute i+b-1, bp
R = {"by_period": [], "fed_drift": []}
for name, dates, hh, mm in (("CPI", event_dates.CPI, 8, 30), ("Fed decision", event_dates.FOMC, 14, 0)):
    ev = [(x, at_ny(x, hh, mm)) for x in dates if at_ny(x, hh, mm) + 40 < n]
    for lab, years in PERIODS:
        s = np.array([i for x, i in ev if x[:4] in years])
        first, after = ret(s, 0, 5), ret(s, 5, 35)
        r, p = stats.pearsonr(first, after)
        R["by_period"].append(dict(event=name, period=lab, n=len(s), first_move_median_abs_bp=round(float(np.median(np.abs(first)))), follow_corr=round(float(r), 2), p=round(float(p), 2)))
    if name == "Fed decision":
        for lab, years in PERIODS + (("All", None),):
            s = np.array([i for x, i in ev if years is None or x[:4] in years]); c = s - 7 * 1440
            b30, c30, b24, c24 = ret(s, -30, 0), ret(c, -30, 0), ret(s, -1440, 0), ret(c, -1440, 0)
            R["fed_drift"].append(dict(period=lab, n=len(s), before_30m_bp=round(float(b30.mean())), se_30m=round(float(b30.std() / np.sqrt(len(s)))), week_earlier_30m=round(float(c30.mean())),
                                       share_up=round(float((b30 > 0).mean()), 2), before_24h_bp=round(float(b24.mean())), se_24h=round(float(b24.std() / np.sqrt(len(s)))), week_earlier_24h=round(float(c24.mean()))))
(L13_RESULTS / "l13_releases.json").write_text(json.dumps(R, indent=1))
if __name__ == "__main__":
    for k in R:
        for row in R[k]: print(row)
