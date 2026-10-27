"""Lecture 16 §2: the speed curve of the plain rule on hourly candles, with the settings of every later section (l16_buildup.py: plain sizing, market
orders, buffer, funding), fast spans from 3 hours to 3 weeks; then figures 16_03 (speed curve) and 16_04 (candle size, from l16_trend_bars.json)."""
import json, sys
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

SPEEDS = [0.125, 0.25, 0.5, 1, 2, 3, 5, 8, 13, 21]
R = {float(k): v for k, v in json.loads((L16_RESULTS / "l16_s2.json").read_text()).items()} if (L16_RESULTS / "l16_s2.json").exists() else None
if R is None:
    import l16_buildup as B
    R = {}
    for fd in SPEEDS:
        net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF, False, fc=B.forecast(B.dp_sd, [fd]))
        R[fd] = {"2021-2024": B.stats(net, parts, B.IS & B.live), "2025-2026": B.stats(net, parts, ~B.IS)}
        g = parts["gross"]; m = B.IS & B.live
        R[fd]["gross_sharpe_2021_2024"] = round(float(g[m].mean() / g[m].std() * np.sqrt(B.PY)), 2)
    (L16_RESULTS / "l16_s2.json").write_text(json.dumps({str(k): v for k, v in R.items()}, indent=1))

LAB = {0.125: "3 h", 0.25: "6 h", 0.5: "12 h", 1: "1 d", 2: "2 d", 3: "3 d", 5: "5 d", 8: "8 d", 13: "13 d", 21: "21 d"}
x = [LAB[fd] for fd in SPEEDS]                                                # speeds spaced proportionally, shown evenly
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=("Sharpe ratio after all costs", "What trading costs, % of capital a year"))
fig.add_scatter(x=x, y=[R[f]["gross_sharpe_2021_2024"] for f in SPEEDS], mode="lines+markers", line=dict(color=MUTED, width=1.6, dash="dot"), marker=dict(size=7),
                name="2021-2024, before costs", row=1, col=1)
fig.add_scatter(x=x, y=[R[f]["2021-2024"]["sharpe"] for f in SPEEDS], mode="lines+markers", line=dict(color=SERIES[0], width=2.4), marker=dict(size=9),
                name="2021-2024, after costs (speeds chosen here)", row=1, col=1)
fig.add_scatter(x=x, y=[R[f]["2025-2026"]["sharpe"] for f in SPEEDS], mode="lines+markers", line=dict(color=SERIES[1], width=2.4), marker=dict(size=9, symbol="diamond"),
                name="2025-2026, after costs (no part in any choice)", row=1, col=1)
fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=1)
fig.add_bar(x=x, y=[100 * R[f]["2021-2024"]["cost"] for f in SPEEDS], marker=dict(color=SERIES[3], line=dict(width=0)), showlegend=False,
            text=[f"{100 * R[f]['2021-2024']['cost']:.1f}%" for f in SPEEDS], textposition="outside", textfont=dict(size=11), row=1, col=2)
for c in (1, 2):
    fig.add_shape(type="rect", xref=("x" if c == 1 else f"x{c}"), yref=("y domain" if c == 1 else f"y{c} domain"), x0=2.5, x1=5.5, y0=0, y1=1, fillcolor="rgba(27,175,122,0.13)", line_width=0, layer="below")
    fig.update_xaxes(type="category", title_text="speed: look-back of the fast average", row=1, col=c)
fig.update_yaxes(title_text="Sharpe ratio", row=1, col=1); fig.update_yaxes(title_text="% a year", range=[0, 33], row=1, col=2)
fig.add_annotation(x=4, y=1.02, xref="x", yref="paper", text="the plateau", showarrow=False, font=dict(size=12, color=SERIES[2]))
fig.update_layout(title="On BTCUSDT the trend rule works at speeds of one to three days; faster, costs eat it; slower, it fades<br><sup>The rule of Part II on hourly "
                        "candles, five years of BTCUSDT, market orders (5 bp fee and the spread) and funding at every settlement</sup>",
                  height=480, width=1150, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "16_03_speed_curve", FIG)

TB = json.loads((L16_RESULTS / "l16_trend_bars.json").read_text()); CANDLES = ["5 min", "15 min", "1 hour", "4 hours", "1 day"]
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("2021-2024", "2025-2026"))
for c, smp in enumerate(("2021-2024", "2025-2026"), start=1):
    for fh, col in (("24 h", SERIES[0]), ("48 h", SERIES[1]), ("96 h", SERIES[2])):
        ys = [TB[cd][fh][smp]["sharpe"] if fh in TB[cd] else None for cd in CANDLES]
        fig.add_scatter(x=CANDLES, y=ys, mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=9), name=f"speed {int(fh[:-2]) // 24} day{'s' if fh != '24 h' else ''}",
                        legendgroup=fh, showlegend=(c == 1), row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_xaxes(title_text="candle: how often the rule looks")
fig.update_yaxes(title_text="Sharpe ratio after all costs", row=1, col=1)
fig.update_layout(title="How often to look: from five minutes to four hours it hardly matters; once a day is too seldom<br><sup>The same rule, the same speeds in "
                        "hours of history, on candles of different lengths; market orders and funding</sup>",
                  height=450, width=1100, margin=dict(t=100, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "16_04_candle_size", FIG)
for f in SPEEDS: print(LAB[f], R[f]["2021-2024"]["sharpe"], R[f]["2025-2026"]["sharpe"], R[f]["gross_sharpe_2021_2024"], R[f]["2021-2024"]["cost"])
