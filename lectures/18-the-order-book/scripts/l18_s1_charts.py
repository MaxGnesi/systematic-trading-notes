"""Lecture 18 figures 18_01-18_03. 18_01: the chain of Part IV (schematic). 18_02: the Bybit BTCUSDT book at 12 March 2024, 12:20:30.015 UTC, best 25
levels each side, and what market buys of 0.5-5 BTC would pay by walking it (from l18_moments.json, top 50 levels). 18_03: the same moment at
three levels of detail: L1 (best bid and ask), L2 (every level), L3 (individual orders: an illustration, not observed in our data)."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
FIG = L18.FIG
BID, ASK = "#2a63b0", "#c0436f"
S = json.loads(L18.result_path("l18_moments.json").read_text())["snapshot"]
bids = [(p / 10, q) for p, q in S["bids"]]; asks = [(p / 10, q) for p, q in S["asks"]]; mid = (bids[0][0] + asks[0][0]) / 2

# 18_01: the chain of Part IV
steps = [("18", "The order book", "what is there"), ("19", "Levels", "the state now"), ("20", "Deltas", "what changed"),
         ("21", "Replay", "our own orders"), ("22", "A market that reacts", "simulated agents"), ("23", "Market making", "one venue"),
         ("24", "Cross-exchange", "quote here, hedge there")]
fig = go.Figure()
for i, (n, a, b) in enumerate(steps):
    x0 = i * 1.45
    fig.add_shape(type="rect", x0=x0, x1=x0 + 1.2, y0=0, y1=1, line=dict(color=INK if i == 0 else MUTED, width=2.5 if i == 0 else 1),
                  fillcolor="#eef3fb" if i == 0 else "white")
    fig.add_annotation(x=x0 + 0.6, y=0.75, text=f"<b>Lecture {n}</b>", showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.48, text=a, showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.22, text=f"<i>{b}</i>", showarrow=False, font=dict(size=11, color=MUTED))
    if i < len(steps) - 1:
        fig.add_annotation(x=x0 + 1.43, y=0.5, ax=x0 + 1.22, ay=0.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowcolor=MUTED, text="")
for x0, x1, lab in ((0, 1.2, "describe"), (1.45, 4.1, "measure"), (4.35, 7.0, "simulate"), (7.25, 9.9, "trade")):
    fig.add_annotation(x=(x0 + x1) / 2, y=1.27, text=lab, showarrow=False, font=dict(size=11, color=MUTED))
    fig.add_shape(type="line", x0=x0, x1=x1, y0=1.13, y1=1.13, line=dict(color=GRID, width=2))
fig.update_xaxes(visible=False, range=[-0.1, 10]); fig.update_yaxes(visible=False, range=[-0.15, 1.42])
fig.update_layout(title="Part IV in one line: from describing the order book to trading on it<br><sup>Each lecture builds on the one before; "
                        "the current one is outlined</sup>", height=270, width=1250, margin=dict(t=80, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L18.PREFIX + "18_01_part_iv", FIG)

# 18_02: the book at one moment, and walking it
N = 25
fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.1,
                    subplot_titles=("The book at 12:20:30.015 UTC: the best 25 levels on each side", "What a market buy would pay by walking the asks"))
fig.add_bar(y=[p for p, _ in bids[:N]], x=[q for _, q in bids[:N]], orientation="h", width=0.08, marker=dict(color=BID, line=dict(width=0)),
            name="bids: resting buy orders", row=1, col=1)
fig.add_bar(y=[p for p, _ in asks[:N]], x=[q for _, q in asks[:N]], orientation="h", width=0.08, marker=dict(color=ASK, line=dict(width=0)),
            name="asks: resting sell orders", row=1, col=1)
fig.add_annotation(x=1.6, y=bids[0][0], text=f"best bid {bids[0][0]:,.1f}: {bids[0][1]:.2f} BTC waiting (a queue), bar cut at 1.6 →", xanchor="right",
                   showarrow=False, yshift=-9, font=dict(size=11, color=BID), row=1, col=1)
fig.add_annotation(x=asks[0][1], y=asks[0][0], text=f"best ask {asks[0][0]:,.1f}: {asks[0][1]:.3f} BTC", xanchor="left", showarrow=False,
                   xshift=6, yshift=8, font=dict(size=11, color=ASK), row=1, col=1)
fig.add_annotation(x=0.9, y=mid + 1.2, text="spread between them: one tick ($0.10)", showarrow=False, font=dict(size=11, color=INK), row=1, col=1)
cum, px = [], []
c = 0.0
for p, q in asks:
    cum += [c, c + q]; px += [p, p]; c += q
fig.add_scatter(x=cum, y=px, mode="lines", line=dict(color=ASK, width=2), name="cumulative asks: the price reached after buying this much", row=1, col=2)
for Q in (0.5, 1, 2, 5):
    left, cost = Q, 0.0
    for p, q in asks:
        t = min(left, q); cost += t * p; left -= t
        if left <= 1e-12: break
    avg = cost / Q
    fig.add_scatter(x=[Q], y=[avg], mode="markers+text", marker=dict(color=INK, size=9), text=[f"{Q:g} BTC: average {avg:,.2f} (+{(avg / mid - 1) * 1e4:.2f} bp)"],
                    textposition="middle right", textfont=dict(size=11), showlegend=False, row=1, col=2)
fig.add_hline(y=mid, line=dict(color=MUTED, dash="dot", width=1), row=1, col=2)
fig.add_annotation(x=12.5, y=mid, text="mid", showarrow=False, yshift=-10, font=dict(size=11, color=MUTED), row=1, col=2)
fig.update_xaxes(title_text="BTC resting at the level (axis cut at 1.6)", range=[0, 1.6], row=1, col=1); fig.update_yaxes(title_text="price, USDT", tickformat=",.0f", row=1, col=1)
fig.update_xaxes(title_text="size of the market buy, BTC", range=[0, 13.5], tickvals=[0, 2, 4, 6, 8], row=1, col=2); fig.update_yaxes(tickformat=",.0f", row=1, col=2)
fig.update_layout(title="An order book at one moment: Bybit BTCUSDT, 12 March 2024, 12:20:30 UTC<br><sup>Reconstructed from the day's snapshot and "
                        "100 ms updates. Walking the book assumes it stands still while the order arrives</sup>", barmode="overlay", height=620, width=1250,
                  margin=dict(t=110, l=80, b=110), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, L18.PREFIX + "18_02_book_moment", FIG)

# 18_03: the same moment at L1, L2, L3, drawn as three ladders (one row per level, asks above, bids below, sizes written in)
K, CAP = 8, 1.0                                                                # levels per side; bars full at 1 BTC, larger sizes marked
rows = [("ask", p, q) for p, q in reversed(asks[:K])] + [("bid", p, q) for p, q in bids[:K]]     # top row = furthest ask
rng = np.random.default_rng(3)
split = {p: rng.dirichlet(np.ones(int(np.clip(np.ceil(q / 0.04), 1, 9)))) * q for _, p, q in rows}   # invented orders (about one per 0.04 BTC, at most 9), for L3 only
fig = go.Figure()
PW, GAP = 1.0, 0.18
for k, (lvl, head) in enumerate((("L1", "L1: the best bid and ask"), ("L2", "L2: every level and its total size"), ("L3", "L3: every order (invented split)"))):
    x0 = k * (PW + GAP); px0, bx0, bx1 = x0, x0 + 0.30, x0 + PW
    fig.add_annotation(x=x0 + PW / 2, y=len(rows) + 0.9, text=f"<b>{head}</b>", showarrow=False, font=dict(size=13, color=INK))
    for i, (side, p, q) in enumerate(rows):
        y = len(rows) - 1 - i; col = ASK if side == "ask" else BID
        best = (side == "ask" and p == asks[0][0]) or (side == "bid" and p == bids[0][0])
        shown = lvl != "L1" or best
        fig.add_shape(type="rect", x0=x0, x1=x0 + PW, y0=y + 0.04, y1=y + 0.96, line=dict(width=0),
                      fillcolor=("#fbe9f1" if side == "ask" else "#e7f0fb") if shown else "#f2f2f2")
        fig.add_annotation(x=px0 + 0.02, y=y + 0.5, text=f"{p:,.1f}", xanchor="left", showarrow=False,
                           font=dict(size=11, color=INK if shown else "#c8c8c8"))
        if not shown:
            fig.add_annotation(x=bx0 + 0.02, y=y + 0.5, text="not in L1 data", xanchor="left", showarrow=False, font=dict(size=10, color="#bdbdbd")); continue
        L = min(q, CAP) / CAP * (bx1 - bx0 - 0.17)
        if lvl == "L3":
            left = bx0
            for v in split[p]:
                w = v / q * L
                fig.add_shape(type="rect", x0=left, x1=left + w, y0=y + 0.2, y1=y + 0.8, fillcolor=col, line=dict(color="white", width=2))
                left += w
            txt = f"{len(split[p])} order{'s' if len(split[p]) > 1 else ''}"
        else:
            fig.add_shape(type="rect", x0=bx0, x1=bx0 + L, y0=y + 0.2, y1=y + 0.8, fillcolor=col, line=dict(width=0))
            txt = f"{q:.3f}"
        txt += " ▶" if q > CAP else ""
        fig.add_annotation(x=bx0 + L + 0.015, y=y + 0.5, text=txt, xanchor="left", showarrow=False, font=dict(size=10, color=INK))
    fig.add_shape(type="line", x0=x0, x1=x0 + PW, y0=K, y1=K, line=dict(color=INK, width=1.5))
fig.add_annotation(x=-0.02, y=K + K / 2, text="asks<br>(sell)", xanchor="right", showarrow=False, font=dict(size=11, color=ASK))
fig.add_annotation(x=-0.02, y=K / 2, text="bids<br>(buy)", xanchor="right", showarrow=False, font=dict(size=11, color=BID))
fig.add_annotation(x=-0.02, y=K, text="spread:<br>one tick", xanchor="right", showarrow=False, font=dict(size=10, color=MUTED))
fig.update_xaxes(visible=False, range=[-0.16, 3 * PW + 2 * GAP + 0.02]); fig.update_yaxes(visible=False, range=[-0.3, len(rows) + 1.5])
fig.update_layout(title="The same moment at three levels of detail: Bybit publishes L2, the size at each price, not the orders inside it<br>"
                        "<sup>Bybit BTCUSDT, 12 March 2024, 12:20:30 UTC, the best 8 levels on each side, sizes in BTC. Bars are full at 1 BTC; ▶ marks a larger size. "
                        "The L3 split into orders is invented: our data do not contain it</sup>", height=640, width=1250, margin=dict(t=100, l=60, r=20, b=20), showlegend=False)
save_figure(fig, L18.PREFIX + "18_03_l1_l2_l3", FIG)
print("ok")
