"""Lecture 13 §7.3: the round-time spike at one-second resolution: from 2 minutes before the full hour (and the half hour) to 5 minutes after."""
import json, sys
from datetime import date, datetime, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, bars
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"
th = bars.thresholds(SYM); all_days = th["day"].to_list()
sample = [d for d in sorted(set(all_days[::31])) if d.weekday() < 5]                    # weekdays among the sample days
OFF = np.arange(-120, 300)
acc = {":00": np.zeros(len(OFF)), ":30": np.zeros(len(OFF))}; n = {":00": 0, ":30": 0}
for d0 in sample:
    tape.wait_for_memory(2.0)
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price", "quantity").collect())
    sec = ((t["transact_time"].to_numpy() - a) // 1000).astype(np.int64)
    usd = np.bincount(sec, weights=(t["price"] * t["quantity"]).to_numpy(), minlength=86_400)
    for h in range(1, 23):                                                              # whole windows within the day
        for name, base in ((":00", h * 3600), (":30", h * 3600 + 1800)):
            hour_mean = usd[h * 3600 - 1800:h * 3600 + 1800 + 1800].mean()           # the hour and a half around it
            if hour_mean > 0:
                acc[name] += usd[base + OFF] / hour_mean; n[name] += 1
prof = {k: acc[k] / n[k] for k in acc}
R = {k: dict(first_second=round(float(prof[k][OFF == 0][0]), 1), first_5s=round(float(prof[k][(OFF >= 0) & (OFF < 5)].mean()), 2),
             first_10s=round(float(prof[k][(OFF >= 0) & (OFF < 10)].mean()), 2), seconds_10_60=round(float(prof[k][(OFF >= 10) & (OFF < 60)].mean()), 2),
             minutes_1_5=round(float(prof[k][(OFF >= 60) & (OFF < 300)].mean()), 2), minute_before=round(float(prof[k][(OFF >= -60) & (OFF < 0)].mean()), 2),
             last_5s_before=round(float(prof[k][(OFF >= -5) & (OFF < 0)].mean()), 2),
             seconds_above_2x=int((prof[k][OFF >= 0] > 2).sum()), back_below_1_5x_after_s=int(np.argmax(prof[k][OFF >= 0] < 1.5))) for k in prof}
R["windows"] = n; R["days"] = len(sample)
fig = make_subplots(rows=1, cols=1)
for k, col in ((":00", SERIES[3]), (":30", SERIES[0])):
    fig.add_scatter(x=OFF, y=prof[k], mode="lines", line=dict(color=col, width=1.5), name=f"around the {'full' if k == ':00' else 'half'} hour ({k})")
fig.add_hline(y=1, line=dict(color=MUTED, dash="dot")); fig.add_vline(x=0, line=dict(color=INK, width=1))
fig.update_xaxes(title_text="seconds from the round time"); fig.update_yaxes(title_text="dollars per second ÷ average", type="log")
fig.update_layout(title="The round-time spike, second by second: most of it lies in the first seconds<br><sup>Weekdays on 43 sample days, every full and half hour from 01:00 to 22:30 UTC; "
                        "dollars per second relative to the average of the surrounding hour and a half</sup>",
                  height=460, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "13_10_round_seconds", FIG)
(L13_RESULTS / "l13_round_seconds.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
