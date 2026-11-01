"""Lecture 21 §2, the cards on invented data. 21_03: what a replay is: the two recorded streams (the book every 100 ms, the trades to the
millisecond) at one price, and what the replay infers from them by merging them in time order: size traded, cancelled and added."""
import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme()
FIG = L21.FIG; FIG.mkdir(parents=True, exist_ok=True)
TRADE_C, CANCEL_C, ADD_C = SERIES[1], MUTED, SERIES[2]

# the running example: the bid at USD 100,000.0; three book updates and three sell trades at that price
BOOK = [(0, 2.0), (100, 1.2), (200, 1.6)]                                        # (ms, size displayed at our price)
TRADES = [(30, 0.3), (70, 0.2), (130, 0.4)]                                      # (ms, size sold at our price)
DECIDE, LAT = 10, 50

# what the replay infers: trades first between two updates, then the rest of the change at the update
steps, size = [(0, 2.0, None)], 2.0
for (t0, q0), (t1, q1) in zip(BOOK, BOOK[1:]):
    for t, s in TRADES:
        if t0 < t < t1: size -= s; steps.append((t, size, "trade"))
    steps.append((t1, q1, "cancel" if q1 < size else "add")); size = q1

fig = make_subplots(rows=2, cols=1, row_heights=[0.38, 0.62], vertical_spacing=0.16,
                    subplot_titles=("What is recorded: two streams at our price", "What the replay infers: the two streams merged in time order"))
# row 1: two lanes
fig.add_scatter(x=[t for t, _ in BOOK], y=[1] * 3, mode="markers+text", marker=dict(symbol="square", size=13, color=INK),
                text=[f"{q:.1f} BTC" for _, q in BOOK], textposition="top center", textfont=dict(size=11, color=INK), name="book update: size displayed",
                row=1, col=1)
fig.add_scatter(x=[t for t, _ in TRADES], y=[0] * 3, mode="markers+text", marker=dict(symbol="triangle-down", size=13, color=TRADE_C),
                text=[f"sold {s:.1f}" for _, s in TRADES], textposition="bottom center", textfont=dict(size=11, color=INK),
                name="sell trade at our price", row=1, col=1)
fig.update_yaxes(tickvals=[0, 1], ticktext=["trades<br>(each ms)", "book<br>(every 100 ms)"], range=[-0.9, 1.9], showgrid=False, row=1, col=1)
# row 2: the inferred size, segment by segment, coloured by cause
prev_t, prev_q = 0, 2.0
for t, q, why in steps[1:]:
    fig.add_scatter(x=[prev_t, t], y=[prev_q, prev_q], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=2, col=1)
    c = {"trade": TRADE_C, "cancel": CANCEL_C, "add": ADD_C}[why]
    fig.add_scatter(x=[t, t], y=[prev_q, q], mode="lines", line=dict(color=c, width=5), showlegend=False, row=2, col=1)
    lab = {"trade": f"traded {prev_q - q:.1f}", "cancel": f"cancelled {prev_q - q:.1f}", "add": f"added {q - prev_q:.1f}"}[why]
    fig.add_annotation(x=t, y=(prev_q + q) / 2, text=lab, showarrow=False, xanchor="left", xshift=6, font=dict(size=11, color=INK), row=2, col=1)
    prev_t, prev_q = t, q
fig.add_scatter(x=[prev_t, 230], y=[prev_q, prev_q], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=2, col=1)
for c, lab in ((TRADE_C, "decrease from a trade"), (CANCEL_C, "decrease beyond the trades: cancelled"), (ADD_C, "increase: added")):
    fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=c, width=5), name=lab, row=2, col=1)
for t, lab in ((DECIDE, "we decide<br>to bid"), (DECIDE + LAT, "our bid<br>arrives")):
    fig.add_scatter(x=[t, t], y=[0, 2.3], mode="lines", line=dict(color=SERIES[0], width=1.5, dash="dot"), showlegend=False, row=2, col=1)
    fig.add_annotation(x=t, y=2.3, text=lab, showarrow=False, yanchor="bottom", font=dict(size=10, color=SERIES[0]), row=2, col=1)
fig.update_yaxes(title_text="BTC at our price", range=[0, 2.75], row=2, col=1)
for r in (1, 2): fig.update_xaxes(range=[-10, 235], dtick=50, row=r, col=1)
fig.update_xaxes(title_text="milliseconds", row=2, col=1)
fig.update_layout(title="A replay merges two recorded streams: trades explain part of each change at our price, the rest was cancelled or added"
                        "<br><sup>Invented example: the bid at USD 100,000.0, three book updates 100 ms apart and three sell trades between them</sup>",
                  height=600, width=1100, margin=dict(t=95, l=120, r=30, b=60), legend=dict(orientation="h", y=-0.14, x=0))
save_figure(fig, L21.PREFIX + "21_03_replay_card", FIG)
print(steps)
