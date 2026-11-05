"""Lecture 21 §4 figure 21_14, from L21_OUT/s4 or results/s4 as shipped: left, the reaction curve of H8, all additions, net of matched controls; middle, H7, the gap between what real taker orders
paid and what the last book promised, by size; right, the two quoters, fills within 1 s of the previous fill on the same side against the rest."""
import sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); S4 = L21.OUT / "s4"
C = pl.read_parquet(L21.result_path(S4, "h8_curve.parquet")).filter(pl.col("kind") == "all"); G = pl.read_parquet(L21.result_path(S4, "h7.parquet")); R = pl.read_parquet(L21.result_path(S4, "reentry.parquet"))
LAB = ["5-10%", "10-25%", "25-50%", "50-100%", "100-200%", "200-400%", "400-800%", "> 800%"]
fig = make_subplots(rows=1, cols=3, column_widths=[0.42, 0.28, 0.30], horizontal_spacing=0.08,
                    subplot_titles=("Size added at the best: the reaction", "Real taker orders: the gap", "Two quoters: re-entry after a fill"))
for h, c, nm in (("1s", SERIES[0], "after 1 s"), ("10s", SERIES[1], "after 10 s")):
    g = pl.concat([C.filter((pl.col("cls") == k) & (pl.col("h") == h)) for k in LAB]); x = list(range(len(LAB)))
    fig.add_scatter(x=x + x[::-1], y=np.r_[g["hi"], g["lo"][::-1]], fill="toself", fillcolor=c, opacity=0.18, line=dict(width=0), hoverinfo="skip", showlegend=False, row=1, col=1)
    fig.add_scatter(x=x, y=g["net"], mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=7), name=nm, row=1, col=1)
    fig.add_scatter(x=x, y=g["raw"], mode="lines", line=dict(color=c, width=1.5, dash="dot"), name=nm + ", before controls", row=1, col=1)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=1)
fig.update_xaxes(tickvals=list(range(len(LAB))), ticktext=LAB, tickangle=-30, title_text="size added / size at the best before", row=1, col=1); fig.update_yaxes(title_text="move of the mid away from the addition, bp", row=1, col=1)
g = pl.concat([G.filter(pl.col("cls") == k) for k in ["< 0.01", "0.01-0.1", "0.1-1", "1-5", ">= 5"]])
fig.add_bar(x=g["cls"], y=g["gap"], marker=dict(color=SERIES[2], line=dict(width=0)), error_y=dict(type="data", symmetric=False, array=g["hi"] - g["gap"], arrayminus=g["gap"] - g["lo"], color=INK, thickness=1, width=3), showlegend=False, row=1, col=2)
fig.update_xaxes(title_text="taker order, BTC", row=1, col=2); fig.update_yaxes(title_text="mean gap, bp", range=[0, 0.42], row=1, col=2)
for k, nm, c in ((True, "within 1 s of the last fill", SERIES[3]), (False, "later", SERIES[4])):
    g = pl.concat([R.filter((pl.col("quoter") == q) & (pl.col("quick") == k)) for q in ("1s", "instant")])
    fig.add_bar(x=[f"once a second<br>({R.filter((pl.col('quoter') == '1s') & pl.col('quick'))['share'][0]:.0%} quick)", f"instant<br>({R.filter((pl.col('quoter') == 'instant') & pl.col('quick'))['share'][0]:.0%} quick)"], y=g["m10"], name=nm,
                marker=dict(color=c, line=dict(width=0)), error_y=dict(type="data", symmetric=False, array=g["hi"] - g["m10"], arrayminus=g["m10"] - g["lo"], color=INK, thickness=1, width=3), row=1, col=3)
fig.update_yaxes(title_text="10-s markout before the fee, bp", range=[-1.1, 0], row=1, col=3)
fig.update_layout(title="The market reacts to size from the smallest class on; real orders pay beyond the book seen; quick re-entry takes the worst fills"
                        "<br><sup>Bybit BTCUSDT, out of sample: left and middle 24 days, right eight days; bands and whiskers: 95% from resampling days</sup>",
                  barmode="group", height=500, width=1300, margin=dict(t=100, l=70, r=30, b=70), legend=dict(orientation="h", y=-0.3, x=0))
save_figure(fig, L21.PREFIX + "21_14_tests", L21.FIG)
