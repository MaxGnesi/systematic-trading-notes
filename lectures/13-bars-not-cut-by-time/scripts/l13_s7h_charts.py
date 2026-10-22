"""Lecture 13 §7 charts: the five hypotheses as forest plots, from l13_s7h.json."""
import json
from pathlib import Path
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import numpy as np
from plotly.subplots import make_subplots
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
J = json.loads((L13_RESULTS / "l13_s7h.json").read_text()); S = J["slots"]
SHORT = {"Tokyo opening hour (9:00 Tokyo)": "Tokyo opening hour", "London opening hour (8:00 London)": "London opening hour",
         "New York opening hour (9:30 New York)": "New York opening hour", "Around the New York close (15:30 New York)": "New York close (15:30-16:30)",
         "New York night (2:00 New York)": "New York night (2:00-3:00)", "US public holiday on a weekday": "US holiday on a weekday",
         "First minute of the hour, funding (00, 08, 16 UTC)": ":00 with funding", "First minute of the hour, other hours": ":00, other hours",
         "First minute of the half hour (:30)": ":30", "First minute of a quarter (:15, :45)": ":15 and :45", "Last minute of the hour (:59)": ":59",
         "US inflation release (CPI, 8:30 New York)": "CPI release", "Fed decision (14:00 New York)": "Fed decision",
         "Quarterly expiry, settlement window (07:30-08:00 UTC)": "Quarterly expiry", "Monthly expiry, settlement window": "Monthly expiry",
         "Weekly expiry, settlement window": "Weekly expiry"}
lab = lambda r: SHORT.get(r["slot"], r["slot"])
RH = list(dict.fromkeys(r["rhythm"] for r in S)); COL = {h: SERIES[i] for i, h in enumerate(RH)}
Y = [lab(r) for r in S][::-1]                                                 # first slot at the top


def finish(fig, ncols):
    """Separators between the rhythms, a filled legend marker per rhythm, one axis title."""
    pos = 0; bounds = []
    for h in RH[::-1][:-1]:
        pos += sum(r["rhythm"] == h for r in S); bounds.append(pos - 0.5)
    for c in range(1, ncols + 1):
        for b in bounds: fig.add_hline(y=b, line=dict(color=MUTED, width=0.6), row=1, col=c)
    for tr in fig.data: tr.showlegend = False
    for h in RH: fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=9, color=COL[h]), name=h, showlegend=True, row=1, col=1)


def ratio(r, k):
    v, c = r[k], r[k + "_ctl"]; se = (v / c) * np.sqrt((r[k + "_se"] / v) ** 2 + (r[k + "_ctl_se"] / c) ** 2)
    return v / c, se


# ---------------------------------------------------------------- H1, H2: activity and volatility against the control
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.03, subplot_titles=("H1 Activity ÷ control", "H2 Size of moves ÷ control"))
for c, k in ((1, "act"), (2, "vol")):
    for h in RH:
        rows = [r for r in S if r["rhythm"] == h]; x, e = zip(*[ratio(r, k) for r in rows])
        filled = [r[k + "_q"] < 0.05 for r in rows]
        fig.add_scatter(x=x, y=[lab(r) for r in rows], mode="markers", error_x=dict(type="data", array=[1.96 * v for v in e], thickness=1.2, width=0, color=COL[h]),
                        marker=dict(size=9, color=[COL[h] if f else "rgba(0,0,0,0)" for f in filled], line=dict(color=COL[h], width=1.5)),
                        name=h, legendgroup=h, showlegend=c == 1, hovertemplate="%{y}: %{x:.2f}<extra></extra>", row=1, col=c)
    fig.add_vline(x=1, line=dict(color=MUTED, dash="dot"), row=1, col=c)
    fig.update_xaxes(type="log", title_text="ratio, log scale (1 = like the control)", row=1, col=c)
fig.update_yaxes(categoryorder="array", categoryarray=Y, showgrid=False); finish(fig, 2)
fig.update_layout(title="Seasonality, H1 and H2: when the market is busy, and whether its moves follow<br><sup>Each slot against its control, ± 95% interval; "
                        "filled: significant after correcting for the 120 tests (Benjamini-Hochberg, 5%), hollow: not</sup>",
                  height=640, width=1100, margin=dict(t=100, l=200), legend=dict(orientation="h", y=-0.12, x=0))
fig.update_layout(legend=dict(orientation="h", y=-0.14, x=0, traceorder="normal"))
save_figure(fig, PREFIX + "13_08_h1_h2_activity_volatility", FIG)

# ---------------------------------------------------------------- H3, H4, H5: flow, direction, follow-through, as distance from chance
def z_diff(r, k): return (r[k] - r[k + "_ctl"]) / np.sqrt(r[k + "_se"] ** 2 + r[k + "_ctl_se"] ** 2)
def z_follow(r): return (np.arctanh(r["follow"]) - np.arctanh(r["follow_ctl"])) / np.sqrt(1 / (r["n"] - 3) + 1 / (r["n_ctl"] - 3))
fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.03,
                    subplot_titles=("H3 Net aggressive buying", "H4 Return in the slot", "H5 Follow-through"))
for c, (zf, q) in enumerate(((lambda r: z_diff(r, "flow"), "flow_q"), (lambda r: z_diff(r, "ret"), "ret_q"), (z_follow, "follow_vs_ctl_q")), start=1):
    for h in RH:
        rows = [r for r in S if r["rhythm"] == h]
        fig.add_scatter(x=[zf(r) for r in rows], y=[lab(r) for r in rows], mode="markers",
                        marker=dict(size=9, color=[COL[h] if r[q] < 0.05 else "rgba(0,0,0,0)" for r in rows], line=dict(color=COL[h], width=1.5)),
                        name=h, legendgroup=h, showlegend=c == 1, hovertemplate="%{y}: %{x:.1f}<extra></extra>", row=1, col=c)
    for v in (-1.96, 1.96): fig.add_vline(x=v, line=dict(color=MUTED, dash="dot", width=1), row=1, col=c)
    fig.add_vline(x=0, line=dict(color=INK, width=1), row=1, col=c)
    fig.update_xaxes(range=[-8, 8], row=1, col=c)
fig.update_yaxes(categoryorder="array", categoryarray=Y, showgrid=False); finish(fig, 3)
fig.add_annotation(text="difference from the control, in standard errors", xref="paper", yref="paper", x=0.5, y=-0.11, showarrow=False, font=dict(size=13))
fig.update_layout(title="Seasonality, H3 to H5: is there one-sided flow, a direction, a move that carries on?<br><sup>Distance from the control in standard errors; "
                        "inside the dotted lines (± 1.96) is what chance gives. Filled: significant after correcting for the 120 tests; points beyond ± 8 are drawn at the edge</sup>",
                  height=640, width=1100, margin=dict(t=100, l=200), legend=dict(orientation="h", y=-0.12, x=0))
for tr in fig.data:
    if tr.x and tr.x[0] is not None: tr.x = tuple(float(np.clip(v, -7.9, 7.9)) for v in tr.x)
fig.update_layout(legend=dict(orientation="h", y=-0.17, x=0, traceorder="normal"))
save_figure(fig, PREFIX + "13_09_h3_h5_flow_direction_follow", FIG)
