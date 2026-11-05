"""Lecture 21 §5 figure 21_15, from L21_OUT/s5 or results/s5 as shipped. Top: 10 October, 20:50-22:50 UTC: the mid; fills in steps of 10 minutes; the 10-s markout. Bottom: adverse share against loss per
fill on all 45 days; the position of the two quoters; the taker orders sent in the window on all 45 days. Usage: python l21_s5_charts.py"""
import sys
from pathlib import Path
import polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); S5 = L21.OUT / "s5"; CRASH = "2025-10-10"; ORANGE, BLUE = SERIES[1], SERIES[0]
read = lambda n: pl.read_parquet(L21.result_path(S5, n))
D, P, M, T = read("days.parquet"), read("path.parquet"), read("minutes.parquet"), read("taker.parquet")
NAME = {"instant": "at every update", "1s": "once a second"}; COL = {"instant": ORANGE, "1s": BLUE}; hhmm = lambda m: f"{20 + (50 + m) // 60:02d}:{(50 + m) % 60:02d}"
TV = list(range(0, 121, 30)); TT = [hhmm(m) for m in TV]
fig = make_subplots(rows=2, cols=3, horizontal_spacing=0.075, vertical_spacing=0.17,
                    subplot_titles=("The price", "Fills every 10 minutes", "Loss per fill", "45 days: share adverse and loss per fill", "The position carried", "Our taker orders, 45 days"))
m = M.filter(pl.col("quoter") == "instant")
fig.add_scatter(x=m["minute"], y=m["mid"], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=1, col=1); fig.update_yaxes(title_text="mid, USDT", row=1, col=1)
for q in ("instant", "1s"):
    p = P.filter(pl.col("quoter") == q); x = (p["step"] * 10 + 5).to_list(); o = D.filter((pl.col("quoter") == q) & (pl.col("day") != CRASH))
    fig.add_scatter(x=x, y=p["fills"], mode="lines+markers", line=dict(color=COL[q], width=2), marker=dict(size=7), name=NAME[q], row=1, col=2)
    fig.add_hline(y=o["fills"].median() / 12, line=dict(color=COL[q], width=1, dash="dot"), row=1, col=2)
    fig.add_scatter(x=x, y=p["m10"], mode="lines+markers", line=dict(color=COL[q], width=2), marker=dict(size=7), showlegend=False, row=1, col=3)
    fig.add_hline(y=o["m10"].median(), line=dict(color=COL[q], width=1, dash="dot"), row=1, col=3)
    z = M.filter(pl.col("quoter") == q); fig.add_scatter(x=z["minute"], y=z["pos"], mode="lines", line=dict(color=COL[q], width=2), showlegend=False, row=2, col=2)
fig.update_yaxes(title_text="fills", type="log", dtick=1, row=1, col=2); fig.update_yaxes(title_text="10-s markout before the fee, bp", row=1, col=3)
fig.update_yaxes(title_text="position, BTC", row=2, col=2); fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=2, col=2)
for r, c in ((1, 1), (1, 2), (1, 3), (2, 2)): fig.update_xaxes(tickvals=TV, ticktext=TT, title_text="UTC, 10 October", row=r, col=c)
I = D.filter(pl.col("quoter") == "instant"); o, c = I.filter(pl.col("day") != CRASH), I.filter(pl.col("day") == CRASH)
fig.add_scatter(x=o["adverse"], y=o["m10"], mode="markers", marker=dict(color=MUTED, size=8, opacity=0.6), showlegend=False, text=o["day"], row=2, col=1)
fig.add_scatter(x=c["adverse"], y=c["m10"], mode="markers+text", marker=dict(color=ORANGE, size=12), text=["10 October"], textposition="top left", showlegend=False, row=2, col=1)
fig.update_xaxes(title_text="share of fills adverse", tickformat=".0%", row=2, col=1); fig.update_yaxes(title_text="10-s markout before the fee, bp", row=2, col=1)
G = T.filter(pl.col("L") == 50)
for k, (lab, col, sz) in enumerate((("0.001 BTC IOC<br>filled short", "short", 0.001), ("5 BTC<br>paid more than seen", "worse", 5.0))):
    g = G.filter((pl.col("S") - sz).abs() < 1e-4); o, c = g.filter(pl.col("day") != CRASH), g.filter(pl.col("day") == CRASH)
    fig.add_box(x=[lab] * o.height, y=o[col], boxpoints="all", jitter=0.5, pointpos=0, fillcolor="rgba(0,0,0,0)", line=dict(color="rgba(0,0,0,0)"), marker=dict(color=MUTED, size=6, opacity=0.6), showlegend=False, row=2, col=3)
    fig.add_scatter(x=[lab], y=c[col], mode="markers", marker=dict(color=ORANGE, size=12), showlegend=False, row=2, col=3)
fig.update_yaxes(title_text="share of orders", tickformat=".0%", rangemode="tozero", row=2, col=3)
fig.update_layout(title="In the cascade fills came 24 times as often and lost twice as much each, and for the faster quoter most of the loss came from the position carried"
                        "<br><sup>Bybit BTCUSDT; the replay's quoters: queue rule, a = 1, 50 ms, 0.001 BTC a side, no limit on the position; window 20:50-22:50 UTC</sup>",
                  height=820, width=1300, margin=dict(t=100, l=70, r=30, b=80), legend=dict(orientation="h", y=-0.09, x=0.36))
save_figure(fig, L21.PREFIX + "21_15_cascade", L21.FIG)
