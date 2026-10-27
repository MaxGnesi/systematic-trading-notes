"""Lecture 16 §7 figures and the capacity table, from l16_s7.json and l16_s7_series.parquet. 16_10: the rule built up step by step, and its two
alternatives: Sharpe ratio in both periods and maximum drawdown. 16_11: cumulative return of the lecture's rule, long-or-flat, and bitcoin held long
scaled to the rule's volatility. Capacity: each trade's size at a given capital, against a minute's and a day's trading, its impact by the square-root
law (Y = 0.5 and 0.9, daily volatility and volume of 2021-2024, Lecture 15 §7), and what the impact costs a year at the rule's turnover."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

R = json.loads((L16_RESULTS / "l16_s7.json").read_text()); S = pl.read_parquet(tape.ROOT / "interim" / "l16_s7_series.parquet")

# ---------------------------------------------------------------- 16_10
order = ["0 plain rule, market orders", "1 + patient entry (the lecture's rule)", "1x longs held in spot", "alternative: sizing by the smoothed risk forecast", "alternative: long or flat"]
lab = ["Plain rule, market orders (§2)", "+ patient entry: the lecture's rule (§5)", "Longs held in spot (§6): not taken", "Alternative: size by the smoothed risk forecast (§4)",
       "Alternative: long or flat"]
cols = [MUTED, SERIES[0], MUTED, SERIES[2], SERIES[2]]
fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.03, subplot_titles=("Sharpe ratio, 2021-2024", "Sharpe ratio, 2025-2026", "Maximum drawdown, 2025-2026"))
for c, (smp, key, f) in enumerate((("2021-2024", "sharpe", 1), ("2025-2026", "sharpe", 1), ("2025-2026", "maxdd", 100)), start=1):
    v = [f * R["variants"][k][smp][key] for k in order]
    fig.add_bar(y=lab[::-1], x=v[::-1], orientation="h", marker=dict(color=cols[::-1], line=dict(width=0)), showlegend=False,
                text=[f"{x:.2f}" if key == "sharpe" else f"{x:.0f}%" for x in v[::-1]], textposition="outside", row=1, col=c)
fig.update_xaxes(range=[0, 1.75], row=1, col=1); fig.update_xaxes(range=[0, 0.8], row=1, col=2); fig.update_xaxes(range=[-22, 0], row=1, col=3)
fig.update_layout(title="The rule built up: the patient entry is the step that pays; the alternatives trade return for steadier risk, or shorts for crisis cover<br><sup>"
                        "BTCUSDT, the rule of §2 (fast spans 1, 2 and 3 days, hourly decisions) after fees, spread and funding</sup>",
                  height=420, width=1200, margin=dict(t=100, l=330))
save_figure(fig, PREFIX + "16_10_rule_built_up", FIG)

# ---------------------------------------------------------------- 16_11
fig = make_subplots(rows=1, cols=1)
for col_, name, c, dash in (("btc_scaled", "bitcoin held long, scaled to the rule's volatility", MUTED, "dot"), ("long_or_flat", "long or flat", SERIES[2], "solid"),
                            ("rule", "the lecture's rule: long and short", SERIES[0], "solid")):
    fig.add_scatter(x=S["t"].to_list(), y=(100 * S[col_].cum_sum()).to_list(), mode="lines", line=dict(color=c, width=2 if dash == "solid" else 1.6, dash=dash), name=name)
fig.add_vrect(x0="2022-01-01", x1="2022-12-31", fillcolor="rgba(232,123,164,0.10)", line_width=0)
fig.add_annotation(x="2022-07-01", y=1, yref="paper", text="2022: bitcoin −64%", showarrow=False, yshift=-8, font=dict(size=11, color=MUTED))
fig.add_vline(x="2025-01-01", line=dict(color=INK, dash="dot", width=1))
fig.add_annotation(x="2025-01-01", y=0, yref="paper", text="2025-2026: no part in any choice", showarrow=False, xanchor="left", xshift=6, yshift=10, font=dict(size=11, color=MUTED))
fig.update_yaxes(title_text="cumulative return, % of capital (sum of returns)")
fig.update_layout(title="In the one bear market of the sample the shorts carried the rule; in the rising years they cost it<br><sup>BTCUSDT, January 2022 to "
                        "September 2026, after fees, spread and funding</sup>", height=460, width=1100, margin=dict(t=100, l=80), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "16_11_equity", FIG)

# ---------------------------------------------------------------- capacity
T = R["trades"]; V, SIG = 13.0e9, 250.0                                          # 2021-2024 medians: daily volume $13bn, daily volatility 2.5% (Lecture 15, §7)
rows = []
for K in (1e7, 1e8, 1e9, 5e9):
    Q = K * T["median_size"]
    imp = {y: y * SIG * np.sqrt(Q / V) for y in (0.5, 0.9)}
    rows.append(dict(capital=K, trade=Q, minutes_of_trading=round(Q / (V / 1440), 2), impact_bp=(round(imp[0.5], 1), round(imp[0.9], 1)),
                     cost_per_year=(round(imp[0.5] * T["turnover_per_year"] / 100, 1), round(imp[0.9] * T["turnover_per_year"] / 100, 1))))
(L16_RESULTS / "l16_capacity.json").write_text(json.dumps(rows, indent=1))
for r in rows: print(r)
