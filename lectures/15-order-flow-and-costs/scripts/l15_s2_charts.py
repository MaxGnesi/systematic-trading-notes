"""Lecture 15 §2 charts: impact and after by fifth of flow and regime; the trend x volatility matrix; three release examples and, across all
CPI and Fed releases, whether the first five minutes' flow predicts the next thirty."""
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy import stats
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, event_dates
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
D = tape.ROOT / "interim" / "tape" / "BTCUSDT"

R = {}

# ---------------------------------------------------------------- 1. impact and after, 30-minute windows
fl = json.loads((L15_RESULTS / "l15_flow.json").read_text())["30 min"]
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("During the window: the impact", "The next 30 minutes: what comes back"))
for lab, col in (("calm", SERIES[0]), ("normal", SERIES[1]), ("volatile", SERIES[3])):
    x = [f"{k}" for k in range(1, 6)]
    fig.add_scatter(x=x, y=[fl[lab][f"fifth {k}"]["during_bp"] for k in range(1, 6)], mode="lines+markers", line=dict(color=col, width=2.2), name=f"{lab} hours", legendgroup=lab, row=1, col=1)
    fig.add_scatter(x=x, y=[fl[lab][f"fifth {k}"]["next_bp"] for k in range(1, 6)], mode="lines+markers", line=dict(color=col, width=2.2), showlegend=False, legendgroup=lab,
                    error_y=dict(type="data", array=[1.96 * fl[lab][f"fifth {k}"]["next_se"] for k in range(1, 6)], thickness=1, width=3), row=1, col=2)
for c in (1, 2): fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"), row=1, col=c)
fig.update_xaxes(tickvals=["1", "2", "3", "4", "5"], ticktext=["most selling", "", "balanced", "", "most buying"], title_text="30-minute windows, by net aggressive buying")
fig.update_yaxes(title_text="return, bp", row=1, col=1); fig.update_yaxes(title_text="return, bp (± 95% interval)", row=1, col=2)
fig.update_layout(title="Flow moves the price while it happens; afterwards a small part comes back, mostly in volatile hours<br><sup>Five years of BTCUSDT; volatility regime "
                        "from the last hour against its 28-day median, known in advance</sup>", height=460, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_01_impact_and_after", FIG)

# ---------------------------------------------------------------- 2. the matrix: t-statistics of the continuation after strong flow
mx = json.loads((L15_RESULTS / "l15_flow_matrix.json").read_text())
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12, subplot_titles=("5-minute windows", "30-minute windows"))
rows = ["flow against the trend", "no clear trend", "flow with the trend"]; keys = ["against the trend", "no clear trend", "with the trend"]; cols = ["calm", "normal", "volatile"]
for c, W in enumerate(("5 min", "30 min"), start=1):
    z = [[mx[W][k][v]["t"] for v in cols] for k in keys]
    txt = [[f"{mx[W][k][v]['bp']:+.2f} bp<br>t {mx[W][k][v]['t']:+.1f}" for v in cols] for k in keys]
    fig.add_heatmap(z=z, x=[f"{v} hours" for v in cols], y=rows, text=txt, texttemplate="%{text}", colorscale=[[0, SERIES[3]], [0.5, "#f4f4f4"], [1, SERIES[0]]],
                    zmin=-6, zmax=6, showscale=(c == 2), colorbar=dict(title="t"), row=1, col=c)
fig.update_yaxes(showticklabels=False, row=1, col=2)
fig.update_layout(title="After strong flow, the price comes back reliably only when the flow went with the slower trend, in normal and volatile hours<br><sup>Next window's return "
                        "in the direction of the flow (negative: reversal); colour: t-statistic with days as clusters; trend: past three days' return over its typical size</sup>",
                  height=430, width=1100, margin=dict(t=100, l=170))
save_figure(fig, PREFIX + "15_02_flow_matrix", FIG)

# ---------------------------------------------------------------- 3. releases: three examples, and all CPI and Fed releases
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close", "usd", "signed_usd").collect().sort("time")
def us_dst(d):
    m = date(d.year, 3, 8); s = m + timedelta(days=(6 - m.weekday()) % 7); k = date(d.year, 11, 1); e = k + timedelta(days=(6 - k.weekday()) % 7)
    return s <= d < e
def release_time(x, hh, mm):
    d = date.fromisoformat(x); return datetime(d.year, d.month, d.day, hh + (4 if us_dst(d) else 5), mm)
EX = [("CPI, 10 November 2022", release_time("2022-11-10", 8, 30)), ("CPI, 13 September 2022", release_time("2022-09-13", 8, 30)), ("Fed decision, 21 September 2022", release_time("2022-09-21", 14, 0))]
fig = make_subplots(rows=2, cols=3, shared_xaxes=True, vertical_spacing=0.06, horizontal_spacing=0.06, row_heights=[0.55, 0.45], subplot_titles=[t for t, _ in EX] + ["", "", ""])
for c, (lab, t) in enumerate(EX, start=1):
    w = m1.filter(pl.col("time").is_between(t - timedelta(minutes=10), t + timedelta(minutes=60), closed="left"))
    x = [(tt - t).total_seconds() / 60 for tt in w["time"].to_list()]; p0 = w.filter(pl.col("time") < t)["close"][-1]
    fig.add_scatter(x=x, y=((w["close"] / p0 - 1) * 1e4).to_list(), mode="lines", line=dict(color=INK, width=1.6), showlegend=False, row=1, col=c)
    fig.add_bar(x=x, y=(w["signed_usd"] / 1e6).to_list(), marker=dict(color=[SERIES[0] if v > 0 else SERIES[3] for v in w["signed_usd"].to_list()], line=dict(width=0)), showlegend=False, row=2, col=c)
    for r in (1, 2): fig.add_vline(x=0, line=dict(color=MUTED, dash="dot"), row=r, col=c)
fig.update_yaxes(title_text="price, bp from before", row=1, col=1); fig.update_yaxes(title_text="net buying, $m per minute", row=2, col=1)
fig.update_xaxes(title_text="minutes from the release", row=2)
# all releases: does the first five minutes' net buying predict the next thirty minutes?
rows_ = []
for name, dates, hh, mm in (("CPI", event_dates.CPI, 8, 30), ("Fed", event_dates.FOMC, 14, 0)):
    for x_ in dates:
        t = release_time(x_, hh, mm); w = m1.filter(pl.col("time").is_between(t - timedelta(minutes=1), t + timedelta(minutes=35), closed="left"))
        if w.height < 36: continue
        p_ = w["close"].to_numpy(); first = w.filter(pl.col("time").is_between(t, t + timedelta(minutes=5), closed="left"))
        rows_.append(dict(event=name, flow=float(first["signed_usd"].sum() / first["usd"].sum()), first_bp=float(np.log(p_[5] / p_[0]) * 1e4), next_bp=float(np.log(p_[35] / p_[5]) * 1e4)))
E = pl.DataFrame(rows_)
for name in ("CPI", "Fed"):
    e = E.filter(pl.col("event") == name)
    r_f, p_f = stats.pearsonr(e["flow"], e["next_bp"]); r_m, p_m = stats.pearsonr(e["first_bp"], e["next_bp"])
    R[name] = dict(n=e.height, flow_vs_next=round(float(r_f), 2), p_flow=round(float(p_f), 2), move_vs_next=round(float(r_m), 2), p_move=round(float(p_m), 2))
fig.update_layout(title="Three releases on the tape: the first minutes' one-sided flow, and what followed<br><sup>One-minute closes and net aggressive buying from 10 minutes before "
                        f"to an hour after. Across all releases, the first five minutes' net buying against the next 30 minutes: CPI r = {R['CPI']['flow_vs_next']:+.2f} "
                        f"(p {R['CPI']['p_flow']:.2f}), Fed r = {R['Fed']['flow_vs_next']:+.2f} (p {R['Fed']['p_flow']:.2f})</sup>", height=560, width=1100, margin=dict(t=100))
save_figure(fig, PREFIX + "15_03_releases", FIG)
(L15_RESULTS / "l15_s2_charts.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
