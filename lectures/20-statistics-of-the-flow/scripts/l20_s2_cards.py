"""Lecture 20, Section 2 cards. 20_03: order-flow imbalance on an invented sequence of five states of the best two levels, with the contribution of
each update (Cont, Kukanov and Stoikov, 2014) and the trade imbalance beside it."""
import sys
from pathlib import Path
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
FIG = L20.FIG; FIG.mkdir(parents=True, exist_ok=True)
BID, ASK, OFI_C, TI_C = "#2a63b0", "#c0436f", "#2a78d6", "#eb6834"


def ofi_term(prev, cur):
    """Contribution of one update: prev and cur are (bid price, bid size, ask price, ask size)."""
    pb0, qb0, pa0, qa0 = prev; pb1, qb1, pa1, qa1 = cur
    return ((qb1 if pb1 >= pb0 else 0) - (qb0 if pb1 <= pb0 else 0) - (qa1 if pa1 <= pa0 else 0) + (qa0 if pa1 >= pa0 else 0))


# 20_03: five states of an invented book, best two levels per side (price in $, size in BTC); the event that leads to each state, and its trades
P0 = 100_000.0
states = [
    dict(bids=[(P0, 2.0), (P0 - 0.1, 1.5)], asks=[(P0 + 0.1, 1.5), (P0 + 0.2, 2.0)], ev="start", tr=0.0),
    dict(bids=[(P0, 2.0), (P0 - 0.1, 1.5)], asks=[(P0 + 0.1, 0.5), (P0 + 0.2, 2.0)], ev="a buyer takes 1.0<br>at the best ask", tr=+1.0),
    dict(bids=[(P0, 3.2), (P0 - 0.1, 1.5)], asks=[(P0 + 0.1, 0.5), (P0 + 0.2, 2.0)], ev="1.2 added<br>to the best bid", tr=0.0),
    dict(bids=[(P0, 3.2), (P0 - 0.1, 1.5)], asks=[(P0 + 0.2, 2.0), (P0 + 0.3, 1.8)], ev="the last 0.5 at the ask<br>is cancelled", tr=0.0),
    dict(bids=[(P0, 3.2), (P0 - 0.1, 1.5)], asks=[(P0 + 0.1, 1.0), (P0 + 0.2, 2.0)], ev="a seller places 1.0<br>back at 100,000.1", tr=0.0),
]
best = [(s["bids"][0][0], s["bids"][0][1], s["asks"][0][0], s["asks"][0][1]) for s in states]
e = [0.0] + [ofi_term(best[i - 1], best[i]) for i in range(1, len(best))]
cum_e = [sum(e[:i + 1]) for i in range(len(e))]; cum_t = [sum(s["tr"] for s in states[:i + 1]) for i in range(len(states))]
mids = [(b[0] + b[2]) / 2 for b in best]
print("e", e, "OFI", cum_e, "TI", cum_t, "mids", mids)

N = len(states)
fig = make_subplots(rows=1, cols=N, horizontal_spacing=0.035, subplot_titles=[f"Update {i}" if i else "Before" for i in range(N)])
CAP, BX0 = 4.0, 0.42
for c, s in enumerate(states, start=1):
    rows = [("ask", p, q) for p, q in reversed(s["asks"])] + [("bid", p, q) for p, q in s["bids"]]
    for i, (side, p, q) in enumerate(rows):
        y = 3 - i; col = ASK if side == "ask" else BID; is_best = (i == 1 or i == 2)
        fig.add_shape(type="rect", x0=0, x1=1, y0=y + 0.05, y1=y + 0.95, line=dict(color=INK if is_best else "rgba(0,0,0,0)", width=1.5 if is_best else 0),
                      fillcolor="#fbe9f1" if side == "ask" else "#e7f0fb", row=1, col=c)
        fig.add_annotation(x=0.03, y=y + 0.5, text=f"{p:,.1f}", xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=c)
        L = min(q, CAP) / CAP * (1 - BX0 - 0.2)
        fig.add_shape(type="rect", x0=BX0, x1=BX0 + L, y0=y + 0.22, y1=y + 0.78, fillcolor=col, line=dict(width=0), row=1, col=c)
        fig.add_annotation(x=BX0 + L + 0.02, y=y + 0.5, text=f"{q:.1f}", xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=c)
    fig.add_shape(type="line", x0=0, x1=1, y0=2, y1=2, line=dict(color=INK, width=1.2), row=1, col=c)
    fig.add_annotation(x=0.5, y=4.55, text=f"<i>{s['ev']}</i>", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=c)
    fig.add_annotation(x=0.5, y=-0.35, text=f"mid {mids[c - 1]:,.2f}", showarrow=False, font=dict(size=10, color=INK), row=1, col=c)
    if c > 1:
        fig.add_annotation(x=0.5, y=-0.9, text=f"contribution <b>{e[c - 1]:+.1f}</b>", showarrow=False, font=dict(size=11, color=OFI_C), row=1, col=c)
    fig.add_annotation(x=0.5, y=-1.45, text=f"order-flow imbalance so far <b>{cum_e[c - 1]:+.1f}</b>", showarrow=False, font=dict(size=10, color=OFI_C), row=1, col=c)
    fig.add_annotation(x=0.5, y=-1.95, text=f"trade imbalance so far <b>{cum_t[c - 1]:+.1f}</b>", showarrow=False, font=dict(size=10, color=TI_C), row=1, col=c)
    fig.update_xaxes(visible=False, range=[-0.02, 1.02], row=1, col=c); fig.update_yaxes(visible=False, range=[-2.25, 4.95], row=1, col=c)
fig.update_layout(title="Order-flow imbalance on an invented book: trades, additions and cancellations at the best all count; the trade imbalance sees only the trade<br>"
                        "<sup>The best two levels on each side, sizes in BTC (bars full at 4 BTC); the best bid and ask are outlined. "
                        "Each update's contribution in BTC: positive pushes the price up, negative down</sup>",
                  height=470, width=1250, margin=dict(t=110, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L20.PREFIX + "20_03_ofi_card", FIG)


# 20_04: impact over time on invented orders. Each order leaves a bare impact G(l) = G1 l^-BETA that fades; the signs of orders are correlated,
# C(l) = C1 l^-GAMMA (buys follow buys, as when large orders are split into many small ones). Left: G. Middle: one run of 20 buys among orders of
# mixed sign, the price with fading and with permanent impact. Right: the response R(l), computed from G and C with the propagator model.
import numpy as np
G1, BETA, C1, GAMMA = 1.0, 0.2, 0.3, 0.6          # BETA = (1 - GAMMA) / 2: the balance at which the price neither trends nor reverts
LMAX = 20_000
nn = np.arange(1, LMAX + 1, dtype=float); G = G1 * nn ** -BETA      # G[l-1] = impact l orders later


def corr(k):
    return np.where(k == 0, 1.0, C1 * np.maximum(k, 1) ** -GAMMA)


def price(eps):
    """Mid after each order: sum over past orders of G(t - i) eps_i."""
    return np.convolve(eps, np.concatenate([[0.0], G]))[:len(eps)]


lags = np.unique(np.round(np.logspace(0, np.log10(300), 20)).astype(int))
base = (G * corr(nn)).sum()
R = np.array([(G * corr(np.abs(nn - l))).sum() - base for l in lags])      # Bouchaud et al. (2004): R(l) = sum_n G(n) C(|n - l|) - sum_n G(n) C(n)
print("R", dict(zip(lags.tolist(), R.round(2))), "G", dict(zip(lags.tolist(), G[lags - 1].round(2))), "C", dict(zip(lags.tolist(), corr(lags).round(3))))

# the story: 20 buys, then 40 orders of random sign (fixed so that the picture does not depend on the draw)
story = np.concatenate([np.ones(20), np.array([1, -1, -1, 1, -1, 1, 1, -1, -1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1,
                                                1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1, -1, 1, 1, -1, -1, 1, -1, 1], float)])
m_fade = price(story); m_perm = np.cumsum(story) * G1
xs = np.arange(1, len(story) + 1)

fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08, column_widths=[0.28, 0.4, 0.32],
                    subplot_titles=("One order: its bare impact fades", "Twenty buys in a row, then mixed orders",
                                    "All orders: the response grows, G fades"))
fig.add_scatter(x=np.arange(1, 101), y=G[:100], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=1, col=1)
fig.update_xaxes(title_text="orders later", row=1, col=1); fig.update_yaxes(title_text="ticks", range=[0, 1.1], row=1, col=1)
fig.add_vrect(x0=0.5, x1=20.5, fillcolor="#eef3fb", line_width=0, row=1, col=2)
fig.add_scatter(x=xs, y=m_perm, mode="lines", name="permanent impact", line=dict(color=MUTED, width=2, dash="dot", shape="hv"), row=1, col=2)
fig.add_scatter(x=xs, y=m_fade, mode="lines", name="fading impact", line=dict(color=OFI_C, width=2, shape="hv"), row=1, col=2)
fig.add_annotation(x=10, y=float(m_perm[19]) + 1.5, text="20 buys", showarrow=False, font=dict(size=10, color=MUTED), row=1, col=2)
fig.update_xaxes(title_text="order number", row=1, col=2); fig.update_yaxes(title_text="mid, ticks from the start", row=1, col=2)
fig.add_scatter(x=lags, y=R, mode="lines+markers", name="response R: the move after an order, in its direction", line=dict(color=TI_C, width=2),
                marker=dict(size=6), row=1, col=3)
fig.add_scatter(x=lags, y=G[lags - 1], mode="lines", name="bare impact G", line=dict(color=INK, width=2), row=1, col=3)
fig.update_xaxes(type="log", title_text="orders later (log scale)", row=1, col=3); fig.update_yaxes(title_text="ticks", rangemode="tozero", row=1, col=3)
fig.update_layout(title="Impact over time on invented orders: each order's own impact fades, yet the price keeps moving, because buys follow buys<br>"
                        f"<sup>Invented: each order moves the mid by {G1:.0f} tick at once, fading as (orders later)^−{BETA}; the correlation of the signs of two orders "
                        f"l apart is {C1} l^−{GAMMA}, as when large orders are split into many small ones</sup>",
                  height=470, width=1250, margin=dict(t=110, l=60, r=20, b=50), legend=dict(orientation="h", y=-0.22, x=0.0))
save_figure(fig, L20.PREFIX + "20_04_impact_card", FIG)
print("story: after 20 buys fade", round(m_fade[19], 1), "perm", m_perm[19], "end fade", round(m_fade[-1], 1), "perm", m_perm[-1])
