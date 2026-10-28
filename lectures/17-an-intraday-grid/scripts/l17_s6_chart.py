"""Lecture 17 figure 17_09, from l17_s6.json. (a) The trend rule alone and with 10% or 25% of the weight in the grid (scaled to the trend rule's
volatility), Sharpe ratio after costs, 2021-24 and 2025-26. (b) The grid's daily net result by the size of the trend forecast at the start of the day
(flat / medium / strong, thirds cut on 2021-24), 95% intervals."""
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

O = pl.DataFrame(json.loads((L17_RESULTS / "l17_s6.json").read_text())).filter(pl.col("rule") == "skew, sign")
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("(a) The trend rule with part of its weight in the grid",
                                                                              "(b) The grid by the size of the trend forecast, known in advance"))
SC = {50: SERIES[1], 100: SERIES[0], 200: SERIES[2]}
for st, c in SC.items():
    for p, dash in (("2021-24", None), ("2025-26", "dot")):
        r = O.filter((pl.col("step") == st) & (pl.col("p") == p)).row(0, named=True)
        fig.add_scatter(x=[0, 10, 25], y=[r["sr_trend"], r["w10"], r["w25"]], mode="lines+markers", line=dict(color=c, width=2, dash=dash), marker=dict(size=8),
                        name=f"grid step {st} bp", showlegend=(p == "2021-24"), legendgroup=str(st), row=1, col=1)
        x = np.arange(3) + {50: -0.2, 100: 0.0, 200: 0.2}[st] + (0.05 if p == "2025-26" else -0.05)
        y = [r["grid_flat"], r["grid_medium"], r["grid_strong"]]; e = [1.96 * r["se_flat"], 1.96 * r.get("se_medium", r["se_flat"]), 1.96 * r["se_strong"]]
        fig.add_scatter(x=x, y=y, mode="markers", marker=dict(color=c, size=9, opacity=1 if p == "2021-24" else 0.45),
                        error_y=dict(array=e, color=c, thickness=1.2, width=0), showlegend=False, legendgroup=str(st), row=1, col=2)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=1); fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=2)
fig.update_xaxes(title_text="share of the weight in the grid, %", tickvals=[0, 10, 25], row=1, col=1)
fig.update_yaxes(title_text="Sharpe ratio of the portfolio", row=1, col=1)
fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["flat", "medium", "strong"], title_text="trend forecast at the start of the day (thirds, cut on 2021-24)", row=1, col=2)
fig.update_yaxes(title_text="grid net, % of capital per day", row=1, col=2)
fig.update_layout(title="The grid does not help the trend rule: every share of weight in it lowers the Sharpe ratio, and it does not earn when the trend rule is flat"
                        "<br><sup>BTCUSDT, after costs. Trend rule: Lecture 16, step 2. Grid: volatility switch + lean with the trend, ladder 200 bp each way. "
                        "(a) solid 2021-24, dotted 2025-26. (b) full colour 2021-24, pale 2025-26, 95% intervals</sup>",
                  height=540, width=1250, margin=dict(t=110, l=70, b=110), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "17_09_with_trend", FIG)
