"""Lecture 19 §4 figure 19_15: the evening of 10 October in 15-minute steps, each measure against the same clock steps on the other 44 days."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); sys.stdout.reconfigure(encoding="utf-8")
D = L19.S3
FIG = L19.FIG
R = json.loads((L19.result_path("l19_s4_stats.json")).read_text()); P = pl.read_parquet(L19.result_path("l19_s4_profile.parquet")); T0 = R["T0"]
def dt(ms): return datetime.fromtimestamp(ms / 1000, timezone.utc)
x = [dt(s + 450_000) for s in P["start"]]                                        # middle of each 15-minute step
C = SERIES[1]
fig = make_subplots(rows=3, cols=2, vertical_spacing=0.13, horizontal_spacing=0.09, shared_xaxes=True,
                    subplot_titles=("Bybit BTCUSDT mid ($), every minute", "Levels refilled 3+ times in a row, per 15 minutes (log; none: gap)",
                                    "Depth in the best 10 levels, both sides (BTC)", "Imbalance at the best: AUC of the next mid move",
                                    "Bybit's publish delay, 99th percentile (ms)", "Gap between Binance's last trade and Bybit's mid ($, absolute)"))
M = pl.read_parquet(L19.minute_path("2025-10-10")).vstack(pl.read_parquet(L19.minute_path("2025-10-11"))).filter(
    (pl.col("t") >= P["start"][0]) & (pl.col("t") < P["start"][-1] + 900_000))
fig.add_scatter(x=[dt(t) for t in M["t"]], y=(M["bid"] + M["ask"]) / 20, mode="lines", line=dict(color=INK, width=1.5), showlegend=False, row=1, col=1)
panels = (("chains", 1, 2), ("depth", 2, 1), ("lag99", 3, 1), ("absgap", 3, 2))
for i, (k, r, c) in enumerate(panels):
    q = np.array([s[k] for s in R["profile_ref"]]).astype(float)
    y = P[k].to_list()
    if k == "chains": q[q <= 0] = np.nan; y = [v if v > 0 else None for v in y]           # log scale: steps with none are left empty
    fig.add_scatter(x=x + x[::-1], y=list(q[:, 2]) + list(q[::-1, 0]), fill="toself", fillcolor=GRID, line=dict(width=0), hoverinfo="skip",
                    name="other 44 days, same clock time: 5th–95th percentile", showlegend=i == 0, legendgroup="b", row=r, col=c)
    fig.add_scatter(x=x, y=q[:, 1], mode="lines", line=dict(color=MUTED, width=1, dash="dot"), name="other 44 days: median", showlegend=i == 0, legendgroup="m", row=r, col=c)
    fig.add_scatter(x=x, y=y, mode="lines+markers", line=dict(color=C, width=2), marker=dict(size=5), name="10 October", showlegend=i == 0, legendgroup="o", row=r, col=c)
st = R["H17_steps"]
fig.add_scatter(x=[dt(s["start"] + 450_000) for s in st], y=[s["auc"] for s in st], mode="lines+markers", line=dict(color=C, width=2), marker=dict(size=5), showlegend=False, row=2, col=2)
fig.add_hline(y=0.897, line=dict(color=MUTED, width=1, dash="dot"), row=2, col=2)
fig.add_annotation(x=x[0], y=0.897, text="out-of-sample days: 0.90", xanchor="left", yshift=9, showarrow=False, font=dict(size=10, color=MUTED), row=2, col=2)
fig.add_hline(y=0.5, line=dict(color=MUTED, width=1), row=2, col=2)
fig.update_yaxes(range=[0.45, 1.0], row=2, col=2)
fig.update_yaxes(type="log", row=1, col=2); fig.update_yaxes(rangemode="tozero", row=2, col=1); fig.update_yaxes(rangemode="tozero", row=3, col=1)
for r in (1, 2, 3):
    for c in (1, 2):
        fig.add_vline(x=dt(T0), line=dict(color=INK, width=1, dash="dash"), row=r, col=c)
        fig.add_vrect(x0=dt(T0 - 7_200_000), x1=dt(T0), fillcolor=SERIES[0], opacity=0.06, line_width=0, row=r, col=c)
fig.add_annotation(x=dt(T0), y=1.0, yref="y domain", text="T0 21:14", xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
fig.add_annotation(x=dt(T0 - 3_600_000), y=0.05, yref="y domain", text="pre-window", showarrow=False, font=dict(size=10, color=SERIES[0]), row=1, col=1)
fig.update_xaxes(tickformat="%H:%M", dtick=3_600_000)
fig.update_layout(title="10 October, 15:14 to 00:14 UTC: refilling and the forecast changed once the fall had begun; depth, the feed and the Binance gap did not warn<br>"
                        "<sup>Bybit BTCUSDT and Binance BTCUSDT perpetual. T0 (dashed): the first minute with a larger one-minute move than any on the 20 calm days; "
                        "shaded: the 2 hours before T0, tested in H14–H18.<br>Grey band: the same 15-minute clock steps on the other 44 days</sup>",
                  height=900, width=1250, margin=dict(t=130, l=70, r=30, b=70), legend=dict(orientation="h", y=-0.07, x=0.0, font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_15_cascade_evening", FIG)
print("ok")
