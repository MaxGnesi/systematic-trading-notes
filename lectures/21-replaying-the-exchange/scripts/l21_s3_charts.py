"""Lecture 21 §3 figures. 21_10 (§3.1): left, the share of the size sold at the best bid that must have been refilled within the same book update, with
the trades shifted against the book, on five days (clock_shift.parquet); right, the same share at no shift, both sides, every day of the 45
(net_days.parquet). From L21_OUT/s31, or results/s31 as shipped.
21_11 (§3.2): what our taker orders meet after the latency gap, from L21_OUT/s32 (size.parquet, ret.parquet of l21_s32_sum.py) or results/s32:
left, the share of market orders that paid more than the book seen at the decision promised, by size, one line per latency; middle, the share
of a limit order at the best price seen left resting, by size and latency; right, the share of minimum-size IOC orders filled short at 50 ms,
by the move of the mid over the next second.
21_12 (§3.3): resting orders in the queue, from L21_OUT/s33_sum (l21_s33_sum.py) or results/s33_sum: left, the share filled by time since joining,
by fill rule; middle, the share filled within 120 s by the size ahead at joining; right, every sampled half-hour, median size ahead against
median time to fill under Q2 (a = 1), 10 October marked."""
import sys
from datetime import date
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme()
S31 = L21.OUT / "s31"
C = pl.read_parquet(L21.result_path(S31, "clock_shift.parquet"))
N = (pl.read_parquet(L21.result_path(S31, "net_days.parquet")).group_by("day").agg(pl.col("traded", "hidden").sum())
     .with_columns((pl.col("hidden") / pl.col("traded")).alias("share")).sort("day"))
wk = [date.fromisoformat(d).weekday() >= 5 for d in N["day"]]
fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], horizontal_spacing=0.09,
                    subplot_titles=("Do the two clocks agree? Five days", "What the book hides, day by day"))
for i, (day, g) in enumerate(C.sort("shift_ms").group_by("day", maintain_order=True)):
    fig.add_scatter(x=g["shift_ms"], y=g["hidden_share"], mode="lines+markers", line=dict(color=SERIES[i % len(SERIES)], width=1.8), marker=dict(size=5),
                    name=day[0], row=1, col=1)
fig.add_vline(x=0, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=1)
fig.update_xaxes(title_text="trades shifted against the book, ms", tickvals=[-100, -50, -20, 0, 20, 50, 100], row=1, col=1)
fig.update_yaxes(title_text="share of traded size refilled unseen", tickformat=".0%", range=[0, 0.9], row=1, col=1)
col = [SERIES[1] if d == "2025-10-10" else (GRID if w else SERIES[0]) for d, w in zip(N["day"], wk)]
fig.add_bar(x=N["day"], y=N["share"], marker=dict(color=col, line=dict(width=0)), showlegend=False, row=1, col=2)
fig.add_hline(y=float(N["share"].median()), line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
fig.add_annotation(x=N["day"][-1], y=float(N["share"].median()), text=f"median {N['share'].median():.0%}", showarrow=False, xanchor="right",
                   yanchor="bottom", font=dict(size=10, color=INK), row=1, col=2)
fig.update_yaxes(tickformat=".0%", range=[0, 0.32], row=1, col=2)
fig.update_xaxes(title_text="day (weekends light, 10 October orange)", row=1, col=2)
fig.update_layout(title="The trades and the book share one clock to the millisecond; even so, a 100 ms book hides about a fifth of the flow at the best"
                        "<br><sup>Bybit BTCUSDT. Share of the size traded at an unchanged best price that must have been refilled within the same update "
                        "(more traded than the queue fell), both sides; left: sells at the best bid with the trades shifted, five days</sup>",
                  height=470, width=1250, margin=dict(t=100, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, L21.PREFIX + "21_10_hidden_flow", L21.FIG)
print("median", round(float(N["share"].median()), 3), "min", round(float(N["share"].min()), 3), "max", round(float(N["share"].max()), 3))

S32 = L21.OUT / "s32"
Z = pl.read_parquet(L21.result_path(S32, "size.parquet")).sort("S"); M = pl.read_parquet(L21.result_path(S32, "ret.parquet"))
fig = make_subplots(rows=1, cols=3, column_widths=[0.33, 0.33, 0.34], horizontal_spacing=0.07,
                    subplot_titles=("Market orders: paid more than seen", "Limit orders: share left resting", "IOC, 0.001 BTC, 50 ms: filled short"))
sizes = [0.001, 0.01, 0.1, 1, 5]
for i, L in enumerate((10, 50, 100)):
    g = Z.filter(pl.col("L") == L); c = SERIES[i]
    for col, y, lo, hi in ((1, "worse", "worse_lo", "worse_hi"), (2, "left", None, None)):
        if lo:
            fig.add_scatter(x=np.r_[g["S"], g["S"][::-1]], y=np.r_[g[hi], g[lo][::-1]], fill="toself", fillcolor=c, opacity=0.15, line=dict(width=0),
                            hoverinfo="skip", showlegend=False, row=1, col=col)
        fig.add_scatter(x=g["S"], y=g[y], mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=7), name=f"L = {L} ms",
                        legendgroup=str(L), showlegend=col == 1, row=1, col=col)
for col in (1, 2):
    fig.update_xaxes(type="log", tickvals=sizes, ticktext=["0.001", "0.01", "0.1", "1", "5"], title_text="order size, BTC", row=1, col=col)
fig.update_yaxes(tickformat=".0%", range=[0, 0.32], row=1, col=1); fig.update_yaxes(tickformat=".0%", range=[0, 0.5], row=1, col=2)
order = ["< -2", "-2 to -0.5", "about 0", "0.5 to 2", "2 to 5", "> 5"]
R = M.filter(pl.col("by") == "move").with_columns(pl.col("cls").replace_strict({k: i for i, k in enumerate(order)}).alias("o")).sort("o")
fig.add_bar(x=R["cls"], y=R["short"], marker=dict(color=[MUTED if k.startswith(("<", "-")) else SERIES[1] for k in R["cls"]], line=dict(width=0)),
            error_y=dict(type="data", symmetric=False, array=R["hi"] - R["short"], arrayminus=R["short"] - R["lo"], color=INK, thickness=1, width=3),
            showlegend=False, row=1, col=3)
for k, n, h in zip(R["cls"], R["n"], R["hi"]):
    fig.add_annotation(x=k, y=h, text=f"{n:,}", showarrow=False, yanchor="bottom", yshift=2, font=dict(size=9, color=MUTED), row=1, col=3)
fig.update_xaxes(title_text="1-s move of the mid, bp (+: order's favour)", row=1, col=3)
fig.update_yaxes(tickformat=".0%", range=[0, 0.42], row=1, col=3)
fig.update_layout(title="The latency gap grows with order size and delay, and the IOC orders it leaves short are the ones that would have paid"
                        "<br><sup>Bybit BTCUSDT, 45 days, a decision every 10 s, buys and sells; the book at t + L is the last update before it less the "
                        "trades since; bands and whiskers: 95% from resampling days; numbers above bars: decisions</sup>",
                  height=480, width=1300, margin=dict(t=100, l=70, r=30, b=70), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L21.PREFIX + "21_11_latency_data", L21.FIG)

S33 = L21.OUT / "s33_sum"
CV = pl.read_parquet(L21.result_path(S33, "curve.parquet")); AH = pl.read_parquet(L21.result_path(S33, "ahead.parquet"))
HH = pl.read_parquet(L21.result_path(S33, "halfhours.parquet"))
RS = [("Q0", "touch (Q0)", MUTED, "dot"), ("Q2 a=1", "queue, a = 1", SERIES[0], "solid"), ("Q2 a=inf", "queue, a = ∞", SERIES[2], "solid"),
      ("Q1", "trade-through (Q1)", INK, "dash")]
fig = make_subplots(rows=1, cols=3, column_widths=[0.34, 0.30, 0.36], horizontal_spacing=0.08,
                    subplot_titles=("Share filled, by time since joining", "Filled within 120 s, by size ahead", "Every sampled half-hour"))
for r, nm, c, dash in RS:
    g = CV.filter((pl.col("rule") == r) & (pl.col("sec") >= 1))
    fig.add_scatter(x=np.r_[g["sec"], g["sec"][::-1]], y=np.r_[g["hi"], g["lo"][::-1]], fill="toself", fillcolor=c, opacity=0.15, line=dict(width=0),
                    hoverinfo="skip", showlegend=False, row=1, col=1)
    fig.add_scatter(x=g["sec"], y=g["share"], mode="lines", line=dict(color=c, width=2, dash=dash), name=nm, legendgroup=r, row=1, col=1)
fig.update_xaxes(type="log", tickvals=[1, 2, 5, 10, 20, 60, 120], title_text="seconds since joining", row=1, col=1)
fig.update_yaxes(tickformat=".0%", range=[0, 1], row=1, col=1)
cls = ["< 0.01", "0.01-0.1", "0.1-1", "1-5", "> 5"]
for r, nm, c, dash in RS:
    g = AH.filter(pl.col("rule") == r).with_columns(pl.col("cls").replace_strict({k: i for i, k in enumerate(cls)}).alias("o")).sort("o")
    fig.add_scatter(x=g["cls"], y=g["filled"], mode="lines+markers", line=dict(color=c, width=2, dash=dash), marker=dict(size=7), legendgroup=r,
                    showlegend=False, row=1, col=2)
fig.update_xaxes(title_text="size ahead at joining, BTC", row=1, col=2); fig.update_yaxes(tickformat=".0%", range=[0.7, 1], row=1, col=2)
o = HH.filter(pl.col("day") != "2025-10-10"); t = HH.filter(pl.col("day") == "2025-10-10")
fig.add_scatter(x=o["ahead"], y=o["wait"], mode="markers", marker=dict(size=6, color=GRID, line=dict(width=0.5, color=MUTED)), name="other days",
                row=1, col=3)
fig.add_scatter(x=t["ahead"], y=t["wait"], mode="markers+text", marker=dict(size=9, color=SERIES[1], line=dict(width=1, color="white")),
                text=[f"{h // 2:02d}:{30 * (h % 2):02d}" for h in t["hh"]], textposition="middle right", textfont=dict(size=9, color=INK),
                name="10 October (UTC)", row=1, col=3)
fig.update_xaxes(type="log", tickvals=[0.1, 0.3, 1, 3, 10], title_text="median size ahead at joining, BTC", row=1, col=3)
fig.update_yaxes(type="log", tickvals=[0.1, 0.3, 1, 3, 10, 30], title_text="median time to fill, s", row=1, col=3)
fig.update_layout(title="Our order joins behind a few BTC; most queue fills come as the price runs through; in the cascade the line shrank to a tenth"
                        "<br><sup>Bybit BTCUSDT, 45 days, eight random half-hours a day, bids and asks: an order of 0.001 BTC every 15 s at the best, "
                        "joining after 50 ms, held up to 120 s; bands: 95% from resampling days</sup>",
                  height=480, width=1300, margin=dict(t=100, l=70, r=30, b=70), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L21.PREFIX + "21_12_queue_data", L21.FIG)
