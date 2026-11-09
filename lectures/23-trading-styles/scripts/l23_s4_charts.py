"""Lecture 23 §4, the figure: the 24-hour profiles of the style shares in and out of sample (H13), the shares by third of volatility out of sample (H14), and the shares day by day.
From L23_RESULTS/s4_tests.json (written by l23_s4.py --tests). Output: figures/23_s4_when.png."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); R = json.loads((L.RESULTS / "s4_tests.json").read_text(encoding="utf-8"))
STY = [("sliced", "sliced (H12's runs)", SERIES[2]), ("sniper", "sniper-like (H10)", SERIES[3]), ("clock", "clock-like (extra size after whole minutes)", SERIES[1])]
fig = make_subplots(rows=2, cols=3, specs=[[{}, {}, {}], [{}, {"colspan": 2}, None]], vertical_spacing=0.2, horizontal_spacing=0.07,
                    subplot_titles=[f"H13: {n}, by hour" for _, n, _ in STY] + ["H14: by volatility of the hour, out of sample", "The shares day by day"])
for c, (s, n, col) in enumerate(STY):
    fig.add_scatter(x=list(range(24)), y=100 * np.array(R["profile_in"][s]), mode="lines+markers", line=dict(color=MUTED, width=2), marker=dict(size=5), name="in sample, 20 Sep - 9 Oct", showlegend=c == 0, legendgroup="in", row=1, col=c + 1)
    fig.add_scatter(x=list(range(24)), y=100 * np.array(R["profile_out"][s]), mode="lines+markers", line=dict(color=INK, width=2), marker=dict(size=5), name="out of sample, 11 Oct - 3 Nov", showlegend=c == 0, legendgroup="out", row=1, col=c + 1)
    fig.update_xaxes(title_text="hour of the day, UTC", row=1, col=c + 1); fig.update_yaxes(title_text="% of taker size" if c == 0 else None, row=1, col=c + 1)
    fig.add_bar(x=["least volatile third", "middle third", "most volatile third"], y=100 * np.array(R["H14"][s]["by_third"]), marker_color=col, name=n, legendgroup=s, row=2, col=1)
    fig.add_scatter(x=[d["day"] for d in R["daily"]], y=[100 * d[s] for d in R["daily"]], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=5), name=n, showlegend=False, legendgroup=s, row=2, col=2)
fig.add_vrect(x0="2025-10-11", x1=R["daily"][-1]["day"], fillcolor=SERIES[0], opacity=0.07, line_width=0, row=2, col=2)
fig.update_yaxes(title_text="% of taker size", row=2, col=1); fig.update_yaxes(title_text="% of taker size", row=2, col=2); fig.update_xaxes(title_text="day (shaded: out of sample)", row=2, col=2)
fig.update_layout(title="When, and in what conditions: the style shares by hour, by volatility and by day<br><sup>Bybit BTCUSDT perpetual, 20 September - 3 November 2025. Shares of taker size; each order counted once, sliced first, then sniper-like</sup>",
                  barmode="group", height=950, width=1500, margin=dict(t=110, l=70, r=30, b=120), legend=dict(orientation="h", y=-0.1, x=0))
save_figure(fig, L.PREFIX + "23_s4_when", L.FIG)
