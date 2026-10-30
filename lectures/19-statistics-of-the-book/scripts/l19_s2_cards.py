"""Lecture 19 §2, stylized pictures of the statistics (invented books, clearly labelled). 19_03: book imbalance, three ladders: a balanced book, a
thin best ask against a large best bid, and a balanced best price with a heavy book behind the bids; under each, the imbalance at the best and in the
best 5 levels, and what it suggests."""
import sys
from pathlib import Path
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme(); sys.stdout.reconfigure(encoding="utf-8")
FIG = L19.FIG; FIG.mkdir(parents=True, exist_ok=True)
BID, ASK = "#2a63b0", "#c0436f"
BEST_BID, TICK = 100_000.0, 0.1


def ladder(fig, x0, asks, bids, head, cap=4.0, pw=1.0, notes=()):
    """One ladder: asks above (best at the bottom), bids below (best at the top); bars full at `cap` BTC, sizes written in."""
    k = len(asks); rows = [("ask", BEST_BID + TICK * (i + 1), q) for i, q in reversed(list(enumerate(asks)))] + \
                          [("bid", BEST_BID - TICK * i, q) for i, q in enumerate(bids)]
    bx0, bx1 = x0 + 0.34, x0 + pw
    fig.add_annotation(x=x0 + pw / 2, y=2 * k + 0.9, text=f"<b>{head}</b>", showarrow=False, font=dict(size=13, color=INK))
    for i, (side, p, q) in enumerate(rows):
        y = 2 * k - 1 - i; best = i in (k - 1, k)
        fig.add_shape(type="rect", x0=x0, x1=x0 + pw, y0=y + 0.04, y1=y + 0.96, fillcolor="#fbe9f1" if side == "ask" else "#e7f0fb",
                      line=dict(color=INK if best else "rgba(0,0,0,0)", width=1.5 if best else 0))
        fig.add_annotation(x=x0 + 0.02, y=y + 0.5, text=f"{p:,.1f}", xanchor="left", showarrow=False, font=dict(size=11, color=INK))
        L = min(q, cap) / cap * (bx1 - bx0 - 0.15)
        fig.add_shape(type="rect", x0=bx0, x1=bx0 + L, y0=y + 0.2, y1=y + 0.8, fillcolor=ASK if side == "ask" else BID, line=dict(width=0))
        fig.add_annotation(x=bx0 + L + 0.015, y=y + 0.5, text=f"{q:.1f}" + (" ▶" if q > cap else ""), xanchor="left", showarrow=False, font=dict(size=10, color=INK))
    fig.add_shape(type="line", x0=x0, x1=x0 + pw, y0=k, y1=k, line=dict(color=INK, width=1.5))
    for j, (txt, size, col) in enumerate(notes):
        fig.add_annotation(x=x0 + pw / 2, y=-0.6 - 0.75 * j, text=txt, showarrow=False, font=dict(size=size, color=col))


def imb(b, a):
    return (b - a) / (b + a)


cases = [("A. Balanced", [0.9, 1.1, 0.8, 1.2, 1.0], [1.0, 0.9, 1.1, 1.0, 1.2], "both sides alike:<br>the next move is a coin flip"),
         ("B. A thin best ask", [0.4, 1.1, 0.8, 1.2, 1.0], [4.0, 0.9, 1.1, 1.0, 1.2], "one small buy empties the ask:<br>the next move is probably up"),
         ("C. Heavy bids behind the best", [0.5, 0.6, 0.5, 0.7, 0.6], [0.5, 3.0, 3.0, 2.5, 2.0], "balanced at the best, not behind it:<br>only the deeper measure sees it")]
fig = go.Figure(); PW, GAP = 1.0, 0.32
for c, (head, a, b, read) in enumerate(cases):
    i1, i5 = imb(b[0], a[0]), imb(sum(b), sum(a))
    ladder(fig, c * (PW + GAP), a, b, head, notes=((f"imbalance at the best: <b>{i1:+.2f}</b>", 12, INK), (f"in the best 5 levels: <b>{i5:+.2f}</b>", 12, INK),
                                                    (f"<i>{read}</i>", 11, MUTED)))
fig.add_annotation(x=-0.03, y=7.5, text="asks<br>(sell)", xanchor="right", showarrow=False, font=dict(size=11, color=ASK))
fig.add_annotation(x=-0.03, y=2.5, text="bids<br>(buy)", xanchor="right", showarrow=False, font=dict(size=11, color=BID))
fig.update_xaxes(visible=False, range=[-0.2, 3 * PW + 2 * GAP + 0.02]); fig.update_yaxes(visible=False, range=[-3.2, 11.5])
fig.update_layout(title="Book imbalance: which side outweighs the other, at the best price and deeper in the book<br>"
                        "<sup>Three invented books, the best 5 levels on each side, sizes in BTC (bars full at 4 BTC); the best bid and ask are outlined. "
                        "Imbalance = (bids − asks) / (bids + asks): −1 only asks, 0 balanced, +1 only bids</sup>",
                  height=640, width=1250, margin=dict(t=100, l=60, r=20, b=20), showlegend=False)
save_figure(fig, L19.PREFIX + "19_03_imbalance_card", FIG)
print("ok", [(h, round(imb(b[0], a[0]), 2), round(imb(sum(b), sum(a)), 2)) for h, a, b, _ in cases])


# 19_04: the microprice as the expected mid once the price has moved. Book B of 19_03 now; two branches with illustrative probabilities;
# a ruler with the mid now, the two future mids, the microprice (their probability-weighted average) and the weighted mid for comparison.
P_UP = 0.65
B0, A0 = BEST_BID, BEST_BID + TICK; MID = (B0 + A0) / 2; UP, DN = MID + TICK, MID - TICK
MICRO = P_UP * UP + (1 - P_UP) * DN; WMID = (0.4 * B0 + 4.0 * A0) / 4.4
fig = go.Figure()


def mini(x0, y0, ask, bid, ask_p, bid_p, title, sub, faded_ask=False, faded_bid=False):
    """A two-row ladder: the best ask over the best bid, with sizes; a title above and the mid below."""
    fig.add_annotation(x=x0 + 0.5, y=y0 + 1.55, text=f"<b>{title}</b>", showarrow=False, font=dict(size=12, color=INK))
    for k, (side, q, pr, faded) in enumerate((("ask", ask, ask_p, faded_ask), ("bid", bid, bid_p, faded_bid))):
        y = y0 + (0.75 if side == "ask" else 0); col = ASK if side == "ask" else BID
        fig.add_shape(type="rect", x0=x0, x1=x0 + 1, y0=y + 0.03, y1=y + 0.72, fillcolor="#fbe9f1" if side == "ask" else "#e7f0fb", line=dict(width=0))
        fig.add_annotation(x=x0 + 0.03, y=y + 0.37, text=f"{pr:,.1f}", xanchor="left", showarrow=False, font=dict(size=11, color=INK))
        L = min(q, 4) / 4 * 0.45
        fig.add_shape(type="rect", x0=x0 + 0.42, x1=x0 + 0.42 + L, y0=y + 0.17, y1=y + 0.57, fillcolor=col, line=dict(width=0), opacity=0.35 if faded else 1)
        fig.add_annotation(x=x0 + 0.44 + L, y=y + 0.37, text=f"{q:.1f}", xanchor="left", showarrow=False, font=dict(size=10, color=INK))
    fig.add_annotation(x=x0 + 0.5, y=y0 - 0.3, text=sub, showarrow=False, font=dict(size=11, color=INK))


mini(0, 2.2, 0.4, 4.0, A0, B0, "1. Now: book B", f"mid {MID:,.2f}")
mini(2.0, 3.6, 1.1, 2.5, A0 + TICK, B0 + TICK, f"2a. The thin ask is taken ({P_UP:.0%})", f"mid {UP:,.2f}: up one tick")
mini(2.0, 0.6, 0.9, 1.2, A0 - TICK, B0 - TICK, f"2b. The bid gives way ({1 - P_UP:.0%})", f"mid {DN:,.2f}: down one tick")
for y1 in (4.3, 1.3):
    fig.add_annotation(x=1.95, y=y1, ax=1.05, ay=2.95, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor=MUTED, text="")
# the ruler
RX0, RX1 = 3.6, 6.9; lo, hi = DN - 0.03, UP + 0.03
X = lambda p: RX0 + (p - lo) / (hi - lo) * (RX1 - RX0)
fig.add_annotation(x=(RX0 + RX1) / 2, y=4.9, text="<b>3. The microprice: the mid to expect once the price has moved</b>", showarrow=False, font=dict(size=12, color=INK))
fig.add_shape(type="line", x0=RX0, x1=RX1, y0=2.6, y1=2.6, line=dict(color=MUTED, width=2))
for p in (B0, A0):
    fig.add_shape(type="line", x0=X(p), x1=X(p), y0=2.5, y1=2.7, line=dict(color=BID if p == B0 else ASK, width=3))
    fig.add_annotation(x=X(p), y=2.25, text=("best bid " if p == B0 else "best ask ") + f"{p:,.1f}", showarrow=False, font=dict(size=10, color=BID if p == B0 else ASK))
pts = [(DN, f"2b: {DN:,.2f}<br>weight {1 - P_UP:.0%}", MUTED, 3.15, 10 + 14 * (1 - P_UP)), (UP, f"2a: {UP:,.2f}<br>weight {P_UP:.0%}", MUTED, 3.15, 10 + 14 * P_UP),
       (MID, f"mid now<br>{MID:,.2f}", INK, 3.15, 12), (MICRO, f"<b>microprice {MICRO:,.3f}</b>", SERIES[2], 1.75, 15), (WMID, f"weighted mid {WMID:,.3f}", SERIES[1], 1.35, 11)]
for p, lab, col, ly, size in pts:
    fig.add_scatter(x=[X(p)], y=[2.6], mode="markers", marker=dict(size=size, color=col, line=dict(color="white", width=2)), showlegend=False)
    fig.add_annotation(x=X(p), y=ly, text=lab, showarrow=False, font=dict(size=10, color=col))
fig.add_annotation(x=(RX0 + RX1) / 2, y=0.75,
                   text=f"microprice = {P_UP:.0%} × {UP:,.2f} + {1 - P_UP:.0%} × {DN:,.2f} = <b>{MICRO:,.3f}</b><br>"
                        "<i>the weighted mid uses only the two sizes; the microprice uses how often each branch actually happens</i>",
                   showarrow=False, font=dict(size=11, color=INK))
fig.update_xaxes(visible=False, range=[-0.1, 7.0]); fig.update_yaxes(visible=False, range=[0, 5.3])
fig.update_layout(title="The microprice: not where the price is, but where the mid is expected to be once it has moved<br>"
                        f"<sup>Book B of figure 19_03, sizes in BTC. The probabilities {P_UP:.0%} and {1 - P_UP:.0%} are an illustration: Section 3 measures them on our data. "
                        "One tick = $0.10</sup>", height=560, width=1250, margin=dict(t=100, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L19.PREFIX + "19_04_microprice_card", FIG)

# 19_05: can imbalance be gamed? An honest book; a 10 BTC sell wall added 4 ticks behind the best ask, just placed; the wall cancelled.
# Under each: the plain imbalance of the best 5 levels, one weighted by distance (weight exp(-k / 1.5) at k ticks behind the best), and one
# weighted by distance that also leaves out depth that has rested less than a second (the wall). Invented numbers.
LAM = 1.5
def wimb(b, a, ab=None, aa=None):
    w = [2.718281828 ** (-k / LAM) for k in range(len(b))]
    ab = ab or [1] * len(b); aa = aa or [1] * len(a)
    sb = sum(x * y * z for x, y, z in zip(b, w, ab)); sa = sum(x * y * z for x, y, z in zip(a, w, aa))
    return (sb - sa) / (sb + sa)
bids = [1.0, 0.9, 1.1, 1.0, 1.2]; honest = [0.9, 1.1, 0.8, 1.2, 1.0]; walled = honest[:4] + [11.0]
aged_wall = [1, 1, 1, 1, 1.0 / 11.0]                                           # of the 11 BTC at the fifth ask, only the old 1 BTC has rested a second
frames = [("1. The honest book", honest, None, "nothing hidden"),
          ("2. A 10 BTC sell wall, just placed", walled, aged_wall, "the plain measure flips; distance<br>dampens it, age removes it"),
          ("3. The wall is cancelled", honest, None, "the wall never traded:<br>it was there to be seen")]
fig = go.Figure(); PW, GAP = 1.0, 0.32
for c, (head, a, age, read) in enumerate(frames):
    plain = imb(sum(bids), sum(a)); dist = wimb(bids, a); both = wimb(bids, a, None, age)
    ladder(fig, c * (PW + GAP), a, bids, head, notes=((f"plain, best 5 levels: <b>{plain:+.2f}</b>", 12, INK), (f"weighted by distance: <b>{dist:+.2f}</b>", 12, INK),
                                                       (f"by distance and age: <b>{both:+.2f}</b>", 12, INK), (f"<i>{read}</i>", 11, MUTED)))
    if c == 1:
        fig.add_shape(type="rect", x0=c * (PW + GAP), x1=c * (PW + GAP) + PW, y0=9.02, y1=9.98, line=dict(color=ASK, width=2, dash="dot"), fillcolor="rgba(0,0,0,0)")
        fig.add_annotation(x=c * (PW + GAP) + PW + 0.02, y=9.5, text="10 BTC added<br>0.2 s ago", xanchor="left", showarrow=False, font=dict(size=10, color=ASK))
fig.add_annotation(x=-0.03, y=7.5, text="asks<br>(sell)", xanchor="right", showarrow=False, font=dict(size=11, color=ASK))
fig.add_annotation(x=-0.03, y=2.5, text="bids<br>(buy)", xanchor="right", showarrow=False, font=dict(size=11, color=BID))
fig.update_xaxes(visible=False, range=[-0.2, 3 * PW + 2 * GAP + 0.25]); fig.update_yaxes(visible=False, range=[-4.0, 11.5])
fig.update_layout(title="Can imbalance be gamed? A wall that is never meant to trade flips the plain measure; weighting by distance dampens it, by age removes it<br>"
                        f"<sup>Invented books, the best 5 levels on each side, sizes in BTC (bars full at 4 BTC; ▶ larger). Distance weight: exp(−k / {LAM}) at k ticks behind the best. "
                        "Age: only depth that has rested at least a second counts</sup>",
                  height=700, width=1250, margin=dict(t=100, l=60, r=20, b=20), showlegend=False)
save_figure(fig, L19.PREFIX + "19_05_spoofing_card", FIG)
print("19_05", [(h, round(imb(sum(bids), sum(a)), 2), round(wimb(bids, a), 2), round(wimb(bids, a, None, g), 2)) for h, a, g, _ in frames])

# 19_06: the stale-quote race. Binance has jumped; a market maker's ask at 100,000.1 on Bybit is now too cheap. The same three senders in both rows:
# the sniper's buy (server A, sent first), a flood of junk messages (server B), the market maker's cancel. Top: first come, first served; bottom:
# an asymmetric speed bump delays orders that would trade at once by 3 ms, everything else passes. Boxes nearest the engine are processed first.
fig = go.Figure()
SN, JK, MM = SERIES[1], "#d9d7cf", BID
rows = [("Without a speed bump: first come, first served", [("buy 1 BTC<br>(sniper, A)", SN, "t + 1.0 ms"), ("junk", JK, "+ 1.1"), ("junk", JK, "+ 1.2"), ("junk", JK, "+ 1.3"),
                                                            ("junk", JK, "+ 1.4"), ("cancel ask<br>(market maker)", MM, "+ 2.0")],
         "The buy reaches the ask first:<br><b>the sniper buys at 100,000.1</b>,<br>the market maker sold too cheap"),
        ("With an asymmetric speed bump: orders that would trade wait 3 ms", [("junk", JK, "t + 1.1"), ("junk", JK, "+ 1.2"), ("junk", JK, "+ 1.3"), ("junk", JK, "+ 1.4"),
                                                                              ("cancel ask<br>(market maker)", MM, "+ 2.0"), ("buy 1 BTC<br>(sniper, A)", SN, "+ 1.0 + 3 = 4.0")],
         "The cancel is processed first:<br><b>the stale ask is gone</b>;<br>the buy meets the new ask")]
BW, BG, EX = 0.95, 0.12, 7.6
for r, (head, queue, result) in enumerate(rows):
    y = 2.6 - r * 2.6
    fig.add_annotation(x=0, y=y + 1.05, text=f"<b>{head}</b>", xanchor="left", showarrow=False, font=dict(size=13, color=INK))
    for k, (lab, col, tlab) in enumerate(queue):                                   # k = 0 is nearest the engine
        x1 = EX - 0.25 - k * (BW + BG); x0 = x1 - BW
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y, y1=y + 0.7, fillcolor=col, line=dict(color="white", width=2), opacity=0.9 if col != JK else 1)
        fig.add_annotation(x=(x0 + x1) / 2, y=y + 0.35, text=lab, showarrow=False, font=dict(size=10, color="white" if col != JK else INK))
        fig.add_annotation(x=(x0 + x1) / 2, y=y - 0.2, text=tlab, showarrow=False, font=dict(size=9.5, color=MUTED))
    fig.add_annotation(x=EX - 0.25 - 6 * (BW + BG) + 0.05, y=y + 0.35, text="queue, towards<br>the engine →", showarrow=False, xanchor="right", font=dict(size=10, color=MUTED))
    fig.add_shape(type="rect", x0=EX, x1=EX + 1.3, y0=y - 0.1, y1=y + 0.8, fillcolor="#eef3fb", line=dict(color=INK, width=2))
    fig.add_annotation(x=EX + 0.65, y=y + 0.35, text="<b>matching<br>engine</b>", showarrow=False, font=dict(size=11, color=INK))
    fig.add_annotation(x=EX + 1.45, y=y + 0.35, text=result, xanchor="left", align="left", showarrow=False, font=dict(size=11, color=INK))
    if r == 1:
        fig.add_annotation(x=EX - 0.25 - 5 * (BW + BG) - BW / 2, y=y + 0.88, text="held 3 ms at the gateway", showarrow=False, font=dict(size=10, color=SN))
fig.update_xaxes(visible=False, range=[-0.3, 11.6]); fig.update_yaxes(visible=False, range=[-0.6, 3.9])
fig.update_layout(title="The stale-quote race: the profit lies in quotes whose cancellation is stuck in the queue<br>"
                        "<sup>Schematic. Binance has just jumped; the market maker's ask at 100,000.1 on Bybit is now too cheap. Same messages in both rows, times after the jump; "
                        "the box nearest the matching engine is processed first</sup>", height=520, width=1250, margin=dict(t=100, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L19.PREFIX + "19_06_stale_quote_race", FIG)

# 19_07: the shape of the book. Two invented ask sides with the same depth within 10 ticks of the best: A steep (2 BTC at every tick), B hollow
# near the price. Left: the two ladders; right: cumulative depth by distance from the best ask, and how far a 3 BTC market buy reaches in each.
from plotly.subplots import make_subplots
A_ = [2.0] * 10; B_ = [0.2, 0.2, 0.3, 0.3, 0.5, 1.0, 3.0, 5.0, 4.5, 5.0]
def walk_ticks(levels, size):
    left, cost = size, 0.0
    for k, q in enumerate(levels):
        x = min(left, q); cost += x * (k + 0.5); left -= x                         # distance from the mid in ticks: best ask is half a tick above it
        if left <= 1e-12: return cost / size, k + 1
fig = make_subplots(rows=1, cols=2, column_widths=[0.45, 0.55], horizontal_spacing=0.08,
                    subplot_titles=("Two ask sides, the best 10 levels", "Depth added up from the best ask"))
for c, (head, lv, col) in enumerate((("A. Steep", A_, ASK), ("B. Hollow near the price", B_, "#e3a1bb"))):
    x0 = c * 1.25
    fig.add_annotation(x=x0 + 0.5, y=10.7, text=f"<b>{head}</b>", showarrow=False, font=dict(size=12, color=INK), row=1, col=1)
    for k, q in enumerate(lv):
        y = k; L = min(q, 5) / 5 * 0.55
        fig.add_shape(type="rect", x0=x0, x1=x0 + 1, y0=y + 0.04, y1=y + 0.96, fillcolor="#fbe9f1", line=dict(width=0), row=1, col=1)
        fig.add_annotation(x=x0 + 0.02, y=y + 0.5, text="best ask" if k == 0 else f"+{k} tick" + ("s" if k > 1 else ""), xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
        fig.add_shape(type="rect", x0=x0 + 0.32, x1=x0 + 0.32 + L, y0=y + 0.2, y1=y + 0.8, fillcolor=ASK, line=dict(width=0), row=1, col=1)
        fig.add_annotation(x=x0 + 0.34 + L, y=y + 0.5, text=f"{q:.1f}", xanchor="left", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
fig.update_xaxes(visible=False, range=[-0.05, 2.3], row=1, col=1); fig.update_yaxes(visible=False, range=[-0.3, 11.2], row=1, col=1)
for head, lv, col, dash in (("A. Steep", A_, INK, "solid"), ("B. Hollow near the price", B_, SERIES[1], "solid")):
    cum = [0] + [sum(lv[:k + 1]) for k in range(len(lv))]
    fig.add_scatter(x=list(range(len(cum))), y=cum, mode="lines+markers", line=dict(color=col, width=2, dash=dash), marker=dict(size=7), name=head, row=1, col=2)
    avg, n = walk_ticks(lv, 3.0)
    fig.add_annotation(x=n, y=3, text=f"{head[0]}: 3 BTC reach {n} levels,<br>average {avg:.1f} ticks above the mid", showarrow=True, ax=-150 if head[0] == "A" else 60,
                       ay=-60 if head[0] == "A" else 35, xanchor="left", font=dict(size=10, color=col), row=1, col=2)
fig.add_hline(y=3, line=dict(color=MUTED, dash="dot", width=1), row=1, col=2)
fig.add_annotation(x=10.8, y=3, text="a 3 BTC market buy", yshift=9, xanchor="right", showarrow=False, font=dict(size=10, color=MUTED), row=1, col=2)
fig.update_xaxes(title_text="levels taken from the best ask (1 = the best ask)", dtick=1, range=[-0.3, 10.8], row=1, col=2); fig.update_yaxes(title_text="BTC", rangemode="tozero", row=1, col=2)
fig.update_layout(title="The shape of the book: the same depth in the best 10 levels, very different costs for the same order<br>"
                        "<sup>Two invented ask sides, sizes in BTC (bars full at 5 BTC). Both hold 20 BTC in their best 10 levels; one tick = $0.10</sup>",
                  height=580, width=1250, margin=dict(t=100, l=40, r=30, b=50), legend=dict(orientation="h", y=-0.15, x=0.55))
save_figure(fig, L19.PREFIX + "19_07_shape_card", FIG)
print("19_07", sum(A_), sum(B_), walk_ticks(A_, 3.0), walk_ticks(B_, 3.0))


# 19_08: a queue at the best bid, seen by the exchange and by L2. Rows are successive updates, 100 ms apart. Each bar: the orders in the queue,
# the front (next to be filled) on the left, shaded by how long each has rested; ours outlined. Next to it: what L2 shows, what the trade feed
# shows, and what we infer by replaying the changes through a first-in, first-out queue. At update 3 a 0.7 BTC order ahead of ours is cancelled:
# L2 does not say where, so the estimate of what stands in front of us depends on the assumption. Invented numbers.
AGE_COL = {5.0: "#1d4f91", 3.0: "#3f74bd", 2.0: SERIES[1], 1.0: "#8db3e2", 0.0: "#cfe0f5"}
states = [("0", [("A", 1.0, 5.0), ("B", 0.7, 3.0), ("ours", 0.1, 2.0), ("C", 1.1, 1.0)], "", "", "the queue as it stands", "1.7 ahead"),
          ("1", [("A", 0.4, 5.0), ("B", 0.7, 3.0), ("ours", 0.1, 2.0), ("C", 1.1, 1.0)], "−0.6", "sells of 0.6", "the decrease was traded:<br>taken from the front", "1.1 ahead"),
          ("2", [("A", 0.4, 5.0), ("B", 0.7, 3.0), ("ours", 0.1, 2.0), ("C", 1.1, 1.0), ("D", 0.5, 0.0)], "+0.5", "none", "an addition:<br>joins the back", "1.1 ahead"),
          ("3", [("A", 0.4, 5.0), ("B cancelled", 0.7, None), ("ours", 0.1, 2.0), ("C", 1.1, 1.0), ("D", 0.5, 0.0)], "−0.7", "none", "a cancellation: <b>where?</b>",
           "truth 0.4<br>model, from the back: 1.1<br>model, in proportion: 0.8"),
          ("4", [("A filled", 0.4, None), ("ours filled", 0.1, None), ("C", 1.0, 1.0), ("D", 0.5, 0.0)], "−0.6", "sells of 0.6", "taken from the front", "truth: ours filled<br>both models: not filled")]
SC = 1.4                                                                             # plot units per BTC
fig = go.Figure(); XL2, XTR, XIN, XUS = 5.0, 6.1, 7.25, 9.3
for x, lab in ((0, "the queue at the best bid, as the exchange holds it<br><i>front: filled first →  back</i>"), (XL2, "L2<br>shows"), (XTR, "trades at<br>this price"),
               (XIN, "what we infer"), (XUS, "in front of ours")):
    fig.add_annotation(x=x, y=5.75, text=f"<b>{lab}</b>", xanchor="left", showarrow=False, font=dict(size=11, color=INK))
for r, (n, orders, dl2, tr, inf, us) in enumerate(states):
    y = 4.4 - r * 1.05; x = 0.35; tot = sum(q for _, q, age in orders if age is not None)
    fig.add_annotation(x=0, y=y, text=f"<b>{n}</b>", xanchor="left", showarrow=False, font=dict(size=12, color=MUTED))
    for name, q, age in orders:
        w = q * SC; ours = name == "ours"
        if age is None:                                                          # gone: a dashed outline where the order was
            fig.add_shape(type="rect", x0=x + 0.02, x1=x + w - 0.02, y0=y - 0.3, y1=y + 0.3, fillcolor="rgba(0,0,0,0)", line=dict(color=MUTED, width=1, dash="dot"))
            fig.add_annotation(x=x + w / 2, y=y + (0.45 if w < 0.5 else 0), text=name.replace("ours ", "ours<br>") if w < 0.5 else name, showarrow=False, font=dict(size=9, color=MUTED))
            x += w; continue
        fig.add_shape(type="rect", x0=x + 0.02, x1=x + w - 0.02, y0=y - 0.3, y1=y + 0.3, fillcolor=AGE_COL[age], line=dict(color=INK if ours else "white", width=2 if ours else 1))
        if not ours:
            fig.add_annotation(x=x + w / 2, y=y, text=f"{name} {q:.1f}", showarrow=False, font=dict(size=10, color="white" if age >= 3 else INK))
        else:
            fig.add_annotation(x=x + w / 2, y=y + 0.45, text="ours 0.1" if r < 3 else "ours", showarrow=False, font=dict(size=10, color=SERIES[1]))
        x += w
    fig.add_annotation(x=XL2, y=y, text=f"<b>{tot:.1f}</b>" + (f" ({dl2})" if dl2 else ""), xanchor="left", showarrow=False, font=dict(size=11, color=INK))
    fig.add_annotation(x=XTR, y=y, text=tr or "", xanchor="left", showarrow=False, font=dict(size=11, color=INK))
    fig.add_annotation(x=XIN, y=y, text=inf, xanchor="left", align="left", showarrow=False, font=dict(size=11, color=INK))
    fig.add_annotation(x=XUS, y=y, text=us, xanchor="left", align="left", showarrow=False, font=dict(size=11, color=SERIES[1]))
# age key
for j, (age, lab) in enumerate(((5.0, "rested 5 s"), (3.0, "3 s"), (2.0, "ours, 2 s"), (1.0, "1 s"), (0.0, "just arrived"))):
    fig.add_shape(type="rect", x0=0.35 + j * 1.15, x1=0.6 + j * 1.15, y0=-0.98, y1=-0.78, fillcolor=AGE_COL[age], line=dict(width=0))
    fig.add_annotation(x=0.65 + j * 1.15, y=-0.88, text=lab, xanchor="left", showarrow=False, font=dict(size=10, color=INK))
fig.add_annotation(x=6.3, y=-0.88, text="ages at update 0; updates 100 ms apart; dotted: gone", xanchor="left", showarrow=False, font=dict(size=10, color=MUTED))
fig.update_xaxes(visible=False, range=[-0.1, 11.3]); fig.update_yaxes(visible=False, range=[-1.15, 6.1])
fig.update_layout(title="A queue at the best bid: the exchange holds separate orders in line, L2 shows only their total<br>"
                        "<sup>Invented numbers, BTC. Each row is one update of the book. Additions join the back and trades take from the front; "
                        "where a cancellation came from, L2 does not say, so it has to be assumed</sup>",
                  height=590, width=1250, margin=dict(t=100, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L19.PREFIX + "19_08_queue_card", FIG)
print("19_08 ok")


# 19_09: markouts. A market maker's bid at 100,000.0 is filled (it bought) with the mid at 100,000.05. Two invented paths of the mid after the fill:
# a good fill (the price holds or rises) and a toxic one (the seller knew: the price falls). Left: the paths over the first 10 s; right: the markout,
# mid after h seconds minus the fill price, in ticks, by horizon h. At h = 0 it is the half spread earned; later it is that minus the price impact.
import numpy as np
from plotly.subplots import make_subplots
FILL_P = BEST_BID
good = [(0, 100_000.05), (0.8, 100_000.15), (3, 100_000.05), (20, 100_000.15)]
toxic = [(0, 100_000.05), (0.2, 99_999.95), (1.0, 99_999.85)]
def mid_at(path, t):
    return [m for s_, m in path if s_ <= t][-1]
H = [0, 0.1, 0.3, 1, 3, 10, 30, 60]
fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.1,
                    subplot_titles=("The mid after the fill: two invented paths", "Markout: mid after h seconds minus the fill price"))
for name, path, col in (("good fill", good, SERIES[0]), ("toxic fill", toxic, SERIES[1])):
    tt = np.linspace(0, 10, 1001)
    fig.add_scatter(x=tt, y=[mid_at(path, t) for t in tt], mode="lines", line=dict(color=col, width=2, shape="hv"), name=name, row=1, col=1)
    mk = [(mid_at(path, h) - FILL_P) / TICK for h in H]
    fig.add_scatter(x=[max(h, 0.05) for h in H], y=mk, mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=8), showlegend=False, row=1, col=2)
fig.add_hline(y=FILL_P, line=dict(color=INK, dash="dot", width=1), row=1, col=1)
fig.add_annotation(x=10, y=FILL_P, text="the fill: the maker bought at 100,000.0", yshift=-10, xanchor="right", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
fig.update_xaxes(title_text="seconds after the fill", range=[-0.2, 10], row=1, col=1)
fig.update_yaxes(title_text="mid price", title_standoff=4, tickformat=",.2f", range=[99_999.8, 100_000.2], row=1, col=1)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=2)
fig.add_annotation(x=np.log10(0.05), y=0.5, text="at the fill: +½ tick,<br>the half spread earned", ax=55, ay=-45, xanchor="left", font=dict(size=10, color=INK), row=1, col=2)
fig.add_annotation(x=0, y=-1.5, text="toxic, from 1 s on: +½ tick of spread,<br>−2 ticks of price impact", ax=60, ay=28, xanchor="left", font=dict(size=10, color=INK), row=1, col=2)
fig.add_annotation(x=np.log10(60), y=-2.4, text="Bybit's base maker fee, 2 bp, is about 200 ticks: far off this scale", xanchor="right", showarrow=False, font=dict(size=10, color=MUTED), row=1, col=2)
fig.update_xaxes(title_text="horizon h, seconds (log scale; 0 drawn at 0.05)", type="log", tickvals=[0.05, 0.1, 0.3, 1, 3, 10, 30, 60], ticktext=["0", "0.1", "0.3", "1", "3", "10", "30", "60"], row=1, col=2)
fig.update_yaxes(title_text="markout, ticks of $0.10 (positive: the fill earned)", range=[-2.5, 2], dtick=0.5, row=1, col=2)
fig.update_layout(title="Markouts: what a fill was worth once the price had moved<br>"
                        "<sup>Invented paths. A market maker's bid at 100,000.0 is filled with the mid at 100,000.05; markout = mid after h seconds − fill price, "
                        "for a buy (the sign flips for a sell). One tick = $0.10, about 0.01 bp</sup>",
                  height=560, width=1250, margin=dict(t=100, l=95, r=30, b=60), legend=dict(orientation="h", y=-0.17, x=0.0))
save_figure(fig, L19.PREFIX + "19_09_markout_card", FIG)
print("19_09 ok")
