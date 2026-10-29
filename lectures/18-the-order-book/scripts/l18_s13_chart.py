"""Lecture 18 figure 18_02b: the path of an order through an exchange (schematic). The trader's order travels to the gateway, the sequencer and the
matching engine; the market data publisher shows the result to everyone; clearing and risk sit under the matching engine. Under each step, what it
decides and the example of Bybit; above, where message caps, speed bumps, maker priority and bundling of the feed act."""
import sys
from pathlib import Path
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme()
FILL, CUR = "#eef3fb", "#f4f4f2"
steps = [("Trader", "sends an order", "", "", ""),
         ("1. Gateway", "lets it in, and when", "account and risk checks,<br>message caps", "Bybit: about 10 orders<br>a second per account", "Binance: 300 orders per 10 s,<br>1,200 a minute, per account"),
         ("2. Sequencer", "puts messages in order", "first come, first served,<br>or by type within a block", "Bybit: by arrival", "Binance: by arrival"),
         ("3. Matching engine", "trades it against the book", "priority among resting<br>orders at a price", "Bybit: price, then time*", "Binance: price, then time*"),
         ("4. Market data", "shows the result", "what is published,<br>and how often", "Bybit: 200 levels every 100 ms,<br>the best level every 10 ms", "Binance: changes every 100,<br>250 or 500 ms; best 5-20 levels")]
W, G, Y0, Y1 = 1.55, 0.5, 0.0, 1.0
fig = go.Figure()
for i, (name, does, decides, bybit, binance) in enumerate(steps):
    x0 = i * (W + G)
    fig.add_shape(type="rect", x0=x0, x1=x0 + W, y0=Y0, y1=Y1, line=dict(color=INK if i == 3 else MUTED, width=2 if i == 3 else 1),
                  fillcolor=FILL if i == 3 else ("white" if i == 0 else CUR))
    fig.add_annotation(x=x0 + W / 2, y=0.68, text=f"<b>{name}</b>", showarrow=False, font=dict(size=13, color=INK))
    fig.add_annotation(x=x0 + W / 2, y=0.35, text=f"<i>{does}</i>", showarrow=False, font=dict(size=11, color=MUTED))
    if decides:
        fig.add_annotation(x=x0 + W / 2, y=-0.32, text=decides, showarrow=False, font=dict(size=10.5, color=INK))
        fig.add_annotation(x=x0 + W / 2, y=-0.78, text=bybit, showarrow=False, font=dict(size=10, color=SERIES[0]))
        fig.add_annotation(x=x0 + W / 2, y=-1.22, text=binance, showarrow=False, font=dict(size=10, color=SERIES[2]))
    if i < len(steps) - 1:
        fig.add_annotation(x=x0 + W + G - 0.03, y=0.5, ax=x0 + W + 0.03, ay=0.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowwidth=1.5, arrowcolor=MUTED, text="")
fig.add_annotation(x=W + G / 2, y=0.62, text="latency", showarrow=False, font=dict(size=10, color=MUTED))
# the feed goes back to every trader
x4 = 4 * (W + G) + W - 0.12
fig.add_shape(type="path", path=f"M {x4},{Y1} C {x4},{Y1 + 0.75} {W / 2},{Y1 + 0.75} {W / 2},{Y1 + 0.04}", line=dict(color=MUTED, width=1.2, dash="dot"))
fig.add_annotation(x=W / 2, y=Y1 + 0.02, ax=W / 2, ay=Y1 + 0.25, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2, arrowcolor=MUTED, text="")
fig.add_annotation(x=x4 / 2 + W / 4, y=Y1 + 0.66, text="what every trader sees, and reacts to", showarrow=False, font=dict(size=10, color=MUTED))
# clearing under the matching engine
x3 = 3 * (W + G)
fig.add_shape(type="rect", x0=x3, x1=x3 + W, y0=-2.3, y1=-1.7, line=dict(color=MUTED, width=1), fillcolor=CUR)
fig.add_annotation(x=x3 + W / 2, y=-2.0, text="<b>5. Clearing and risk</b><br><i>margin, liquidations</i>", showarrow=False, font=dict(size=11, color=INK))
fig.add_shape(type="line", x0=x3 + W / 2, x1=x3 + W / 2, y0=-1.45, y1=-1.68, line=dict(color=MUTED, width=1))
# where the defences of Lecture 19 act
for i, lab in ((1, "caps, speed bumps"), (2, "maker priority"), (3, "batch auctions"), (4, "bundling the feed")):
    fig.add_annotation(x=i * (W + G) + W / 2, y=Y1 + 0.18, text=lab, showarrow=False, font=dict(size=10, color=SERIES[1]))
fig.update_xaxes(visible=False, range=[-0.1, 5 * W + 4 * G + 0.1]); fig.add_annotation(x=x3 - 0.1, y=-2.0, text="both venues: liquidation in the market, then the insurance fund,<br>then auto-deleveraging of profitable positions on the other side",
                   xanchor="right", align="right", showarrow=False, font=dict(size=10, color=INK))
fig.update_yaxes(visible=False, range=[-2.4, 1.95])
fig.update_layout(title="The path of an order through an exchange: each step has its own rules, and together they are the venue's market model<br>"
                        "<sup>Schematic. Grey: what each step does; black: what it decides; blue: Bybit; green: Binance; orange: where the defences of Lecture 19, §2.1 act. "
                        "* The standard rule of continuous books, not stated in the venues' documents</sup>", height=600, width=1250, margin=dict(t=100, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L18.PREFIX + "18_02b_order_path", L18.FIG)
print("ok")
