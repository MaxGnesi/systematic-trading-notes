"""Lecture 13 §7.4: option expiries (Deribit, Fridays 08:00 UTC): activity and the size of moves, minute by minute from 07:00 to 09:30 UTC,
on quarterly, monthly and weekly expiry Fridays, against Thursdays as a control."""
import json, sys
from datetime import date, timedelta
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
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
m1 = (pl.concat([pl.read_parquet(f, columns=["time", "close", "usd", "trades"]) for f in sorted(D.glob("*/m1.parquet"))]).sort("time")
        .with_columns(pl.col("close").log().diff().abs().alias("absr"), pl.col("time").dt.date().alias("day"),
                      (pl.col("time").dt.hour().cast(pl.Int32) * 60 + pl.col("time").dt.minute().cast(pl.Int32)).alias("mod")))
m1 = m1.join(m1.group_by("day").agg(pl.col("usd").mean().alias("du"), pl.col("absr").mean().alias("dr")), on="day").with_columns(
    (pl.col("usd") / pl.col("du")).alias("act"), (pl.col("absr") / pl.col("dr")).alias("mv"))


def kind(d):
    if d.weekday() == 3: return "Thursday: no expiry (control)"
    if d.weekday() != 4: return None
    last = (d + timedelta(days=7)).month != d.month
    if last and d.month in (3, 6, 9, 12): return "quarterly expiry"
    if last: return "monthly expiry"
    return "weekly expiry (other Fridays)"


days = pl.DataFrame({"day": sorted(m1["day"].unique().to_list())}).with_columns(pl.col("day").map_elements(kind, return_dtype=pl.Utf8).alias("kind")).drop_nulls("kind")
w = m1.filter(pl.col("mod").is_between(7 * 60, 9 * 60 + 29)).join(days, on="day")
prof = w.group_by("kind", "mod").agg(pl.col("act").median(), pl.col("mv").median()).sort("kind", "mod")
# volatility in the hour before and the hour after 08:00, relative to the day's average minute
vol = (w.with_columns(pl.when(pl.col("mod") < 8 * 60).then(pl.lit("before")).otherwise(pl.lit("after")).alias("side"))
         .filter(pl.col("mod").is_between(7 * 60, 8 * 60 + 59)).group_by("kind", "side").agg(pl.col("mv").median(), pl.col("act").median()))
counts = days.group_by("kind").len()
R = {"counts": {k: n for k, n in counts.iter_rows()},
     "minute_0800": {k: dict(activity=round(float(a), 2), move=round(float(m), 2)) for k, a, m in prof.filter(pl.col("mod") == 8 * 60).select("kind", "act", "mv").iter_rows()},
     "hour_before_after": {f"{k} / {s}": dict(move=round(float(m), 2), activity=round(float(a), 2)) for k, s, m, a in vol.sort("kind", "side").iter_rows()}}
STY = {"quarterly expiry": (SERIES[3], 2.2), "monthly expiry": (SERIES[1], 1.8), "weekly expiry (other Fridays)": (SERIES[0], 1.4), "Thursday: no expiry (control)": (MUTED, 1.4)}
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, subplot_titles=("Dollars per minute ÷ the day's average", "Size of the move per minute ÷ the day's average"))
for k, (col, wdt) in STY.items():
    q = prof.filter(pl.col("kind") == k)
    if not q.height: continue
    sm_a = q["act"].rolling_mean(3, center=True, min_samples=1); sm_m = q["mv"].rolling_mean(3, center=True, min_samples=1)
    lab = f"{k} ({R['counts'].get(k, 0)} days)"
    fig.add_scatter(x=q["mod"] / 60, y=sm_a, mode="lines", line=dict(color=col, width=wdt), name=lab, legendgroup=k, row=1, col=1)
    fig.add_scatter(x=q["mod"] / 60, y=sm_m, mode="lines", line=dict(color=col, width=wdt), name=lab, legendgroup=k, showlegend=False, row=2, col=1)
for r in (1, 2):
    fig.add_vline(x=8, line=dict(color=INK, width=1, dash="dot"), row=r, col=1)
fig.add_annotation(x=8, y=0.97, yref="y domain", text="08:00 UTC: expiry", showarrow=False, xanchor="left", yanchor="top", xshift=4, font=dict(size=11))
fig.update_xaxes(title_text="time of day, UTC (hours)", tickvals=[7, 7.5, 8, 8.5, 9, 9.5], ticktext=["07:00", "07:30", "08:00", "08:30", "09:00", "09:30"], row=2, col=1)
fig.update_layout(title="Option expiries on the tape: Fridays at 08:00 UTC, against Thursdays<br><sup>Median over five years, three-minute smoothing. "
                        "Quarterly expiries (last Friday of March, June, September, December) are the largest</sup>",
                  height=600, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.12, x=0))
save_figure(fig, PREFIX + "13_11_option_expiry", FIG)
(L13_RESULTS / "l13_expiry.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
