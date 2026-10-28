"""Lecture 17 figure 17_08, from l17_s5_tests.json. (a) Q1, does a rule cut losses: the daily net result with the rule minus its baseline, % of capital,
with 95% intervals, 2021-24 (full colour) and 2025-26 (pale), by step; a ring marks a result that survives the Benjamini-Hochberg correction (q < 0.05).
(b) The correction drawn: the sorted p-values of each question against the line 0.05 x i / m; a test counts if it lies below the line, or any later
test does."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
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
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

J = json.loads((L17_RESULTS / "l17_s5_tests.json").read_text()); Q1 = pl.DataFrame(J["q1"]); Q2 = pl.DataFrame(J["q2"])
RULES = [("off above 1.5", "switch off above 1.5x", "#a9c8ef"), ("off above 2.0", "switch off above 2x", "#4a88d8"), ("off above 3.0", "switch off above 3x", "#173f75"),
         ("skew, sign", "lean with the trend", SERIES[1]), ("skew, strong", "lean, strong trends only", SERIES[4]),
         ("off in strong trend", "off in strong trends", SERIES[3]), ("channel", "the channel", MUTED)]
fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.09,
                    subplot_titles=("(a) Does the rule cut losses? Net with the rule minus its baseline", "(b) The Benjamini–Hochberg correction, drawn"))
steps = [25, 50, 100, 200]
for j, (key, nm, c) in enumerate(RULES):
    d = Q1.filter(pl.col("rule") == key).sort("step")
    x = np.arange(len(steps)) + (j - 3) * 0.11
    se = (d["diff"] / d["t_diff"]).to_numpy(); se_o = (d["diff_oos"] / d["t_diff_oos"]).to_numpy()
    fig.add_scatter(x=x - 0.025, y=d["diff"], mode="markers", marker=dict(color=c, size=9, line=dict(color=INK, width=np.where(d["bh"].to_numpy(), 2, 0))),
                    error_y=dict(array=1.96 * se, color=c, thickness=1.2, width=0), name=nm, legendgroup=key, row=1, col=1)
    fig.add_scatter(x=x + 0.025, y=d["diff_oos"], mode="markers", marker=dict(color=c, size=7, opacity=0.45), error_y=dict(array=1.96 * se_o, color=c, thickness=1, width=0),
                    showlegend=False, legendgroup=key, row=1, col=1)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=1)
for q, nm, c in ((Q1, "cut losses: 28 tests", INK), (Q2, "an edge: 56 tests", "#8268d2")):
    p = np.sort(q["pv"].to_numpy()); m = len(p); i = np.arange(1, m + 1)
    fig.add_scatter(x=i / m, y=p, mode="markers", marker=dict(color=c, size=7), name=f"sorted p-values, {nm}", row=1, col=2)
fig.add_scatter(x=[0, 1], y=[0, 0.05], mode="lines", line=dict(color=MUTED, width=1.5, dash="dash"), name="the bar: 0.05 × i / m", row=1, col=2)
fig.update_xaxes(tickvals=list(range(4)), ticktext=[f"{s} bp" for s in steps], title_text="step", row=1, col=1)
fig.update_yaxes(title_text="% of capital per day", row=1, col=1)
fig.update_xaxes(title_text="rank of the test ÷ number of tests (i / m)", range=[0, 1], row=1, col=2)
fig.update_yaxes(title_text="p-value", range=[0, 0.5], row=1, col=2)
fig.update_layout(title="Known in advance: the volatility switch and leaning with the trend cut the grid's losses; nothing creates an edge<br><sup>BTCUSDT; tests run on "
                        "2021-24, 2025-26 as the check. (a) Full colour 2021-24, pale 2025-26, whiskers 95% intervals, a dark ring where the result survives the correction (q < 0.05). "
                        "(b) 2021-24 p-values, one-sided</sup>", height=560, width=1250, margin=dict(t=110, l=70, b=130), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "17_08_known_in_advance", FIG)
