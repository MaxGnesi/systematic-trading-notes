"""Lecture 22 §2, the teaching simulation step by step. Step 1: noise traders only. Left: one minute of the book and the trades. Middle: the mid over ten minutes. Right: the average size by distance from the best."""
import sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); BLUE, ORANGE = SERIES[0], SERIES[1]
m = Sim.Market(seed=3); n = Sim.Noise(); m.players.append(n); m.run(600_000)
B, T = m.public_book().group_by("t", "price", "side").agg(pl.col("size").sum()), m.public_trades()
A, Z = 300_000, 360_000
print("trades", T.height, "size", round(T["size"].sum(), 1), "resting", len(m.book.where), "spread now", m.book.best(-1) - m.book.best(1))
W = B.filter(pl.col("t").is_between(A, Z)); mids = B.group_by("t").agg(pl.col("price").filter(pl.col("side") == 1).max().alias("b"), pl.col("price").filter(pl.col("side") == -1).min().alias("a")).sort("t").with_columns(((pl.col("a") + pl.col("b")) / 2).alias("mid"), (pl.col("a") - pl.col("b")).alias("spread"))
print("spread: median", mids["spread"].median(), "mean", round(mids["spread"].mean(), 2), "share one tick", round((mids["spread"] == 1).mean(), 3))
fig = make_subplots(rows=1, cols=3, column_widths=[0.5, 0.25, 0.25], horizontal_spacing=0.07, subplot_titles=("One minute of the book and the trades", "The mid over ten minutes", "Average size by distance from the best"))
ts = np.arange(A, Z + 1, 100); lo, hi = int(mids.filter(pl.col("t").is_between(A, Z))["mid"].min()) - 14, int(mids.filter(pl.col("t").is_between(A, Z))["mid"].max()) + 14; ps = np.arange(lo, hi + 1)
for side, c, nm in ((1, "37,99,235", "bids"), (-1, "235,104,52", "asks")):
    g = np.full((len(ps), len(ts)), np.nan)
    for t, p, z in W.filter(pl.col("side") == side).select("t", "price", "size").iter_rows():
        if lo <= p <= hi: g[p - lo, (t - A) // 100] = z
    fig.add_heatmap(x=(ts - A) / 1000, y=ps - m.start, z=np.sqrt(g), colorscale=[[0, f"rgba({c},0.08)"], [1, f"rgba({c},1)"]], zmin=0, zmax=1.5, showscale=False, hoverinfo="skip", row=1, col=1)
X = T.filter(pl.col("t").is_between(A, Z))
for s, c, nm in ((1, ORANGE, "market buy"), (-1, BLUE, "market sell")):
    x = X.filter(pl.col("side") == s); fig.add_scatter(x=(x["t"] - A) / 1000, y=x["price"] - m.start, mode="markers", marker=dict(size=4 + 14 * np.sqrt(x["size"].to_numpy()), color=c, symbol="triangle-up" if s == 1 else "triangle-down", line=dict(width=1, color=INK)), name=nm, row=1, col=1)
fig.update_xaxes(title_text="seconds", row=1, col=1); fig.update_yaxes(title_text="price, ticks from the start", row=1, col=1)
fig.add_scatter(x=mids["t"] / 1000, y=mids["mid"] - m.start, mode="lines", line=dict(color=INK, width=1.5), showlegend=False, row=1, col=2)
fig.update_xaxes(title_text="seconds", row=1, col=2); fig.update_yaxes(title_text="mid, ticks from the start", row=1, col=2)
D = B.join(mids.select("t", "b", "a"), on="t").with_columns(pl.when(pl.col("side") == 1).then(pl.col("b") - pl.col("price")).otherwise(pl.col("price") - pl.col("a")).alias("d")).filter(pl.col("d") <= 30)
P = D.group_by("d").agg(pl.col("size").sum() / (mids.height * 2)).sort("d")
fig.add_bar(x=P["d"], y=P["size"], marker=dict(color=MUTED, line=dict(width=0)), showlegend=False, row=1, col=3)
fig.update_xaxes(title_text="ticks behind the best", row=1, col=3); fig.update_yaxes(title_text="size, BTC", row=1, col=3)
fig.update_layout(title="Step 1: an order book with noise traders only<br><sup>Invented; 40 limit orders and 6 market orders a second, placed at random; nobody knows anything about the price</sup>", height=520, width=1300, margin=dict(t=100, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.14, x=0))
save_figure(fig, L.PREFIX + "22_sim_step1", L.FIG)
