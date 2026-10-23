"""Lecture 14 §6: risk on any clock. From the bars of Lecture 13, five years.
1. variance per day = bars per day x average variance per bar: the share of the day-to-day variation of log daily variance due to each factor.
2. Wald's identity: true average daily variance against E[bars per day] x E[variance per bar].
3. Precision: relative standard error of a day's variance, sqrt(2/3 sum r^4) / sum r^2, per clock at about 50 bars a day, and for one-minute time bars."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, bars
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
D = tape.ROOT / "interim" / "tape" / "BTCUSDT"


def daily(df):
    b = df.sort("end_ms").with_columns(pl.col("close").log().diff().alias("r"), (pl.col("end_ms") // 86_400_000).alias("d")).drop_nulls()
    return b.group_by("d").agg(pl.len().alias("n"), (pl.col("r") ** 2).sum().alias("rv"), (pl.col("r") ** 4).sum().alias("rq")).filter(pl.col("n") >= 10)


R = {}
CLOCKS = {"time, 30 min": "time", "tick": "tick", "dollar": "dollar", "range": "range", "CUSUM": "cusum"}
for lab, k in CLOCKS.items():
    g = daily(pl.scan_parquet(sorted(bars.bars_dir("BTCUSDT", k).glob("*.parquet"))).select("end_ms", "close").collect())
    n, rv, rq = (g[c].to_numpy() for c in ("n", "rv", "rq"))
    ln, lm = np.log(n), np.log(rv / n); V = (ln + lm).var(); cov = np.cov(ln, lm)[0, 1]
    R[lab] = dict(bars_per_day=round(float(n.mean()), 1), share_count=round(float((ln.var() + cov) / V), 3), share_size=round(float((lm.var() + cov) / V), 3),
                  corr=round(float(np.corrcoef(ln, lm)[0, 1]), 2), true_over_product=round(float(rv.mean() / (n.mean() * (rv / n).mean())), 3),
                  rel_error=round(float(np.median(np.sqrt(2 / 3 * rq) / rv)), 3), rel_error_normal=round(float(np.sqrt(2 / n.mean())), 3))
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select(pl.col("time").dt.epoch("ms").alias("end_ms"), "close").collect()
g = daily(m1); n, rv, rq = (g[c].to_numpy() for c in ("n", "rv", "rq"))
R["time, 1 min"] = dict(bars_per_day=round(float(n.mean()), 1), rel_error=round(float(np.median(np.sqrt(2 / 3 * rq) / rv)), 3), rel_error_normal=round(float(np.sqrt(2 / n.mean())), 3))
print(json.dumps(R, indent=1))

labs = ["time, 30 min", "dollar", "range"]
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12, subplot_titles=("Where a day's risk shows up", "How precisely one day's variance is measured"))
fig.add_bar(x=labs, y=[100 * R[l]["share_count"] for l in labs], name="in the number of bars", marker=dict(color=SERIES[0], line=dict(width=0)), row=1, col=1)
fig.add_bar(x=labs, y=[100 * R[l]["share_size"] for l in labs], name="in the size of each bar's move", marker=dict(color=SERIES[1], line=dict(width=0)), row=1, col=1)
fig.update_layout(barmode="stack")
pl_ = labs + ["time, 1 min"]
fig.add_bar(x=pl_, y=[100 * R[l]["rel_error"] for l in pl_], marker=dict(color=[SERIES[2]] * 3 + [MUTED], line=dict(width=0)), showlegend=False,
            text=[f"{100 * R[l]['rel_error']:.0f}%" for l in pl_], textposition="outside", row=1, col=2)
fig.update_yaxes(title_text="% of the day-to-day variation", range=[0, 105], row=1, col=1)
fig.update_yaxes(title_text="relative error of a day's variance, median", range=[0, 32], row=1, col=2)
fig.update_xaxes(tickvals=pl_, ticktext=["time, 30 min", "dollar", "range", "time, 1 min (1,440 bars)"], row=1, col=2)
fig.update_layout(title="Risk on any clock: the same risk, carried by different parts of the bars<br><sup>Five years of BTCUSDT; left: the variation of each day's variance from day to day, split "
                        "into bar count and move size; right: the sampling error of one day's variance, clocks at about 50 bars a day and one-minute bars for comparison</sup>",
                  height=460, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "14_11_risk_on_any_clock", FIG)
(L14_RESULTS / "l14_s6.json").write_text(json.dumps(R, indent=1))
