"""Lecture 21 figures 21_01 and 21_02. 21_01: the chain of Part IV, Lecture 21 outlined. 21_02, the key chart: left, one real moment of Bybit
BTCUSDT (1 October 2025, 09:33:15 UTC): a resting bid of 0.001 BTC at the best, the trades that reach it and when it is filled under the three
fill rules; below, the size ahead of it in the queue; right, over the whole of that day, the same order every 15 s: how often it is filled and
the price after the fill under each rule. From l21_s1_key.py's results (L21_OUT/key, or results/key as shipped)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme()
FIG = L21.FIG; FIG.mkdir(parents=True, exist_ok=True)
RULES = [("q0", "touch", SERIES[1]), ("q2", "queue", SERIES[0]), ("q1", "trade-through", SERIES[2])]
INF_C = "#8fb8ea"                                                                  # the queue rule with every cancellation behind us
DAY_RULES = RULES[:2] + [("q2i", "queue, a = ∞", INF_C)] + RULES[2:]

# 21_01: the chain of Part IV
steps = [("18", "The order book", "what is there"), ("19", "Levels", "the state now"), ("20", "Deltas", "what changed"),
         ("21", "Replay", "our own orders"), ("22", "A market that reacts", "simulated agents"), ("23", "Market making", "one venue"),
         ("24", "Cross-exchange", "quote here, hedge there")]
CUR = 3
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
fig.update_layout(title="Part IV in one line: Lecture 21 puts our own orders into the recorded market<br><sup>Each lecture builds on the one before; "
                        "the current one is outlined, done ones are ticked</sup>", height=270, width=1250, margin=dict(t=80, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L21.PREFIX + "21_01_part_iv", FIG)

# 21_02: the key chart
M = json.loads(L21.result_path(L21.KEY, "moment.json").read_text())
SB = pl.read_parquet(L21.result_path(L21.KEY, "moment_book.parquet")); ST = pl.read_parquet(L21.result_path(L21.KEY, "moment_trades.parquet"))
SQ = pl.read_parquet(L21.result_path(L21.KEY, "moment_queue.parquet")); SI = pl.read_parquet(L21.result_path(L21.KEY, "moment_queue_inf.parquet"))
D = pl.read_parquet(L21.result_path(L21.KEY, "day_orders.parquet"))
t0, p = M["t0"], M["p"]
sec = lambda t: (np.asarray(t) - t0) / 1000
end = float(sec(max(M["fills"].values()))) + 11
print("moment: ahead", M["q"], {k: round(float(sec(v)), 2) for k, v in M["fills"].items()},
      {k: {h: round(x, 2) for h, x in v.items()} for k, v in M["markout"].items()})

fig = make_subplots(rows=2, cols=2, column_widths=[0.64, 0.36], horizontal_spacing=0.1, vertical_spacing=0.12, row_heights=[0.6, 0.4],
                    subplot_titles=("One moment: our bid at the best, and when each rule fills it", "One day: share of the orders filled within 120 s",
                                    "The queue rule: size ahead of our bid, under the two ends of the unknown", "One day: price after the fill, average per fill"))
fig.add_scatter(x=sec(SB["ts"]), y=SB["ask"] * L21.TICK, mode="lines", line=dict(color=MUTED, width=1.5, shape="hv"), name="best ask", row=1, col=1)
fig.add_scatter(x=sec(SB["ts"]), y=SB["bid"] * L21.TICK, mode="lines", line=dict(color=INK, width=1.5, shape="hv"), name="best bid", row=1, col=1)
fig.add_hline(y=p * L21.TICK, line=dict(color=SERIES[0], width=1, dash="dot"), row=1, col=1)
SELL = ST.filter((pl.col("side") == -1) & (pl.col("tick") <= p))
for sel, sym, lab in ((pl.col("tick") == p, "circle-open", "sell trades at our price"), (pl.col("tick") < p, "x-thin-open", "sell trades below our price")):
    X = SELL.filter(sel)
    fig.add_scatter(x=sec(X["ts"]), y=X["tick"] * L21.TICK, mode="markers", marker=dict(symbol=sym, size=8, color=MUTED, line=dict(width=1.2, color=MUTED)),
                    name=lab, row=1, col=1)
ylo, yhi = SB["bid"].min() * L21.TICK - 1, SB["ask"].max() * L21.TICK + 9
for k, lab, c in RULES:
    x = float(sec(M["fills"][k])); m = M["markout"][k]["10"]
    fig.add_scatter(x=[x, x], y=[ylo, yhi], mode="lines", line=dict(color=c, width=2), name=f"filled: {lab}", row=1, col=1)
    fig.add_annotation(x=x, y=yhi, text=f"<b>{lab}{' (a = 1)' if k == 'q2' else ''}</b><br>after {x:.1f} s<br>10 s later: {m:+.1f} bp", showarrow=False, yanchor="top", align="left",
                       xanchor="left", xshift=3, font=dict(size=10, color=INK), row=1, col=1)
fig.add_annotation(x=end - 0.3, y=p * L21.TICK, text="our price", showarrow=False, xanchor="right", yanchor="bottom",
                   font=dict(size=10, color=SERIES[0]), row=1, col=1)
SQ = pl.concat([SQ, SQ.tail(1).with_columns(pl.lit(M["fills"]["q2"]).alias("ts"))])        # held until the fill
SI = pl.concat([SI, SI.tail(1).with_columns(pl.lit(M["q2_inf"]).alias("ts"))])
for x, c, dash in ((float(sec(M["fills"]["q2"])), SERIES[0], "solid"), (float(sec(M["q2_inf"])), INF_C, "dash")):
    fig.add_scatter(x=[x, x], y=[0, 11], mode="lines", line=dict(color=c, width=2, dash=dash), showlegend=False, row=2, col=1)
i = int(np.searchsorted(SB["ts"].to_numpy(), M["q2_inf"] + 10_000, "right")) - 1
m_inf = ((SB["bid"][i] + SB["ask"][i]) / 2 - p) / p * 1e4
fig.add_annotation(x=float(sec(M["q2_inf"])), y=4.5, text=f"<b>queue, a = ∞</b><br>after {float(sec(M['q2_inf'])):.1f} s<br>10 s later: {m_inf:+.1f} bp",
                   showarrow=False, xanchor="left", align="left", xshift=3, font=dict(size=10, color=INK), row=2, col=1)
fig.add_annotation(x=float(sec(M["fills"]["q2"])), y=9.5, text="<b>queue, a = 1</b><br>(the line above)", showarrow=False, align="left", xanchor="left", xshift=3,
                   font=dict(size=10, color=INK), row=2, col=1)
fig.add_scatter(x=sec(SQ["ts"]), y=SQ["level"], mode="lines", line=dict(color=MUTED, width=1.5, shape="hv"), name="displayed size at our price",
                row=2, col=1)
fig.add_scatter(x=sec(SQ["ts"]), y=SQ["ahead"], mode="lines", line=dict(color=SERIES[0], width=2, shape="hv"), name="size ahead of us: cancellations split evenly (a = 1)",
                row=2, col=1)
fig.add_scatter(x=sec(SI["ts"]), y=SI["ahead"], mode="lines", line=dict(color=INF_C, width=2, dash="dash", shape="hv"),
                name="size ahead of us: cancellations behind us (a = ∞)", row=2, col=1)
for r in (1, 2): fig.update_xaxes(range=[-2, end], matches="x", row=r, col=1)
fig.update_xaxes(title_text="seconds after 09:33:15 UTC", row=2, col=1)
fig.update_yaxes(title_text="$", title_standoff=4, tickformat=",.0f", range=[ylo, yhi], row=1, col=1)
fig.update_yaxes(title_text="BTC", range=[0, 11.5], row=2, col=1)

n = D.height
fr = [D[k].is_not_null().mean() for k, _, _ in DAY_RULES]
fig.add_bar(x=[l for _, l, _ in DAY_RULES], y=fr, marker_color=[c for *_, c in DAY_RULES], showlegend=False, text=[f"{v:.0%}" for v in fr],
            textposition="outside", textfont=dict(size=10, color=INK), row=1, col=2)
fig.update_yaxes(tickformat=".0%", range=[0, 1.12], row=1, col=2)
for k, lab, c in DAY_RULES:
    v = [D[f"{k}_m{h}"].mean() for h in (1, 10)]
    fig.add_bar(x=["1 s after", "10 s after"], y=v, marker_color=c, showlegend=False, text=[f"{x:+.2f}" for x in v], textposition="outside",
                textfont=dict(size=9, color=INK), row=2, col=2)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=2, col=2)
fig.update_yaxes(title_text="bp: mid minus our price", range=[-0.95, 0.15], row=2, col=2)
fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08,
                  title="A naive replay hands us the good fills: filled on touch, our bid gets the trades that come before the price falls;<br>"
                        "waiting its turn in the queue, it is filled later and worse, often only when the price runs through it"
                        "<br><sup>Bybit BTCUSDT, a resting bid of 0.001 BTC at the best, active 50 ms after the decision, held up to 120 s. Left: 1 October 2025, "
                        f"09:33:15 UTC, {M['q']:.1f} BTC displayed ahead of it. Right: the same order every 15 s of 1 October, {n:,} orders</sup>",
                  height=740, width=1300, margin=dict(t=140, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.13, x=0))
save_figure(fig, L21.PREFIX + "21_02_three_replays", FIG)
print("day:", n, "filled", [round(x, 3) for x in fr], {k: [round(D[f"{k}_m{h}"].mean(), 3) for h in (1, 10)] for k, _, _ in DAY_RULES}, "moment a = inf", round(float(sec(M["q2_inf"])), 2), round(m_inf, 2))
