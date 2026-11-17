"""Lecture 22 §2: the life of an order in a replay (redrawn from E27's l21_s2_cards.py with this lecture's section numbers).
Output: figures/21_09_order_life.png. Usage: python l22_order_life.py"""
import sys
from pathlib import Path
import plotly.graph_objects as go
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402
apply_theme()

# 21_09: the life of an order in a replay, step by step, with the family of models that covers each step and the card that introduced it.
STEPS = [("1. Decide", "on the book we see", "feed latency", "§2.2"), ("2. Travel", "to the exchange", "latency models", "§2.2"),
         ("3. Arrive", "a market order fills here", "order types: market, IOC, limit", "§2.2"), ("4. Wait", "in the line", "queue models", "§2.3"),
         ("5. Filled?", "a trade reaches us", "fill rules, fill probability", "§1, §2.3"), ("6. After", "the price moves on", "adverse selection, markout", "§2.4")]
fig = go.Figure()
for i, (a, b, fam, sec) in enumerate(STEPS):
    x0 = i * 1.62
    fig.add_shape(type="rect", x0=x0, x1=x0 + 1.38, y0=0.35, y1=1.15, line=dict(color=INK, width=1), fillcolor="white")
    fig.add_annotation(x=x0 + 0.69, y=0.93, text=f"<b>{a}</b>", showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.69, y=0.7, text=b, showarrow=False, font=dict(size=11, color=INK))
    fig.add_annotation(x=x0 + 0.69, y=0.5, text=f"<i>{sec}</i>", showarrow=False, font=dict(size=10, color=MUTED))
    fig.add_shape(type="rect", x0=x0, x1=x0 + 1.38, y0=-0.3, y1=0.15, line=dict(color=SERIES[0], width=1), fillcolor="#eef3fb")
    fig.add_annotation(x=x0 + 0.69, y=-0.075, text=fam, showarrow=False, font=dict(size=11, color=INK))
    if i < len(STEPS) - 1:
        fig.add_annotation(x=x0 + 1.6, y=0.75, ax=x0 + 1.4, ay=0.75, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowcolor=MUTED, text="")
fig.add_annotation(x=-0.05, y=-0.075, text="models:", showarrow=False, xanchor="right", font=dict(size=11, color=SERIES[0]))
fig.add_shape(type="rect", x0=0, x1=1.62 * 5 + 1.38, y0=-0.75, y1=-0.45, line=dict(color=MUTED, width=1, dash="dot"), fillcolor="#f4f4f2")
fig.add_annotation(x=(1.62 * 5 + 1.38) / 2, y=-0.6, text="across every step: our footprint, left out here (§2.5) and added back in §5 and §6",
                   showarrow=False, font=dict(size=11, color=INK))
fig.update_xaxes(visible=False, range=[-0.8, 9.6]); fig.update_yaxes(visible=False, range=[-0.85, 1.25])
fig.update_layout(title="The life of an order in a replay: six steps, and the family of models that covers each"
                        "<br><sup>Top: what happens to our order; middle, blue: the models used for that step; the cards of Section 2 that introduce them</sup>",
                  height=360, width=1300, margin=dict(t=80, l=30, r=20, b=10), showlegend=False)
save_figure(fig, "21_09_order_life", HERE.parent / "figures")
