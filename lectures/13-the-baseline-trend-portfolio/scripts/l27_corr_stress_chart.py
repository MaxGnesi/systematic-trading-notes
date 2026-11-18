"""Lecture 13 §3.4 figure from results/corr_stress.json: the baseline's 10% total under each correlation scenario.
Usage: python l27_corr_stress_chart.py"""
import json, sys
import os
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402

J = json.loads((Path(os.environ.get("L27_RESULTS", HERE.parent / "results")) / "corr_stress.json").read_text(encoding="utf-8"))["stress_total_pct"]
order = ["Measured, 2023-2025 (the target)", "Calm (2017)", "Average (2008-2025)", "Crisis window 2008-2009", "Crisis window 2020",
         "Crisis window 2022", "Crisis (highest of 2008-09, 2020, 2022)", "Every correlation at 1 (bound)"]
label = ["Measured, 2023-2025 (the target)", "Calm, 2017", "Average, 2008-2025", "Crisis window 2008-09", "Crisis window 2020",
         "Crisis window 2022", "Crisis scenario: highest of the three", "Every correlation at 1: the bound"]
col = [INK, MUTED, MUTED, SERIES[1], SERIES[1], SERIES[1], SERIES[3], SERIES[0]]
apply_theme()
v = [J[k] for k in order]
f = go.Figure(go.Bar(y=label, x=v, orientation="h", marker=dict(color=col, line=dict(color="#fcfcfb", width=2)),
                     text=[f"{x:.1f}%" for x in v], textposition="outside", cliponaxis=False))
f.add_vline(x=10, line=dict(color=INK, dash="dot", width=1.5))
f.update_yaxes(autorange="reversed"); f.update_xaxes(range=[0, 28], ticksuffix="%", title_text="volatility of the same weights, % a year")
f.update_layout(title="The baseline's 10% under other correlations<br><sup>same weights (equal risk per market within a class, classes equal), scaled to 10% on 2023-2025; only the correlations change</sup>",
                height=470, width=1100, margin=dict(t=100, l=280, r=40, b=70), font=dict(size=14), showlegend=False)
save_figure(f, os.environ.get("L27_PREFIX", "") + "27_corr_stress", HERE.parent / "figures")
print("ok")
