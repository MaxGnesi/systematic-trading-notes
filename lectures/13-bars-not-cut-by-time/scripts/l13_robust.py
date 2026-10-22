"""Lecture 13 §3: are the clocks robust to their settings? A grid of choices, on a sample of days, with three stability measures.

Price clocks (range, CUSUM): resolution of the clock's price (every fill, 100 ms, 1 s, 5 s, 30 s) x target bars per day (12 ... 192).
For each resolution the threshold scale is set once so that the median day has the target number of bars (fairness, not tuning).
Measures: dispersion of bars per day across days, busiest day relative to the median day, share of bars with 3 trades or fewer,
and the Fed day of 21 September 2022 relative to the median day.
Dollar clock: the window of the adaptive threshold (14, 28, 56 days): bars per day by year and weeks within 25% of the target."""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, bars

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
RES = {"every fill": 0, "100 ms": 100, "1 s": 1000, "5 s": 5000, "30 s": 30000}
TARGETS = [12, 24, 48, 96, 192]
th = bars.thresholds(SYM)
sigma = th.select("day", (pl.col("range") / bars.K_RANGE * np.sqrt(bars.N)).alias("sig"))      # typical daily volatility, past 28 days
special = [date(2022, 9, 21), date(2023, 1, 7), date(2023, 8, 17)]
all_days = sigma["day"].to_list(); sample = sorted(set(special) | set(all_days[::31]))
print("days in the sample:", len(sample), flush=True)

counts = {}                                                                # (clock, resolution, target) -> list of (day, bars, small bars)
for d0 in sample:
    tape.wait_for_memory(2.0)
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price", "quantity").collect())
    ts, px, q = t["transact_time"].to_numpy(), t["price"].to_numpy(), t["quantity"].to_numpy()
    sig = sigma.filter(pl.col("day") == d0)["sig"].item()
    for rname, rms in RES.items():
        if rms == 0:
            lp = np.log(px); trades_per_point = np.ones(len(px), np.int64)
        else:
            b = ts // rms; first = np.r_[True, b[1:] != b[:-1]]; idx = np.cumsum(first) - 1
            lp = np.log(np.bincount(idx, px * q) / np.bincount(idx, q)); trades_per_point = np.bincount(idx)
        cum = np.cumsum(trades_per_point)
        for clock, fn in (("range", bars._range_ends), ("cusum", bars._cusum_ends)):
            for n in TARGETS:
                ends = fn(lp, sig / np.sqrt(n))                           # scale 1; calibrated below from the median day
                per_bar = np.diff(np.r_[0, cum[ends]]) if len(ends) else np.array([])
                counts.setdefault((clock, rname, n), []).append((d0, len(ends), int((per_bar <= 3).sum())))
    print(d0, flush=True)

# For a threshold scaled by k, the number of bars falls roughly as 1/k^2: choose k per (clock, resolution) so the median day hits the target.
# The counts above were made at k = 1; rather than rerun, report the dispersion measures, which do not depend on k to first order,
# and the scale k each setting would need (a stable method needs similar k across resolutions).
rows = []
for (clock, rname, n), v in counts.items():
    c = np.array([x[1] for x in v], float); small = np.array([x[2] for x in v], float)
    med = np.median(c); fed = dict((x[0], x[1]) for x in v).get(date(2022, 9, 21), np.nan)
    rows.append(dict(clock=clock, resolution=rname, target=n, scale_needed=round(float(np.sqrt(med / n)), 2) if med > 0 else None,
                     dispersion=round(float(np.std(np.log1p(c))), 2), busiest_vs_median=round(float(c.max() / med), 1) if med > 0 else None,
                     share_bars_3_trades_or_fewer=round(float(small.sum() / max(c.sum(), 1)), 3), fed_day_vs_median=round(float(fed / med), 1) if med > 0 else None))
T = pl.DataFrame(rows).sort("clock", "target", "resolution")

# the dollar clock: window of the adaptive threshold
dd = pl.concat([pl.read_parquet(f, columns=["day", "usd"]) for f in sorted(D.glob("*/days.parquet"))]).sort("day")
dollar = []
for w in (14, 28, 56):
    x = dd.with_columns((pl.col("usd") / (pl.col("usd").shift(1).rolling_median(w, min_samples=7) / bars.N)).alias("bars")).drop_nulls("bars")
    wk = x.group_by(pl.col("day").dt.truncate("1w")).agg(pl.col("bars").mean())
    dollar.append(dict(window_days=w, mean_bars_per_day=round(float(x["bars"].mean()), 1), weeks_within_25pct=round(float(((wk["bars"] / bars.N - 1).abs() <= 0.25).mean()), 2),
                       by_year=x.group_by(pl.col("day").dt.year().alias("y")).agg(pl.col("bars").mean().round(1)).sort("y").to_dicts()))
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(180)
print(T); print(json.dumps(dollar, indent=1, default=str))
T.write_parquet(L13_RESULTS / "l13_robust_price.parquet"); (L13_RESULTS / "l13_robust_dollar.json").write_text(json.dumps(dollar, indent=1, default=str))
