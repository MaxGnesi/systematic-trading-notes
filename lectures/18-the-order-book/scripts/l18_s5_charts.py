"""Lecture 18 figures 18_05 and 18_06, from l18_s5_summary.json. 18_05: the 45 days, day by day: depth within 5 bp of the mid on each side (median of
the day's seconds) and what a 5 BTC market buy pays beyond the mid by walking the book (median and the worst 1% of seconds); 10 October marked.
18_06: the evening of 10 October, minute by minute: the spread in ticks, the depth within 5 bp, and the share of seconds in which 200 levels did not
hold 5 BTC on one side; the 100% tariff post (20:50:01.7 UTC) marked."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()
FIG = L18.FIG
J = json.loads(L18.result_path("l18_s5_summary.json").read_text()); BID, ASK = "#2a63b0", "#c0436f"
D = pl.DataFrame(J["by_day"]).sort("day")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.5, 0.5],
                    subplot_titles=("Depth within 5 bp of the mid, BTC (median of each day's seconds)", "What a 5 BTC market buy pays beyond the mid, bp"))
fig.add_scatter(x=D["day"], y=D["depth_bid"], mode="lines+markers", line=dict(color=BID, width=2), marker=dict(size=5), name="bids", row=1, col=1)
fig.add_scatter(x=D["day"], y=D["depth_ask"], mode="lines+markers", line=dict(color=ASK, width=2), marker=dict(size=5), name="asks", row=1, col=1)
fig.add_scatter(x=D["day"], y=D["buy_5_bp"], mode="lines+markers", line=dict(color=INK, width=2), marker=dict(size=5), name="median second", row=2, col=1)
fig.add_scatter(x=D["day"], y=D["buy_5_p99_bp"], mode="lines+markers", line=dict(color=MUTED, width=1.5, dash="dot"), marker=dict(size=4), name="worst 1% of seconds", row=2, col=1)
for r in (1, 2):
    fig.add_vline(x="2025-10-10", line=dict(color=SERIES[4], width=1.5, dash="dash"), row=r, col=1)
fig.add_annotation(x="2025-10-10", y=1.0, yref="y domain", text="10 October: the cascade", showarrow=False, xanchor="left", xshift=6, font=dict(size=11, color=INK), row=1, col=1)
fig.update_yaxes(title_text="BTC", rangemode="tozero", row=1, col=1); fig.update_yaxes(title_text="bp", type="log", row=2, col=1)
fig.update_layout(title="Liquidity on Bybit BTCUSDT, 20 September – 3 November 2025: after the cascade, half the depth and several times the cost<br>"
                        "<sup>From the reconstructed book, every second of every day; the three feed gaps left out</sup>",
                  height=640, width=1200, margin=dict(t=110, l=70, b=80), legend=dict(orientation="h", y=-0.1, x=0))
save_figure(fig, L18.PREFIX + "18_05_liquidity_45_days", FIG)

E = pl.DataFrame(J["evening_10_oct"]).sort("minute"); x = [f"{m // 60:02d}:{m % 60:02d}" for m in E["minute"]]
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                    subplot_titles=("Spread, ticks of $0.10 (average of the minute; log scale)", "Depth within 5 bp of the mid, both sides, BTC (median of the minute)",
                                    "Share of seconds in which the 200 levels of one side did not hold 5 BTC"))
fig.add_bar(x=x, y=E["spread_ticks"], marker=dict(color=SERIES[1]), showlegend=False, row=1, col=1)
fig.add_bar(x=x, y=E["depth"], marker=dict(color=BID), showlegend=False, row=2, col=1)
fig.add_hline(y=J["calm"]["depth"], line=dict(color=MUTED, dash="dot", width=1.2), row=2, col=1)
fig.add_annotation(x=x[2], y=J["calm"]["depth"], text=f"a calm day's median: {J['calm']['depth']:.0f} BTC", showarrow=False, yshift=9, xanchor="left", font=dict(size=10, color=MUTED), row=2, col=1)
fig.add_bar(x=x, y=E["beyond_book"], marker=dict(color=INK), showlegend=False, row=3, col=1)
fig.add_annotation(x="21:42", y=430, text="walls at the round number $111,000:<br>56.8 BTC at 111,000.0 and exactly 100 BTC at 111,001.0", showarrow=True, ax=120, ay=-5, xanchor="left", font=dict(size=10, color=INK), row=2, col=1)
for r in (1, 2, 3): fig.add_vline(x="20:50", line=dict(color=SERIES[4], width=1.5, dash="dash"), row=r, col=1)
fig.add_annotation(x="20:50", y=1.0, yref="y domain", text="20:50:01.7 the tariff post", showarrow=False, xanchor="left", xshift=6, font=dict(size=11, color=INK), row=1, col=1)
fig.update_yaxes(type="log", row=1, col=1); fig.update_yaxes(tickformat=".0%", range=[0, 1], row=3, col=1)
fig.update_xaxes(tickvals=x[::10], row=3, col=1, title_text="UTC, 10 October 2025")
fig.update_layout(title="The evening of 10 October 2025, minute by minute: the book thinned after the post and nearly vanished from 21:15<br>"
                        "<sup>Bybit BTCUSDT, reconstructed book, 20:30–22:30 UTC</sup>", height=760, width=1200, margin=dict(t=110, l=70, b=70), bargap=0.1)
save_figure(fig, L18.PREFIX + "18_06_cascade_book", FIG)
print("ok")
