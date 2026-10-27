"""Lecture 16 figure 16_12: the classic two-sided grid, schematic. Left: a ladder of levels and one price path; a round trip (a buy filled, then its paired
sell one level up) and a run downward that fills buy after buy and leaves inventory. Right: three size profiles across the levels: uniform, V-shaped
(more size further from the centre) and bell-shaped (more size near the centre)."""
import sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

lv = np.arange(-4, 5)                                                            # levels, in steps from the centre
t = np.linspace(0, 10, 1000)
# a swing that dips through level -1 and comes back through level 0, then a run down through levels -1 to -4
path = np.where(t < 3.2, 0.3 - 1.5 * np.sin(np.pi * t / 3.2) ** 2 + 0.25 * np.sin(np.pi * t / 1.6) * (t > 1.6), np.nan)
run = t >= 3.2; path[run] = 0.3 - 0.75 * (t[run] - 3.2) + 0.12 * np.sin(4.5 * (t[run] - 3.2))
fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.1,
                    subplot_titles=("A paired grid: a round trip, then a run", "How much to put at each level: three shapes"))
for l in lv:
    col = SERIES[0] if l < 0 else (SERIES[3] if l > 0 else MUTED)
    fig.add_shape(type="line", xref="x domain", yref="y", x0=0, x1=1, y0=l, y1=l, line=dict(color=col, width=1, dash="dot" if l == 0 else "solid"), layer="below")
fig.add_scatter(x=t, y=path, mode="lines", line=dict(color=INK, width=2), name="price", row=1, col=1)


def cross(level, down, after):
    """First time after `after` at which the path crosses `level` (downward or upward)."""
    for i in range(1, len(t)):
        if t[i] <= after: continue
        if (down and path[i - 1] > level >= path[i]) or (not down and path[i - 1] < level <= path[i]): return t[i]
    return None


tb = cross(-1, True, 0); ts = cross(0, False, tb)
fig.add_scatter(x=[tb], y=[-1], mode="markers", marker=dict(color=SERIES[0], size=13, symbol="triangle-up"), name="buy filled", row=1, col=1)
fig.add_scatter(x=[ts], y=[0], mode="markers", marker=dict(color=SERIES[3], size=13, symbol="triangle-down"), name="its paired sell, one step up, filled: one step earned", row=1, col=1)
for k, l in enumerate((-1, -2, -3, -4)):
    xi = cross(l, True, 3.2)
    fig.add_scatter(x=[xi], y=[l], mode="markers", marker=dict(color=SERIES[0], size=13, symbol="triangle-up"), showlegend=False, row=1, col=1)
    fig.add_scatter(x=[xi, 10], y=[l + 1, l + 1], mode="lines", line=dict(color=SERIES[3], width=1.5, dash="dash"), showlegend=(k == 0),
                    name="paired sells still waiting: the inventory left by the run", row=1, col=1)
fig.add_annotation(x=1.6, y=0.75, text="swing: a round trip", showarrow=False, font=dict(size=11, color=MUTED), row=1, col=1)
fig.add_annotation(x=7.8, y=-1.2, text="run: buy after buy", showarrow=False, font=dict(size=11, color=MUTED), row=1, col=1)
fig.update_yaxes(title_text="level, in steps from the centre", tickvals=list(lv), row=1, col=1)
fig.update_xaxes(showticklabels=False, title_text="time", row=1, col=1)
shapes = {"uniform": np.ones(len(lv)), "V-shaped: more further away": 0.4 + 0.3 * np.abs(lv), "bell-shaped: more near the centre": np.exp(-(lv / 2.2) ** 2) * 1.6 + 0.1}
for (name, w), col, off in zip(shapes.items(), (MUTED, SERIES[1], SERIES[2]), (-0.25, 0.0, 0.25)):
    w = np.where(lv == 0, 0, w); w = w / w.sum() * (len(lv) - 1)
    fig.add_bar(y=lv + off, x=w, orientation="h", width=0.22, marker=dict(color=col, line=dict(width=0)), name=name, row=1, col=2)
fig.update_yaxes(tickvals=list(lv), row=1, col=2); fig.update_xaxes(title_text="size at the level (average = 1)", row=1, col=2)
fig.update_layout(title="The classic grid: buy orders below the price, sell orders above, each re-armed only after its paired trade<br><sup>A schematic, not data. "
                        "Blue levels hold buy orders, pink levels sell orders; the step between levels is set from volatility (Lecture 17)</sup>",
                  height=500, width=1200, margin=dict(t=110, l=70, b=120), legend=dict(orientation="h", y=-0.25, x=0))
save_figure(fig, PREFIX + "16_12_grid", FIG)
print("done")
