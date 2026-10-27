"""Lecture 16 figure 16_05: the information clock, from l16_plugin.json. Sharpe ratio after all costs by speed for the hourly rule reading its trend
measure from A hourly closes, B dollar bars with an average per bar, C dollar bars with an average that fades by elapsed time; 2021-2024 and 2025-2026;
the plateau shaded; the blend of the plateau speeds marked on the right."""
import json, sys
from pathlib import Path
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

R = json.loads((L16_RESULTS / "l16_plugin.json").read_text())
SP = ["0.5 d", "1 d", "2 d", "3 d", "5 d", "8 d", "13 d", "21 d"]; X = ["12 h", "1 d", "2 d", "3 d", "5 d", "8 d", "13 d", "21 d", "blend 1-3 d"]
V = (("A time bars", "A: hourly closes", SERIES[0], "circle"), ("B dollar bars, per bar", "B: dollar bars, average per bar", SERIES[3], "square"),
     ("C dollar bars, decay by time", "C: dollar bars, average fading by time", SERIES[2], "diamond"))
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("2021-2024", "2025-2026"))
for c, smp in enumerate(("2021-2024", "2025-2026"), start=1):
    for key, lab, col, sym in V:
        fig.add_scatter(x=X[:-1], y=[R[s][key][smp]["sharpe"] for s in SP], mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=8, symbol=sym),
                        name=lab, legendgroup=key, showlegend=(c == 1), row=1, col=c)
        fig.add_scatter(x=[X[-1]], y=[R["blend 1-2-3 d"][key][smp]["sharpe"]], mode="markers", marker=dict(size=12, symbol=sym, color=col, line=dict(width=1.5, color=INK)),
                        showlegend=False, legendgroup=key, row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=X, row=1, col=c)
    fig.add_shape(type="rect", xref=("x" if c == 1 else f"x{c}"), yref=("y domain" if c == 1 else f"y{c} domain"), x0=0.5, x1=3.5, y0=0, y1=1,
                  fillcolor="rgba(27,175,122,0.12)", line_width=0, layer="below")
fig.update_xaxes(title_text="speed: look-back of the fast average")
fig.update_yaxes(title_text="Sharpe ratio after all costs", row=1, col=1)
fig.update_layout(title="Reading the trend from dollar bars: the same with an average that fades by time, worse with one that counts bars<br><sup>The rule decides at "
                        "every hourly close in all three versions; only the information it reads changes. Shaded: the plateau of §2; right: the rule's blend of its speeds</sup>",
                  height=480, width=1150, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "16_05_information_clock", FIG)
print("done")
