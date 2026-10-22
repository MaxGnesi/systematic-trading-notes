"""Lecture 13 §3: where each clock ticks, how each clock runs, and bars per week with fixed or adaptive thresholds."""
import json, sys
from datetime import date, datetime, timedelta, timezone
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
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
ORDER = ["time", "tick", "volume", "dollar", "range", "cusum"]
LABEL = {"time": "time (30 minutes)", "tick": "tick", "volume": "volume", "dollar": "dollar", "range": "range", "cusum": "CUSUM"}
COLOR = {"time": INK, "tick": SERIES[4], "volume": SERIES[1], "dollar": SERIES[0], "range": SERIES[2], "cusum": SERIES[3]}
R = {}


def load(kind):
    return pl.concat([pl.read_parquet(f) for f in sorted(bars.bars_dir(SYM, kind).glob("*.parquet"))]).with_columns(
        pl.from_epoch("end_ms", time_unit="ms").alias("end"))


B = {k: load(k) for k in ORDER}
m1 = pl.concat([pl.read_parquet(f, columns=["time", "close"]) for f in sorted(D.glob("*/m1.parquet"))])

# ---------------------------------------------------------------- 1. where each clock ticks: a busy day and a quiet day
days = [(date(2022, 9, 21), "21 September 2022: the Fed decision"), (date(2023, 1, 7), "7 January 2023: the quietest day")]
fig = make_subplots(rows=2, cols=2, shared_xaxes="columns", row_heights=[0.42, 0.58], vertical_spacing=0.04, horizontal_spacing=0.06,
                    subplot_titles=[t for _, t in days] + ["", ""])
for c, (d0, _) in enumerate(days, start=1):
    a, b = datetime(d0.year, d0.month, d0.day), datetime(d0.year, d0.month, d0.day) + timedelta(days=1)
    p = m1.filter(pl.col("time").is_between(a, b, closed="left"))
    fig.add_scatter(x=p["time"], y=p["close"], mode="lines", line=dict(color=INK, width=1), showlegend=False, row=1, col=c)
    counts = {}
    for k in ORDER:
        e = B[k].filter(pl.col("end").is_between(a, b, closed="left"))["end"]; counts[k] = len(e)
        fig.add_scatter(x=e, y=[f"{LABEL[k]}"] * len(e), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=1.2, color=COLOR[k])),
                        showlegend=False, hovertemplate="%{x|%H:%M:%S}<extra>" + LABEL[k] + "</extra>", row=2, col=c)
    R[f"bars_on_{d0}"] = counts
    fig.update_yaxes(categoryorder="array", categoryarray=[LABEL[k] for k in ORDER[::-1]], showgrid=False, showticklabels=c == 1, row=2, col=c)
for c, (d0, _) in enumerate(days, start=1):                              # the number of bars of each clock that day, under its panel
    txt = ", ".join(f"{LABEL[k].split(' ')[0]} {R[f'bars_on_{d0}'][k]}" for k in ORDER)
    fig.add_annotation(text="bars that day: " + txt, xref=f"x{2 + c} domain", yref="paper", x=0, y=-0.08, showarrow=False, xanchor="left", font=dict(size=11, color=MUTED), yshift=-18)
fig.update_yaxes(title_text="price, USDT", row=1, col=1)
fig.update_layout(title="Where each clock ticks: one mark for every bar that closes<br><sup>Each clock is set for 48 bars a day on average, from the past 28 days. "
                        "On a busy day the market's clocks run fast; on a quiet day they nearly stop, while the time bars tick on</sup>",
                  height=640, width=1100, margin=dict(t=100, b=95, l=130))
save_figure(fig, PREFIX + "13_01_where_clocks_tick", FIG)

# ---------------------------------------------------------------- 2. how each clock runs: cumulative bars through one week
a, b = datetime(2022, 9, 19), datetime(2022, 9, 26)
fig = make_subplots(rows=1, cols=1)
for k in ORDER:
    e = B[k].filter(pl.col("end").is_between(a, b, closed="left"))["end"]
    fig.add_scatter(x=e, y=np.arange(1, len(e) + 1), mode="lines", line=dict(color=COLOR[k], width=2 if k != "time" else 1.5, dash="dash" if k == "time" else None, shape="hv"),
                    name=f"{LABEL[k]}: {len(e)} bars")
fig.update_yaxes(title_text="bars closed since Monday 00:00 UTC"); fig.update_xaxes(title_text="19 to 25 September 2022")
fig.update_layout(title="How each clock runs: bars closed through the week of the Fed decision<br><sup>The slope is bars per hour. The time bars climb at a constant rate; "
                        "the market's clocks race on Wednesday evening and almost stop at the weekend</sup>",
                  height=480, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "13_02_how_clocks_run", FIG)

# ---------------------------------------------------------------- 3. dollar bars per week: a fixed threshold against an adaptive one
dd = pl.concat([pl.read_parquet(f, columns=["day", "usd"]) for f in sorted(D.glob("*/days.parquet"))]).sort("day")
fixed_thr = float(dd["usd"].head(28).median()) / bars.N                    # set once, from the first 28 days, and never changed
wk = dd.group_by(pl.col("day").dt.truncate("1w").alias("week")).agg((pl.col("usd").sum() / fixed_thr / 7).alias("fixed")).sort("week")
ad = B["dollar"].group_by(pl.col("end").dt.date().dt.truncate("1w").alias("week")).agg((pl.len() / 7).alias("adaptive")).sort("week")
w = wk.join(ad, on="week").filter(pl.col("week") > pl.col("week").min()).filter(pl.col("week") < pl.col("week").max())
R["bars_per_day_by_year"] = (w.group_by(pl.col("week").dt.year().alias("year")).agg(pl.col("fixed").mean().round(1), pl.col("adaptive").mean().round(1)).sort("year").to_dicts())
R["share_weeks_within_25pct"] = {c: float(((w[c] / bars.N - 1).abs() <= 0.25).mean()) for c in ("fixed", "adaptive")}
fig = make_subplots(rows=1, cols=1)
fig.add_scatter(x=w["week"], y=w["fixed"], mode="lines", line=dict(color=SERIES[1], width=1.5), name="fixed threshold, set from the first 28 days")
fig.add_scatter(x=w["week"], y=w["adaptive"], mode="lines", line=dict(color=SERIES[0], width=1.5), name="adaptive threshold: median of the past 28 days")
fig.add_hline(y=bars.N, line=dict(color=MUTED, dash="dot"), annotation_text="target: 48 a day", annotation_position="top left")
fig.update_yaxes(title_text="dollar bars per day, weekly average", rangemode="tozero")
fig.update_layout(title="Dollar bars per day: a fixed threshold drifts with the market's activity, an adaptive one stays near its target", height=440, width=1100,
                  legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "13_03_fixed_vs_adaptive", FIG)
(L13_RESULTS / "l13_s3.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps(R, indent=1, default=str))
