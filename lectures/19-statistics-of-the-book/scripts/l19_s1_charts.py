"""Lecture 19 figures 19_01 and 19_02. 19_01: the chain of Part IV, Lecture 19 outlined, Lecture 18 done. 19_02, the key chart: left, the lopsided book
of 12 March 2024, 12:20:30 UTC (best 5 levels each side, from l18_moments.json) and its imbalance at the best price; right, over our days (L19_OUT/state/),
the share of next mid moves that were up, by the imbalance at the best price just before (updates with a one-tick spread)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme(); sys.stdout.reconfigure(encoding="utf-8")
FIG = L19.FIG; FIG.mkdir(parents=True, exist_ok=True)
BID, ASK = "#2a63b0", "#c0436f"

# 19_01: the chain of Part IV
steps = [("18", "The order book", "what is there"), ("19", "Levels", "the state now"), ("20", "Deltas", "what changed"),
         ("21", "Replay", "our own orders"), ("22", "A market that reacts", "simulated agents"), ("23", "Market making", "one venue"),
         ("24", "Cross-exchange", "quote here, hedge there")]
CUR = 1
fig = go.Figure()
for i, (n, a, b) in enumerate(steps):
    x0 = i * 1.45
    fig.add_shape(type="rect", x0=x0, x1=x0 + 1.2, y0=0, y1=1, line=dict(color=INK if i == CUR else MUTED, width=2.5 if i == CUR else 1),
                  fillcolor="#eef3fb" if i == CUR else ("#f4f4f2" if i < CUR else "white"))
    fig.add_annotation(x=x0 + 0.6, y=0.75, text=f"<b>Lecture {n}</b>" + (" ✓" if i < CUR else ""), showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.48, text=a, showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.22, text=f"<i>{b}</i>", showarrow=False, font=dict(size=11, color=MUTED))
    if i < len(steps) - 1:
        fig.add_annotation(x=x0 + 1.43, y=0.5, ax=x0 + 1.22, ay=0.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowcolor=MUTED, text="")
for x0, x1, lab in ((0, 1.2, "describe"), (1.45, 4.1, "measure"), (4.35, 7.0, "simulate"), (7.25, 9.9, "trade")):
    fig.add_annotation(x=(x0 + x1) / 2, y=1.27, text=lab, showarrow=False, font=dict(size=11, color=MUTED))
    fig.add_shape(type="line", x0=x0, x1=x1, y0=1.13, y1=1.13, line=dict(color=GRID, width=2))
fig.update_xaxes(visible=False, range=[-0.1, 10]); fig.update_yaxes(visible=False, range=[-0.15, 1.42])
fig.update_layout(title="Part IV in one line: Lecture 19 measures the book as it stands<br><sup>Each lecture builds on the one before; "
                        "the current one is outlined, done ones are ticked</sup>", height=270, width=1250, margin=dict(t=80, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L19.PREFIX + "19_01_part_iv", FIG)

# 19_02: the key chart
S = json.loads((L19.L18_RESULTS / "l18_moments.json").read_text())["snapshot"]
bids = [(p / 10, q) for p, q in S["bids"][:5]]; asks = [(p / 10, q) for p, q in S["asks"][:5]]
qb, qa = bids[0][1], asks[0][1]; I0 = (qb - qa) / (qb + qa)
KB = json.loads(L19.result_path("l19_key_bins.json").read_text()); files = sorted(KB)
G = pl.DataFrame([(int(b), *v) for d in files for b, v in KB[d].items()], schema=["b", "si", "su", "n"], orient="row")
G = G.group_by("b").agg(pl.col("si", "su", "n").sum()).sort("b").with_columns((pl.col("si") / pl.col("n")).alias("I"), (pl.col("su") / pl.col("n")).alias("p_up"))
n_upd = int(G["n"].sum()); p_at = float(G.filter(pl.col("b") == min(19, int((I0 + 1) / 2 * 20)))["p_up"][0])

fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], horizontal_spacing=0.09,
                    subplot_titles=("One moment: the best bid holds 28 times the best ask", "Every update: the next move of the mid, by the imbalance"))
K, CAP, BX0, BX1 = 5, 2.0, 0.32, 1.0
rows = [("ask", p, q) for p, q in reversed(asks[:K])] + [("bid", p, q) for p, q in bids[:K]]
for i, (side, p, q) in enumerate(rows):
    y = len(rows) - 1 - i; col = ASK if side == "ask" else BID; best = p in (asks[0][0], bids[0][0])
    fig.add_shape(type="rect", x0=0, x1=1, y0=y + 0.04, y1=y + 0.96, line=dict(color=INK if best else "rgba(0,0,0,0)", width=1.5 if best else 0),
                  fillcolor="#fbe9f1" if side == "ask" else "#e7f0fb", row=1, col=1)
    fig.add_annotation(x=0.02, y=y + 0.5, text=f"{p:,.1f}", xanchor="left", showarrow=False, font=dict(size=11, color=INK), row=1, col=1)
    L = min(q, CAP) / CAP * (BX1 - BX0 - 0.17)
    fig.add_shape(type="rect", x0=BX0, x1=BX0 + L, y0=y + 0.2, y1=y + 0.8, fillcolor=col, line=dict(width=0), row=1, col=1)
    fig.add_annotation(x=BX0 + L + 0.015, y=y + 0.5, text=f"{q:.3f}" + (" ▶" if q > CAP else ""), xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
fig.add_shape(type="line", x0=0, x1=1, y0=K, y1=K, line=dict(color=INK, width=1.5), row=1, col=1)
fig.add_annotation(x=-0.02, y=K + K / 2, text="asks", xanchor="right", showarrow=False, font=dict(size=11, color=ASK), row=1, col=1)
fig.add_annotation(x=-0.02, y=K / 2, text="bids", xanchor="right", showarrow=False, font=dict(size=11, color=BID), row=1, col=1)
fig.add_annotation(x=0.5, y=-0.75, text=f"imbalance at the best = ({qb:.3f} − {qa:.3f}) / ({qb:.3f} + {qa:.3f}) = <b>{I0:+.2f}</b>", showarrow=False,
                   font=dict(size=11, color=INK), row=1, col=1)
fig.update_xaxes(visible=False, range=[-0.18, 1.02], row=1, col=1); fig.update_yaxes(visible=False, range=[-1.2, 2 * K + 0.2], row=1, col=1)
fig.add_scatter(x=G["I"], y=G["p_up"], mode="lines+markers", line=dict(color=INK, width=2), marker=dict(size=8), showlegend=False, row=1, col=2)
fig.add_hline(y=0.5, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=2)
fig.add_annotation(x=I0, y=p_at, text=f"a book like the one on the left:<br>next move up {p_at:.0%} of the time", showarrow=True, ax=-120, ay=-10,
                   xanchor="right", font=dict(size=11, color=INK), row=1, col=2)
fig.add_annotation(x=-0.95, y=0.52, text="no imbalance, no edge: 50%", showarrow=False, xanchor="left", yshift=8, font=dict(size=10, color=MUTED), row=1, col=2)
fig.update_xaxes(title_text="imbalance at the best: −1 only asks, +1 only bids", range=[-1.05, 1.05], row=1, col=2)
fig.update_yaxes(title_text="share of next mid moves that were up", tickformat=".0%", range=[0, 1], row=1, col=2)
fig.update_layout(title="Book imbalance and the next move of the mid: when the best bid outweighed the best ask, the next move was mostly up<br>"
                        f"<sup>Bybit BTCUSDT. Left: 12 March 2024, 12:20:30 UTC, the best 5 levels on each side, BTC (bars full at {CAP:.0f} BTC; ▶ larger). "
                        f"Right: {n_upd / 1e6:.0f} million updates with a one-tick spread, {len(files)} days of 20 September – 3 November 2025</sup>",
                  height=560, width=1250, margin=dict(t=110, l=60, r=30, b=40))
save_figure(fig, L19.PREFIX + "19_02_imbalance_key", FIG)
print("ok", len(files), "days", G.select("I", "p_up", "n").to_dicts()[::4], "p at moment", p_at)
