"""Lecture 22 §2, teaching simulation, step 2: the market maker. Left, top: 20 seconds of the book with the market maker's orders in their own colour. Left, bottom: the same seconds as the public feed shows them.
Right: its position and its result; the spread and depth with and without it; the footprint: the share of published updates in which both sides change together."""
import sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); BLUE, ORANGE, GREEN = SERIES[0], SERIES[1], SERIES[2]; T_END = 600_000; A, Z = 300_000, 320_000


def world(maker, seed=3):
    m = Sim.Market(seed=seed); ps = [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value()] + ([Sim.MarketMaker()] if maker else []); m.players += ps; m.run(T_END)
    return m, ps[-1]


def tops(m):
    """Per published update: best prices, sizes at the best, depth within 5 ticks."""
    B = m.public_book().group_by("t", "price", "side").agg(pl.col("size").sum())
    g = B.group_by("t").agg(pl.col("price").filter(pl.col("side") == 1).max().alias("b"), pl.col("price").filter(pl.col("side") == -1).min().alias("a")).drop_nulls().sort("t")
    J = B.join(g, on="t")
    best = J.filter(((pl.col("side") == 1) & (pl.col("price") == pl.col("b"))) | ((pl.col("side") == -1) & (pl.col("price") == pl.col("a")))).group_by("t").agg(pl.col("size").filter(pl.col("side") == 1).sum().alias("zb"), pl.col("size").filter(pl.col("side") == -1).sum().alias("za"))
    dp = J.filter(((pl.col("side") == 1) & (pl.col("b") - pl.col("price") <= 5)) | ((pl.col("side") == -1) & (pl.col("price") - pl.col("a") <= 5))).group_by("t").agg((pl.col("size").sum() / 2).alias("depth"))
    return g.join(best, on="t").join(dp, on="t").sort("t").with_columns((pl.col("a") - pl.col("b")).alias("spread"))


def both(G):
    """Share of updates in which both sides change at once, against what two independent sides would give; and by time since the last multiple of 500 ms."""
    x = G.select(((pl.col("b").diff() != 0) | (pl.col("zb").diff().abs() > 1e-9)).alias("cb"), ((pl.col("a").diff() != 0) | (pl.col("za").diff().abs() > 1e-9)).alias("ca"), "t").drop_nulls()
    return float((x["cb"] & x["ca"]).mean()), float(x["cb"].mean() * x["ca"].mean()), x


def phase(m, cycle=500):
    """From the public feed alone: the size that changes in the book between updates, summed over all prices, by the update's place in a cycle of `cycle` ms, as a share of the total."""
    B = m.public_book().group_by("t", "price", "side").agg(pl.col("size").sum()).sort("t"); prev, tot = {}, {}
    for (t,), g in B.group_by(["t"], maintain_order=True):
        cur = {(p, sd): z for p, sd, z in g.select("price", "side", "size").iter_rows()}
        ch = sum(abs(cur.get(k, 0.0) - prev.get(k, 0.0)) for k in set(cur) | set(prev)); prev = cur
        if t > 100: tot[t % cycle] = tot.get(t % cycle, 0.0) + ch
    w = sum(tot.values()); return {k: v / w for k, v in sorted(tot.items())}


M1, mm = world(True); M0, _ = world(False); G1, G0 = tops(M1), tops(M0)
s = {nm: dict(spread=float(g["spread"].mean()), one=float((g["spread"] == 1).mean()), depth=float(g["depth"].median()), zbest=float((g["zb"] + g["za"]).median() / 2)) for nm, g in (("with", G1), ("without", G0))}
b1, i1, X1 = both(G1); b0, i0, _ = both(G0); mt = M1.public_trades(); mf = mt.filter(pl.col("maker") == "market maker")
F1, F0 = phase(M1), phase(M0); print("change by place in the 500 ms cycle: with", {k: round(v, 3) for k, v in F1.items()}, "without", {k: round(v, 3) for k, v in F0.items()})
P = np.array(mm.path); print(s); print("both sides change together: with", round(b1, 3), "independent would give", round(i1, 3), "| without", round(b0, 3), "independent", round(i0, 3))
print("maker: share of traded size", round(mf["size"].sum() / mt["size"].sum(), 3), "largest position", round(np.abs(P[:, 1]).max(), 2), "result in ticks x BTC", round(P[-1, 2], 1), "size traded", round(mf["size"].sum(), 1), "per BTC", round(P[-1, 2] / mf["size"].sum(), 3))
print("final mid against the fair value, ticks: with", (G1["a"][-1] + G1["b"][-1]) / 2 - M1.fair, "without", (G0["a"][-1] + G0["b"][-1]) / 2 - M0.fair, "updates kept", G1.height, G0.height)
fig = make_subplots(rows=2, cols=3, column_widths=[0.5, 0.25, 0.25], horizontal_spacing=0.07, vertical_spacing=0.14,
                    subplot_titles=("With the owners known: the market maker in green", "Its position", "Size at the best price", "The same seconds in the public feed", "Its result", "Its clock, from the public feed alone"))
W = M1.public_book().filter(pl.col("t").is_between(A, Z)); ts = np.arange(A, Z + 1, 100); tg = G1.filter(pl.col("t").is_between(A, Z)); lo, hi = int(tg["b"].min()) - 9, int(tg["a"].max()) + 9; ps = np.arange(lo, hi + 1)


def grid(D):
    g = np.full((len(ps), len(ts)), np.nan)
    for t, p, z in D.select("t", "price", "size").iter_rows():
        if lo <= p <= hi: g[p - lo, (t - A) // 100] = z
    return np.sqrt(g)


def add(z, c, row):
    fig.add_heatmap(x=(ts - A) / 1000, y=ps - M1.start, z=z, colorscale=[[0, f"rgba({c},0.10)"], [1, f"rgba({c},1)"]], zmin=0, zmax=1.2, showscale=False, hoverinfo="skip", row=row, col=1)


add(grid(W.filter(pl.col("owner") == "noise")), "137,135,129", 1); add(grid(W.filter(pl.col("owner") == "market maker")), "27,175,122", 1)
Pub = W.group_by("t", "price", "side").agg(pl.col("size").sum()); add(grid(Pub.filter(pl.col("side") == 1)), "42,120,214", 2); add(grid(Pub.filter(pl.col("side") == -1)), "235,104,52", 2)
for r in (1, 2):
    fig.add_scatter(x=(tg["t"] - A) / 1000, y=tg["b"] - M1.start, mode="lines", line=dict(color=INK, width=1, shape="hv"), showlegend=False, row=r, col=1); fig.add_scatter(x=(tg["t"] - A) / 1000, y=tg["a"] - M1.start, mode="lines", line=dict(color=INK, width=1, shape="hv"), showlegend=False, row=r, col=1)
    fig.update_xaxes(title_text="seconds", row=r, col=1); fig.update_yaxes(title_text="price, ticks from the start", row=r, col=1)
fig.add_scatter(x=P[:, 0] / 1000, y=P[:, 1], mode="lines", line=dict(color=GREEN, width=1.5), showlegend=False, row=1, col=2); fig.update_xaxes(title_text="seconds", row=1, col=2); fig.update_yaxes(title_text="BTC", row=1, col=2)
fig.add_scatter(x=P[:, 0] / 1000, y=P[:, 2], mode="lines", line=dict(color=GREEN, width=1.5), showlegend=False, row=2, col=2); fig.update_xaxes(title_text="seconds", row=2, col=2); fig.update_yaxes(title_text="ticks × BTC, at the fair value", row=2, col=2)
fig.add_bar(x=["without", "with"], y=[s["without"]["zbest"], s["with"]["zbest"]], marker=dict(color=[MUTED, GREEN], line=dict(width=0)), showlegend=False, row=1, col=3); fig.update_yaxes(title_text="median BTC", row=1, col=3)
for nm, F, c in (("without it", F0, MUTED), ("with it", F1, GREEN)):
    fig.add_bar(x=[f"{k} ms" for k in F], y=list(F.values()), marker=dict(color=c, line=dict(width=0)), name=nm, row=2, col=3)
fig.add_hline(y=0.2, line=dict(color=INK, width=1, dash="dot"), row=2, col=3); fig.update_xaxes(title_text="place in a 500 ms cycle", row=2, col=3); fig.update_yaxes(title_text="share of the book's changes", tickformat=".0%", row=2, col=3)
fig.update_layout(barmode="group", title="Step 2: a market maker joins<br><sup>Invented; quotes a ladder of 5 prices a side around a hidden value, refreshed every 500 ms, leaning against its position; noise traders send fewer limit orders than in step 1, and value traders tie the price to the value</sup>", height=760, width=1300, margin=dict(t=100, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.1, x=0.78))
save_figure(fig, L.PREFIX + "22_sim_step2", L.FIG)
