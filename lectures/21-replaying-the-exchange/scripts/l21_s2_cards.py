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

# 21_06: the queue models of the literature side by side: the share of a cancellation each puts ahead of us, against our position x, for a line
# of 1.4 BTC (the log models depend on the sizes, not only on x); the dots mark the cancellation at 300 ms of 21_05 (0.6 BTC ahead, 0.8 behind).
# Formulas as in Rigtorp (2013) and in hftbacktest's queue.rs: there "prob" is the share BEHIND us, so the share ahead is 1 - prob.
import math
LINE = 1.4
MODELS = [  # (label, share ahead as a function of (front, back), colour, dash)
    ("even split: Rigtorp with f = identity; hftbacktest power, n = 1; our a = 1", lambda f, b: f / (f + b), SERIES[0], "solid"),
    ("Rigtorp with f = log(1 + x); hftbacktest log", lambda f, b: math.log1p(f) / (math.log1p(f) + math.log1p(b)), SERIES[3], "solid"),
    ("hftbacktest log, variant 2", lambda f, b: 1 - math.log1p(b) / math.log1p(f + b), SERIES[3], "dot"),
    ("hftbacktest power, n = 2", lambda f, b: f ** 2 / (f ** 2 + b ** 2), SERIES[4], "solid"),
    ("hftbacktest power variant 2, n = 2", lambda f, b: 1 - (b / (f + b)) ** 2, SERIES[4], "dot"),
    ("hftbacktest power variant 3, n = 2; our a = 2", lambda f, b: (f / (f + b)) ** 2, "#5d9be3", "dash"),
    ("hftbacktest risk-averse; our a = ∞", lambda f, b: 0.0 if b > 0 else 1.0, INK, "dash"),
]
fig = make_subplots(rows=1, cols=2, column_widths=[0.58, 0.42], horizontal_spacing=0.1,
                    subplot_titles=("Each model's share, by our position in the line", "How the parameter moves it, at our position x = 0.43"))
xs = [i / 200 for i in range(1, 200)]
for lab, fn, c, dash in MODELS:
    fig.add_scatter(x=xs, y=[fn(x * LINE, (1 - x) * LINE) for x in xs], mode="lines", line=dict(color=c, width=2, dash=dash), name=lab, row=1, col=1)
    v = fn(0.6, 0.8)
    fig.add_scatter(x=[0.6 / 1.4], y=[v], mode="markers", marker=dict(size=8, color=c, line=dict(width=1, color=INK)), showlegend=False, row=1, col=1)
    print(f"{lab}: share ahead {v:.3f}, size ahead after {0.6 - v * 0.8 + min(0.8 - (1 - v) * 0.8, 0):.3f}")
fig.add_vline(x=0.6 / 1.4, line=dict(color=GRID, width=1), row=1, col=1)
fig.update_xaxes(title_text="our position x (0 = front, 1 = back)", range=[0, 1], row=1, col=1)
fig.update_yaxes(title_text="share of a cancellation put ahead of us", range=[-0.02, 1.05], row=1, col=1)
# right (annotations on a log axis take log10 of x): the share at x = 0.43 against the parameter n (or a) of the three power families
X0 = 0.6 / 1.4; ns = [1 + i / 10 for i in range(0, 191)]
for lab, fn, c, dash in (("power variant 3, x^n = our dial x^a", lambda n: X0 ** n, "#5d9be3", "dash"),
                         ("power, x^n / (x^n + (1 - x)^n)", lambda n: X0 ** n / (X0 ** n + (1 - X0) ** n), SERIES[4], "solid"),
                         ("power variant 2, 1 - (1 - x)^n", lambda n: 1 - (1 - X0) ** n, SERIES[4], "dot")):
    fig.add_scatter(x=ns, y=[fn(n) for n in ns], mode="lines", line=dict(color=c, width=2, dash=dash), showlegend=False, row=1, col=2)
    fig.add_annotation(x=math.log10(3.2), y=fn(3.2), text=lab, showarrow=False, xanchor="left", xshift=6, font=dict(size=10, color=INK), row=1, col=2)
fig.add_hline(y=X0, line=dict(color=SERIES[0], width=1), row=1, col=2)
fig.add_annotation(x=math.log10(20), y=X0, text="even split, n = 1", showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=10, color=SERIES[0]), row=1, col=2)
fig.update_xaxes(title_text="parameter n (for our dial: a)", type="log", tickvals=[1, 2, 5, 10, 20], range=[0, 1.31], row=1, col=2)
fig.update_yaxes(title_text="share ahead of us at x = 0.43", range=[-0.02, 1.05], row=1, col=2)
fig.update_layout(title="Queue models disagree most in the middle of the line, and their parameters push in opposite directions"
                        "<br><sup>Left: the share of a cancellation each model puts ahead of our order, for a line of 1.4 BTC in units of 1 BTC; dots: the cancellation "
                        "of 0.8 BTC at 300 ms in Figure 21_05. Right: the same share at that position as the parameter of the power models grows</sup>",
                  height=600, width=1300, margin=dict(t=100, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.17, x=0, font=dict(size=11)))
save_figure(fig, L21.PREFIX + "21_06_queue_models", FIG)

# 21_07: adverse fills. Left: DeLise (2024), eq. 3: the expected move after a fill of a bid, in ticks, when the next move is down with probability
# P(D) (the price runs through our bid: always filled) or up with P(U) = 1 - P(D) (filled only with probability R_f before it leaves), against R_f.
# Right: the bid of §1 on 1 October 2025 (results/key/day_orders.parquet): the share of each rule's fills made as the price ran through our level,
# and the mid 10 s after those fills and after the others.
import polars as pl
fig = make_subplots(rows=1, cols=3, column_widths=[0.4, 0.28, 0.32], horizontal_spacing=0.09,
                    subplot_titles=("A fair coin, yet the fill predicts a fall", "1 October: fills made as the price ran through",
                                    "1 October: mid 10 s after the fill"))
rs = [i / 100 for i in range(0, 101)]
for pu, c, dash in ((0.5, INK, "solid"), (0.6, MUTED, "dash"), (0.4, MUTED, "dot")):
    pd_ = 1 - pu
    fig.add_scatter(x=rs, y=[(r * pu - pd_) / (pd_ + r * pu) for r in rs], mode="lines", line=dict(color=c, width=2, dash=dash),
                    name=f"next move up with probability {pu:.0%}", row=1, col=1)
fig.add_scatter(x=[0.3], y=[(0.3 * 0.5 - 0.5) / (0.5 + 0.15)], mode="markers", marker=dict(size=9, color=SERIES[0]), showlegend=False, row=1, col=1)
fig.add_annotation(x=0.3, y=(0.15 - 0.5) / 0.65, text="R = 0.3: −0.54 ticks", showarrow=True, ax=70, ay=40, font=dict(size=10, color=INK), row=1, col=1)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=1, col=1)
fig.update_xaxes(title_text="R: chance of a fill when the price moves away from us", range=[0, 1], row=1, col=1)
fig.update_yaxes(title_text="expected move after a fill, ticks", range=[-1.05, 0.45], row=1, col=1)
DD = pl.read_parquet(L21.result_path(L21.KEY, "day_orders.parquet"))
rules = [("q0", "touch", SERIES[1]), ("q2", "queue, a = 1", SERIES[0]), ("q2i", "queue, a = ∞", "#8fb8ea")]
adv, m_adv, m_non = [], [], []
for k, lab, c in rules:
    f = DD.filter(pl.col(k).is_not_null()); a = (f[k] == f["q1"]).fill_null(False)
    adv.append(a.mean()); m_adv.append(f.filter(a)[f"{k}_m10"].mean()); m_non.append(f.filter(~a)[f"{k}_m10"].mean())
fig.add_bar(x=[l for _, l, _ in rules], y=adv, marker_color=[c for *_, c in rules], text=[f"{v:.0%}" for v in adv], textposition="outside",
            textfont=dict(size=10, color=INK), showlegend=False, row=1, col=2)
fig.update_yaxes(tickformat=".0%", range=[0, 0.9], row=1, col=2)
fig.add_bar(x=[l for _, l, _ in rules], y=m_adv, marker_color=MUTED, name="fills made as the price ran through", text=[f"{v:+.2f}" for v in m_adv],
            textposition="outside", textfont=dict(size=10, color=INK), row=1, col=3)
fig.add_bar(x=[l for _, l, _ in rules], y=m_non, marker_color=GRID, name="other fills", text=[f"{v:+.2f}" for v in m_non], textposition="outside",
            textfont=dict(size=10, color=INK), row=1, col=3)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=1, col=3)
fig.update_yaxes(title_text="bp: mid minus our price", range=[-0.95, 0.1], row=1, col=3)
fig.update_layout(barmode="group", title="Adverse fills: a fall through our price always fills our bid, a rise only sometimes, so the fills we get lean towards losses"
                        "<br><sup>Left: DeLise (2024), eq. 3: a bid at the best; the next move is one tick down (traded through: filled) or one tick up (filled only with chance R). Middle and right: the resting bid of 0.001 BTC of §1, "
                        "every 15 s of 1 October 2025, Bybit BTCUSDT (one in-sample day)</sup>",
                  height=500, width=1300, margin=dict(t=100, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L21.PREFIX + "21_07_adverse_card", FIG)
print("adverse", [round(x, 3) for x in adv], [round(x, 3) for x in m_adv], [round(x, 3) for x in m_non])

# 21_08: our footprint. Left: the ask side of §2.2 at 100 ms, as recorded and as it would stand after our market buy of 0.5 BTC at 60 ms (if
# nobody refilled). Right: the size displayed at the best bid when the bid of §1 was placed, every 15 s of 1 October 2025 (results/key), as a
# cumulative share, with the five order sizes of the lecture.
REC = [(100_000.1, 0.2), (100_000.2, 1.5), (100_000.3, 2.0)]
after = [(100_000.1, 0.2 - 0.2), (100_000.2, 1.5 - 0.3), (100_000.3, 2.0)]
fig = make_subplots(rows=1, cols=3, column_widths=[0.25, 0.25, 0.5], horizontal_spacing=0.08,
                    subplot_titles=("100 ms, as recorded", "100 ms, after our buy",
                                    "1 October: size at the best bid, and our order sizes"))
yl = [f"USD {p:,.1f}" for p, _ in REC]
for col, book, c in ((1, REC, GRID), (2, after, GRID)):
    fig.add_bar(y=yl, x=[q for _, q in book], orientation="h", marker_color=c, showlegend=False, text=[f"{q:.1f}" for _, q in book],
                textposition="outside", textfont=dict(size=11, color=INK), row=1, col=col)
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=yl, row=1, col=col)
    fig.update_xaxes(title_text="BTC offered", range=[0, 2.6], row=1, col=col)
fig.add_annotation(x=0.3, y=yl[0], text="taken by us: the best ask<br>is now one tick higher", showarrow=False, xanchor="left", font=dict(size=10, color=SERIES[0]),
                   row=1, col=2)
fig.add_annotation(x=0.55, y=yl[0], text="still here in the record:<br>a second order of ours<br>would buy it again", showarrow=False, xanchor="left",
                   font=dict(size=10, color=INK), row=1, col=1)
DQ = pl.read_parquet(L21.result_path(L21.KEY, "day_orders.parquet"))["q"].sort().to_list()
n = len(DQ)
fig.add_scatter(x=DQ, y=[(i + 1) / n for i in range(n)], mode="lines", line=dict(color=INK, width=2), showlegend=False, row=1, col=3)
for s in (0.001, 0.01, 0.1, 1, 5):
    sh = sum(q < s for q in DQ) / n
    fig.add_scatter(x=[s, s], y=[0, 1], mode="lines", line=dict(color=SERIES[0], width=1, dash="dot"), showlegend=False, row=1, col=3)
    fig.add_annotation(x=math.log10(s), y=1.0, text=f"{s:g} BTC<br>{sh:.1%}", showarrow=False, yanchor="bottom", font=dict(size=10, color=INK), row=1, col=3)
fig.update_xaxes(title_text="BTC at the best bid (log scale)", type="log", range=[-3.3, 1.8], row=1, col=3)
fig.update_yaxes(title_text="share of moments with at most this size", tickformat=".0%", range=[0, 1.18], row=1, col=3)
fig.update_layout(title="Our footprint: the replay assumes our orders take nothing and change nothing; that holds for the smallest orders, not for the largest"
                        "<br><sup>Left and middle: the invented ask side of §2.2 at 100 ms, after our market buy of 0.5 BTC at 60 ms, before anyone refills.<br>"
                        "Right: Bybit BTCUSDT, 1 October 2025, every 15 s; the percentages are the share of moments in which the whole best queue was smaller than our order</sup>",
                  height=520, width=1300, margin=dict(t=130, l=110, r=30, b=60))
save_figure(fig, L21.PREFIX + "21_08_footprint_card", FIG)

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
fig.add_annotation(x=(1.62 * 5 + 1.38) / 2, y=-0.6, text="across every step: our footprint, left out here (§2.5) and added back in Lecture 22",
                   showarrow=False, font=dict(size=11, color=INK))
fig.update_xaxes(visible=False, range=[-0.8, 9.6]); fig.update_yaxes(visible=False, range=[-0.85, 1.25])
fig.update_layout(title="The life of an order in a replay: six steps, and the family of models that covers each"
                        "<br><sup>Top: what happens to our order; middle, blue: the models used for that step; the cards of Section 2 that introduce them</sup>",
                  height=360, width=1300, margin=dict(t=80, l=30, r=20, b=10), showlegend=False)
save_figure(fig, L21.PREFIX + "21_09_order_life", FIG)
