"""Lecture 17 figure 17_05: the size profile, stylised, no data. A ladder of 8 levels on each side, the same capital in a full ladder for every shape
(average size 1 unit). (a) size at each level; (b) units held after the price has fallen k steps from the centre; (c) what one swing pays: the price
falls k steps and returns, every level filled on the way down sold one step higher; (d) what a run costs: the price falls k steps and the units are
closed there, against their own buy prices; the last point is the stop, one step beyond the last level. Money in steps x units (one round trip of an
average unit = 1). Shapes as in l17_grid.shape (Lecture 16, §8)."""
import sys
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
import l17_grid as g
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

N = 8; k = np.arange(1, N + 1); ks = np.arange(1, N + 2)
COL = {"uniform": MUTED, "V-shaped": SERIES[1], "bell-shaped": SERIES[2], "bimodal": SERIES[0]}
NAME = {"uniform": "uniform", "V-shaped": "V-shaped: more size further out", "bell-shaped": "bell-shaped: more size near the centre", "bimodal": "bimodal: a bell on each side, a few levels from the price"}
fig = make_subplots(rows=2, cols=2, vertical_spacing=0.17, horizontal_spacing=0.09,
                    subplot_titles=("(a) Size at each level, below and above the price", "(b) Units held after a fall of k steps: also what the swing earns back",
                                    "(c) What a run costs: down k steps, closed there", "(d) Swings of k steps needed to pay for one stop"))
for j, sh in enumerate(COL):
    w = g.shape(sh, N)[1:]
    held = np.cumsum(w); swing = held.copy()                                   # every level filled on the way down earns one step on the way back
    run = np.array([(w[:min(d, N)] * (d - k[:min(d, N)])).sum() for d in ks])   # units bought at levels 1..d, closed d steps below the centre
    show = dict(name=NAME[sh], legendgroup=sh)
    fig.add_bar(x=np.r_[-k[::-1], k] + (j - 1.5) * 0.2, y=np.r_[w[::-1], w], width=0.19, marker=dict(color=COL[sh]), showlegend=True, **show, row=1, col=1)
    fig.add_scatter(x=k, y=held, mode="lines+markers", line=dict(color=COL[sh], width=2, shape="hv"), marker=dict(size=7), showlegend=False, **show, row=1, col=2)
    fig.add_scatter(x=ks, y=-run, mode="lines+markers", line=dict(color=COL[sh], width=2), marker=dict(size=7), showlegend=False, **show, row=2, col=1)
    fig.add_scatter(x=k, y=run[-1] / swing, mode="lines+markers", line=dict(color=COL[sh], width=2), marker=dict(size=7), showlegend=False, **show, row=2, col=2)
fig.add_annotation(x=N + 1, y=-48.5, text="the stop", showarrow=True, ax=-50, ay=0, font=dict(size=11, color=MUTED), row=2, col=1)
fig.update_xaxes(title_text="level, steps from the centre (− below, + above)", dtick=1, row=1, col=1); fig.update_xaxes(title_text="fall, steps", dtick=1, row=1, col=2)
fig.update_xaxes(title_text="depth of the run, steps", dtick=1, row=2, col=1); fig.update_xaxes(title_text="depth of the swing, steps", dtick=1, row=2, col=2)
fig.update_yaxes(title_text="units", row=1, col=1); fig.update_yaxes(title_text="units = steps × units", row=1, col=2)
fig.update_yaxes(title_text="steps × units", row=2, col=1); fig.update_yaxes(title_text="swings", rangemode="tozero", row=2, col=2)
fig.update_layout(title="Four ways to spread the same capital: the bell bets on small swings, the bimodal on medium ones, the V on deep ones; the more near the price, the more a run costs<br>"
                        "<sup>A schematic, not data: 8 levels on each side; panels (b) to (d) show the side below, the side above is its mirror image, the same capital in a full ladder for every shape. "
                        "Money in steps × units: one round trip of an average-sized unit earns 1</sup>",
                  height=760, width=1200, margin=dict(t=110, l=70, b=90), legend=dict(orientation="h", y=-0.12, x=0))
save_figure(fig, PREFIX + "17_05_shapes", FIG)
