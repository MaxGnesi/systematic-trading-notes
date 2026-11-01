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

# 21_04: the latency gap. The same invented book, ask side: we decide at 10 ms to buy 0.5 BTC on the book last seen; a faster buyer takes 0.4 BTC
# at the best ask at 40 ms; our order arrives at 60 ms. Right: the failure probability of minimum-size market orders on Bybit against the return
# that followed them, the model of Albers, Cucuringu, Howison and Shestopaloff (2025), eq. (17) with their Table 6 (Bybit BTC).
ASKS_SEEN = [(100_000.1, 0.6), (100_000.2, 1.5), (100_000.3, 2.0)]
FAST, BUY = 0.4, 0.5
ASKS_MET = [(p, q - FAST if i == 0 else q) for i, (p, q) in enumerate(ASKS_SEEN)]


def walk(book, size):
    """Fills of a market buy of `size` walking `book` [(price, size), ...]: [(price, filled), ...]."""
    out = []
    for p, q in book:
        if size <= 1e-12: break
        f = min(q, size); out.append((p, f)); size -= f
    return out


exp, got = walk(ASKS_SEEN, BUY), walk(ASKS_MET, BUY)
avg = lambda f: sum(p * q for p, q in f) / sum(q for _, q in f)
print("expected", exp, round(avg(exp), 2), "met", got, round(avg(got), 3), "IOC at the best:", got[0])
C_, A_, B_ = 0.00088, 0.0424, 0.02187
fig = make_subplots(rows=1, cols=3, column_widths=[0.27, 0.27, 0.46], horizontal_spacing=0.09,
                    subplot_titles=("10 ms: the book we decide on", "60 ms: the book our order meets",
                                    "Bybit, live orders: missing the best price"))
ylab = [f"USD {p:,.1f}" for p, _ in ASKS_SEEN]
for col, book, fills, lab in ((1, ASKS_SEEN, exp, "we expect to buy"), (2, ASKS_MET, got, "our market order buys")):
    ours = [dict(fills).get(p, 0.0) for p, _ in book]
    fig.add_bar(y=ylab, x=ours, orientation="h", marker_color=SERIES[0] if col == 2 else "#8fb8ea", name=lab,
                text=[f"{q:.1f}" if q else "" for q in ours], textposition="inside", insidetextanchor="middle", textangle=0, textfont=dict(color="white", size=11), row=1, col=col)
    fig.add_bar(y=ylab, x=[q - o for (_, q), o in zip(book, ours)], orientation="h", marker_color=GRID, showlegend=False,
                text=[f"{q - o:.1f}" if q - o > 0.15 else "" for (_, q), o in zip(book, ours)], textposition="inside", textfont=dict(color=INK, size=11),
                row=1, col=col)
    fig.update_xaxes(title_text="BTC offered", range=[0, 2.2], row=1, col=col)
fig.add_annotation(x=0.3, y=ylab[0], text=f"a faster buyer took {FAST:.1f} at 40 ms", showarrow=False, xanchor="left", font=dict(size=10, color=INK),
                   row=1, col=2)
for c in (1, 2): fig.update_yaxes(type="category", categoryorder="array", categoryarray=ylab, row=1, col=c)
xs = [x / 10 for x in range(-50, 101)]
ys = [C_ if x <= 0 else A_ + B_ * x for x in xs]
fig.add_scatter(x=[x for x in xs if x <= 0], y=[C_] * sum(x <= 0 for x in xs), mode="lines", line=dict(color=INK, width=2), showlegend=False, row=1, col=3)
fig.add_scatter(x=[x for x in xs if x > 0], y=[A_ + B_ * x for x in xs if x > 0], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=1, col=3)
for x in (5, 10):
    fig.add_annotation(x=x, y=A_ + B_ * x, text=f"+{x} bp: {A_ + B_ * x:.0%}", showarrow=True, arrowhead=0, ax=-45, ay=-20, font=dict(size=10, color=INK),
                       row=1, col=3)
fig.add_annotation(x=-2.5, y=0.03, text=f"price fell or stayed: {C_:.1%}", showarrow=False, font=dict(size=10, color=INK), row=1, col=3)
fig.update_xaxes(title_text="return after the order, bp (positive: in the order's favour)", zeroline=True, zerolinecolor=GRID, row=1, col=3)
fig.update_yaxes(title_text="share of orders that missed it", tickformat=".0%", range=[0, 0.3], row=1, col=3)
fig.update_layout(barmode="stack", bargap=0.35,
                  title="The latency gap: our order meets a later book than the one we decided on,<br>and that book has most likely changed when the trade would have paid"
                        "<br><sup>Left and middle: the invented book of §2.1, ask side; we decide at 10 ms to buy 0.5 BTC, the order arrives at 60 ms. "
                        "Right: Albers et al. (2025), eq. 17, fitted on 3.1 million minimum-size market orders, Bybit BTCUSD inverse perpetual, April 2023</sup>",
                  height=500, width=1300, margin=dict(t=150, l=110, r=30, b=60), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L21.PREFIX + "21_04_latency_card", FIG)

# 21_05: the queue. The bid of §2.1 joins at 60 ms behind 1.7 BTC; the invented book runs on to 450 ms. Events at our price: sells (trades) and
# book updates (displayed size). Under each value of the dial a, the size ahead of us and the moment we are filled. Right: the share of a
# cancellation put ahead of us, p = x^a, against our relative position x = ahead / (ahead + behind).
EV = [(70, "t", 0.2), (100, "u", 1.2), (130, "t", 0.4), (200, "u", 1.6), (250, "t", 0.2), (300, "u", 0.6), (340, "t", 0.5), (420, "x", 0.3)]                               # "x": a sell below our price
JOIN, AHEAD0 = 60, 1.7
DIALS = [(1.0, "a = 1: split evenly", SERIES[0], "solid"), (2.0, "a = 2", "#5d9be3", "dot"), (float("inf"), "a = ∞: all behind us where possible", "#8fb8ea", "dash")]


def queue(a):
    """Size ahead of the bid and the displayed size after each event, under dial a; the time of the fill (None if not filled)."""
    ahead, level, tsum, path = AHEAD0, AHEAD0, 0.0, [(JOIN, AHEAD0, AHEAD0)]
    for t, kind, v in EV:
        if kind == "x": return path + [(t, 0.0, 0.0)], t                          # the price runs through: filled
        if kind == "t":
            if v > ahead: return path + [(t, 0.0, level - v)], t
            ahead -= v; level -= v; tsum += v
        else:
            d = level - v
            if d > 0:
                x = min(ahead / level, 1.0); behind = min(((1 - x ** a) if a != float("inf") else 1.0) * d if x < 1 else 0.0, level - ahead)
                ahead -= d - behind
            level, tsum = v, 0.0
        path.append((t, ahead, level))
    return path, None


fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.1,
                    subplot_titles=("Our bid in the line: size ahead of it under three dials", "The dial: share of a cancellation put ahead of us"))
P1, _ = queue(1.0)
fig.add_scatter(x=[t for t, _, _ in P1] + [420], y=[q for _, _, q in P1] + [P1[-1][2]], mode="lines", line=dict(color=MUTED, width=1.5, shape="hv"),
                name="displayed size at our price (without ours)", row=1, col=1)
fills = {}
for a, lab, c, dash in DIALS:
    P, tf = queue(a); fills[a] = tf
    fig.add_scatter(x=[t for t, _, _ in P], y=[q for _, q, _ in P], mode="lines", line=dict(color=c, width=2.5, dash=dash, shape="hv"),
                    name=f"size ahead of us, {lab}", row=1, col=1)
    fig.add_scatter(x=[tf], y=[0], mode="markers", marker=dict(symbol="star", size=14, color=c, line=dict(width=1, color=INK)), showlegend=False, row=1, col=1)
fig.add_scatter(x=[t for t, k, _ in EV if k == "t"], y=[-0.22] * 4, mode="markers+text", marker=dict(symbol="triangle-down", size=11, color=TRADE_C),
                text=[f"{v:.1f}" for t, k, v in EV if k == "t"], textposition="middle right", textfont=dict(size=10, color=INK),
                name="sell trade at our price (BTC)", row=1, col=1)
fig.add_scatter(x=[420], y=[-0.22], mode="markers+text", marker=dict(symbol="x-thin-open", size=11, color=MUTED, line=dict(width=2, color=MUTED)),
                text=["0.3 below"], textposition="middle right", textfont=dict(size=10, color=INK), name="sell trade below our price", row=1, col=1)
fig.add_scatter(x=[70, 70], y=[0, 2.0], mode="lines", line=dict(color=SERIES[1], width=2), name="touch rule: filled by the first trade", row=1, col=1)
for t, lab in ((100, "cancelled 0.3:<br>all ahead, none behind yet"), (200, "added 0.8:<br>behind us"), (300, "cancelled 0.8:<br>whose?")):
    fig.add_annotation(x=t, y=2.05, text=lab, showarrow=False, yanchor="bottom", font=dict(size=10, color=INK), row=1, col=1)
fig.update_xaxes(title_text="milliseconds", range=[40, 455], row=1, col=1)
fig.update_yaxes(title_text="BTC", range=[-0.4, 2.55], row=1, col=1)
xs = [i / 100 for i in range(101)]
for a, lab, c in ((1, "a = 1", SERIES[0]), (2, "a = 2", "#5d9be3"), (5, "a = 5", "#8fb8ea"), (20, "a = 20", GRID)):
    fig.add_scatter(x=xs, y=[x ** a for x in xs], mode="lines", line=dict(color=c, width=2), showlegend=False, row=1, col=2)
    fig.add_annotation(x=0.72, y=0.72 ** a, text=lab, showarrow=False, xanchor="left", xshift=4, yshift=6, font=dict(size=10, color=INK), row=1, col=2)
fig.add_scatter(x=[0, 0.995, 1], y=[0, 0, 1], mode="lines", line=dict(color=INK, width=1.5, dash="dash"), showlegend=False, row=1, col=2)
fig.add_annotation(x=0.35, y=0.06, text="a = ∞: nothing ahead unless<br>nobody is behind", showarrow=False, font=dict(size=10, color=INK), row=1, col=2)
fig.add_scatter(x=[0.6 / 1.4], y=[0.6 / 1.4], mode="markers", marker=dict(size=9, color=INK), showlegend=False, row=1, col=2)
fig.add_annotation(x=0.6 / 1.4, y=0.6 / 1.4, text="our bid at 300 ms", showarrow=True, ax=-60, ay=-30, font=dict(size=10, color=INK), row=1, col=2)
fig.update_xaxes(title_text="our position x: share of the line ahead of us", range=[0, 1], row=1, col=2)
fig.update_yaxes(title_text="share of a cancellation ahead of us, p", range=[0, 1.02], row=1, col=2)
fig.update_layout(title="The queue: L2 shows how long the line is, not who leaves it; the assumption about who cancels decides when our turn comes"
                        "<br><sup>The invented bid of §2.1 at USD 100,000.0, joining at 60 ms behind 1.7 BTC; stars mark the fill under each dial</sup>",
                  height=520, width=1300, margin=dict(t=100, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, L21.PREFIX + "21_05_queue_card", FIG)
print("queue fills", fills, {a: [(t, round(q, 3), round(l, 3)) for t, q, l in queue(a)[0]] for a, *_ in DIALS})
