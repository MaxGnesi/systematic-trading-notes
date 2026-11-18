"""Lecture 13 §3.3 figure from results/regimes.json: stock-bond correlation by regime (assets, trend streams) and the volatility a
total scaled to 10% in 2003-2006 would carry in each regime. Usage: python l27_regimes_chart.py"""
import json, sys
import os
from pathlib import Path

from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import MUTED, SERIES, apply_theme, save_figure  # noqa: E402

J = json.loads((Path(os.environ.get("L27_RESULTS", HERE.parent / "results")) / "regimes.json").read_text(encoding="utf-8"))
names = [k for k in J["windows"] if not k.startswith("2023")]
short = [n.split(" ", 1)[0] + "  " + n.split(" ", 1)[1] for n in names]
apply_theme()
f = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                  subplot_titles=("Stock-bond correlation", "Volatility of a total scaled to 10% in 2003-2006"))
f.add_bar(y=short, x=[J["windows"][n]["stock_bond_assets"] for n in names], orientation="h", name="Assets", marker_color=MUTED, row=1, col=1)
f.add_bar(y=short, x=[J["windows"][n]["stock_bond_trend"] for n in names], orientation="h", name="Trend streams", marker_color=SERIES[0], row=1, col=1)
v = [J["stress_pairs"][n]["2003-2006 calm"] for n in names]
f.add_bar(y=short, x=v, orientation="h", name="Total, trend streams", marker_color=SERIES[1], showlegend=False, row=1, col=2,
          text=[f"{x:.1f}%" for x in v], textposition="outside", cliponaxis=False)
f.add_vline(x=10, line=dict(color="#0b0b0b", dash="dot", width=1.5), row=1, col=2)
f.add_vline(x=0, line=dict(color="#0b0b0b", width=1), row=1, col=1)
f.update_yaxes(autorange="reversed")
f.update_xaxes(range=[-0.8, 0.5], row=1, col=1); f.update_xaxes(range=[0, 16], ticksuffix="%", row=1, col=2)
f.update_layout(title="Correlations across classes change regime<br><sup>monthly, 1973-2024; one series per class; assets and their 12-month trend streams</sup>",
                barmode="group", height=520, width=1150, margin=dict(t=110, l=240, r=40, b=60), font=dict(size=14),
                legend=dict(orientation="h", y=-0.08, x=0))
save_figure(f, os.environ.get("L27_PREFIX", "") + "27_regimes", HERE.parent / "figures")
print("ok")
