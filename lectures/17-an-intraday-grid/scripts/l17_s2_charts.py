"""Lecture 17 figures 17_02 and 17_03, from l17_mc.json and l17_mc_calib.json (Monte Carlo, 1,000 simulated days each, no costs).
17_02: on a price with no pattern the grid's profit is minus its gap; profit + gap is what the path's pattern earns. Paired grid, 5 levels a side,
stop + restart, daily close; per unit of size, bp of the starting price per day; bars with 95% intervals.
17_03: run episodes. Top: one simulated day of the model calibrated to the tape (10% of the time in runs), runs shaded, with the hidden drift.
Bottom: the grid's profit by the share of time in runs, every model with the tape's reversion (variance ratio 0.90) and volatility (3% a day):
always on, and switched off during runs seen with a lag of 0, 5, 15 or 30 minutes."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()

MC = json.loads((L17_RESULTS / "l17_mc.json").read_text()); CAL = json.loads((L17_RESULTS / "l17_mc_calib.json").read_text())

# 17_02
SC = [("random walk", "random walk"), ("random walk + small jumps", "+ small jumps<br>10 a day, 40 bp"), ("random walk + large jumps", "+ large jumps<br>2 a day, 120 bp"),
      ("control: reverting part", "control:<br>swings"), ("control: trend days", "control:<br>a trend day")]
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("step 25 bp", "step 50 bp"))
for c, st in enumerate((25, 50), start=1):
    rows = [MC[f"step {st} bp | stop+restart | {k}"] for k, _ in SC]; lab = [l for _, l in SC]
    fig.add_bar(x=lab, y=[r["mean_bp"] for r in rows], error_y=dict(array=[1.96 * r["se"] for r in rows], color=INK, thickness=1),
                marker=dict(color=SERIES[0]), name="the grid's profit", showlegend=c == 1, row=1, col=c)
    fig.add_bar(x=lab, y=[-r["gap_bp"] for r in rows], marker=dict(color=MUTED), name="minus the gap: what its fills paid above the market", showlegend=c == 1, row=1, col=c)
    fig.add_bar(x=lab, y=[r["mean_bp"] + r["gap_bp"] for r in rows], error_y=dict(array=[1.96 * r["sum_se"] for r in rows], color=INK, thickness=1),
                marker=dict(color=SERIES[1]), name="profit + gap: what the path's pattern earned", showlegend=c == 1, row=1, col=c)
    fig.add_vrect(x0=2.5, x1=4.5, fillcolor=GRID, opacity=0.35, line_width=0, layer="below", row=1, col=c)
fig.update_yaxes(title_text="bp per day, per unit", zeroline=True, zerolinecolor=MUTED, row=1, col=1)
fig.update_layout(title="On a price with no pattern, the grid earns exactly minus its gap; jumps only widen the gap<br><sup>Monte Carlo, 1,000 simulated days "
                        "of one-second steps, 3% daily volatility; paired grid, 5 levels a side, stop + restart, daily close, no costs. Shaded: two controls with a pattern. "
                        "Whiskers: 95% intervals</sup>", barmode="group", height=520, width=1200, margin=dict(t=110, l=70, b=110),
                  legend=dict(orientation="h", y=-0.22, x=0))
fig.update_xaxes(tickangle=0)
save_figure(fig, PREFIX + "17_02_martingale", FIG)

# 17_03: one simulated day of the calibrated model (same equations as l17_mc_calib.day), and the two Monte Carlo views of runs
RU = json.loads((L17_RESULTS / "l17_mc_runs.json").read_text())
c = next(r for r in CAL if abs(r["p_run"] - 0.10) < 1e-9); T, RUN, HL = 86_400, 1800.0, 600.0
rng = np.random.default_rng(14)                                                 # a day with 10.2% of its time in runs, close to the model's 10%
a = np.exp(-np.log(2) / HL); b = c["drift"] * np.sqrt(1 - a * a); e = c["ou"] * np.sqrt(1 - a * a); sig_s = c["sig"] / np.sqrt(T)
p_exit = 1 / RUN; p_enter = p_exit * 0.10 / 0.90
run = False; w = 1.0; d = y = 0.0; P = np.empty(T); R = np.zeros(T, bool); Dr = np.empty(T)
u1, z = rng.random(T), rng.standard_normal((T, 3))
for t_ in range(T):
    run = (not (u1[t_] < p_exit)) if run else (u1[t_] < p_enter)
    d = a * d + b * z[t_, 0] if run else a * d
    w += d + sig_s * z[t_, 1]
    if not run: y = a * y + e * z[t_, 2]
    P[t_] = w + y; R[t_] = run; Dr[t_] = d
h = np.arange(T) / 3600
fig = make_subplots(rows=3, cols=2, row_heights=[0.36, 0.16, 0.48], vertical_spacing=0.12, horizontal_spacing=0.08,
                    specs=[[{"colspan": 2}, None], [{"colspan": 2}, None], [{}, {}]],
                    subplot_titles=(f"One simulated day of the calibrated model ({R.mean():.1%} of its time in runs, shaded)",
                                    "The hidden drift, bp per minute: it builds during a run and fades after it",
                                    "Swings held fixed: runs cost the grid", "The tape's reversion held fixed: how it is split decides"))
fig.add_scatter(x=h[::10], y=(P[::10] - 1) * 100, mode="lines", line=dict(color=INK, width=1.2), name="price, % from the open", row=1, col=1)
fig.add_scatter(x=h[::10], y=Dr[::10] * 60 * 1e4, mode="lines", line=dict(color=SERIES[1], width=1.5), name="hidden drift", row=2, col=1)
edges = np.flatnonzero(np.diff(np.r_[0, R.astype(int), 0]))
for s0, s1 in zip(edges[::2], edges[1::2]):
    for r_ in (1, 2):
        fig.add_vrect(x0=s0 / 3600, x1=s1 / 3600, fillcolor=SERIES[1], opacity=0.18, line_width=0, layer="below", row=r_, col=1)
for ou, col, nm in ((0.0, MUTED, "random walk + runs"), (0.002, INK, "random walk + swings (20 bp, half-life 10 min) + runs")):
    rr = [r for r in RU if r["ou_sd"] == ou]
    fig.add_scatter(x=[r["p_run"] * 100 for r in rr], y=[r["mean_bp"] for r in rr], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=8),
                    name=nm, row=3, col=1)
px = [r["p_run"] * 100 for r in CAL]
fig.add_scatter(x=px, y=[r["grid"] for r in CAL], mode="lines+markers", line=dict(color=INK, width=2, dash="dash"), marker=dict(size=8),
                name="calibrated: grid always on", row=3, col=2)
for lag, col, nm in ((0, SERIES[0], "calibrated: off in runs, seen at once"), (300, SERIES[2], "seen 5 min late"), (900, SERIES[4], "seen 15 min late"),
                     (1800, SERIES[3], "seen 30 min late")):
    rr = [r for r in CAL if f"switch_{lag}" in r]
    fig.add_scatter(x=[r["p_run"] * 100 for r in rr], y=[r[f"switch_{lag}"] for r in rr], mode="lines+markers",
                    line=dict(color=col, width=2, dash="solid" if lag == 0 else "dot"), marker=dict(size=8), name=nm, row=3, col=2)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=3, col=1)
fig.update_yaxes(title_text="%", row=1, col=1); fig.update_yaxes(title_text="bp/min", row=2, col=1)
fig.update_yaxes(title_text="bp per day, per unit", row=3, col=1); fig.update_yaxes(rangemode="tozero", row=3, col=2)
fig.update_xaxes(range=[0, 24], tickvals=list(range(0, 25, 2)), row=1, col=1)
fig.update_xaxes(title_text="hour of the simulated day", range=[0, 24], tickvals=list(range(0, 25, 2)), row=2, col=1)
fig.update_xaxes(title_text="share of time in runs, %", row=3, col=1); fig.update_xaxes(title_text="share of time in runs, %", tickvals=px, row=3, col=2)
fig.update_layout(title="Runs are jumps spread over minutes: they cost the grid, and the same average reversion pays very differently depending on how often the market runs<br>"
                        "<sup>Monte Carlo, 1,000 simulated days per point; runs last 30 min on average and carry a hidden drift with a 10-minute half-life.<br>"
                        "Right: every model has the tape's reversion (variance ratio 0.90) and volatility (3% a day). Grid: step 25 bp, 5 levels a side, stop + restart, no costs</sup>",
                  height=1000, width=1200, margin=dict(t=130, l=70, b=60), legend=dict(orientation="h", y=-0.08, x=0))
save_figure(fig, PREFIX + "17_03_runs", FIG)
print("runs share of the drawn day:", R.mean())
