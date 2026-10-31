"""Lecture 20, Section 4 figures. 20_14: the afternoon and evening of 10 October, mid and net taker flow added up on Bybit and Binance, with the two posts,
the registered windows and T0. 20_15: H8 and H9, the value of 10 October's window against every reference window. 20_16: the early-warning table
on a time line. Each figure is drawn from L20_OUT/s4 if computed, otherwise from the results shipped in results/s4."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
S4 = L20.S4
FIG = L20.FIG
BY_C, BN_C, CASC_C = "#2a78d6", "#eb6834", "#c0436f"
ms = lambda s: int(np.datetime64(f"2025-10-10T{s}", "ms").astype(np.int64))
POST, MORN, T0 = ms("20:50:01.702"), ms("14:57:52.308"), ms("21:14:00")
dt = lambda x: np.asarray(x.to_numpy() if hasattr(x, "to_numpy") else x, dtype=np.int64).astype("datetime64[ms]")
LEG = dict(orientation="h", y=-0.14, x=0)

# ---- 20_14: the evening ----
a, b = ms("14:00:00"), ms("22:00:00")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.45, 0.55], vertical_spacing=0.06,
                    subplot_titles=("Bybit mid, $", "Net taker flow added up from 14:00 UTC, BTC (taker buys − taker sells)"))
if (L20.BOOK10 / "2025-10-10.parquet").exists() and (L20.ORD / "binance_2025-10-10.parquet").exists():     # per-minute extract, shipped in results/s4
    B = pl.read_parquet(L20.BOOK10 / "2025-10-10.parquet", columns=["sec", "mid2"]).filter((pl.col("sec") * 1000 >= a) & (pl.col("sec") * 1000 < b))
    B = B.group_by((pl.col("sec") // 60 * 60000).alias("t")).agg(pl.col("mid2").last()).sort("t")
    for v in ("bybit", "binance"):
        O = pl.read_parquet(L20.ORD / f"{v}_2025-10-10.parquet", columns=["ts", "side", "size"]).filter((pl.col("ts") >= a) & (pl.col("ts") < b))
        B = B.join(O.group_by((pl.col("ts") // 60000 * 60000).alias("t")).agg((pl.col("side") * pl.col("size")).sum().alias(f"ti_{v}")), on="t", how="full", coalesce=True)
    B.sort("t").write_parquet(S4 / "evening.parquet")
B = pl.read_parquet(L20.result_path(S4, "evening.parquet")).sort("t")
b_mid = B.drop_nulls("mid2")
fig.add_scatter(x=dt(b_mid["t"]), y=b_mid["mid2"] / 20, mode="lines", line=dict(color=INK, width=1.5), showlegend=False, row=1, col=1)
for v, c, nm in (("bybit", BY_C, "Bybit"), ("binance", BN_C, "Binance")):
    m = B.drop_nulls(f"ti_{v}").select("t", pl.col(f"ti_{v}").cum_sum().alias("ti"))
    fig.add_scatter(x=dt(m["t"]), y=m["ti"], mode="lines", line=dict(color=c, width=2), name=nm, row=2, col=1)
for x0, x1, lab, col in ((POST - 7_200_000, POST - 3_600_000, "H9: two hours before", "#eef3fb"), (POST - 3_600_000, POST, "H8: the hour before", "#dfe9f7")):
    for r in (1, 2): fig.add_vrect(x0=dt(x0), x1=dt(x1), fillcolor=col, line_width=0, layer="below", row=r, col=1)
fig.add_annotation(x=dt(POST - 7_200_000), y=1.0, yref="y domain", text="H9: the two hours before →", xanchor="left", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=1)
fig.add_annotation(x=dt(POST - 3_600_000), y=0.9, yref="y domain", text="H8: the hour before →", xanchor="left", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=1)
for x, lab in ((MORN, "14:57:52 first post"), (POST, "20:50:01.7 tariff post"), (T0, "21:14 T0")):
    for r in (1, 2): fig.add_vline(x=dt(x), line=dict(color=CASC_C, width=1, dash="dot"), row=r, col=1)
    fig.add_annotation(x=dt(x), y=0.02, yref="y domain", text=lab, textangle=-90, xanchor="right", yanchor="bottom", showarrow=False, font=dict(size=10, color=CASC_C), row=1, col=1)
fig.update_layout(title="10 October: the selling came in the afternoon and from 18:50 to 19:50 UTC; the hour before the post was quiet, with net buying<br>"
                  "<sup>Bybit and Binance BTCUSDT perpetuals, 14:00–22:00 UTC, per minute. Shaded: the windows of H8 (dark) and H9 (both) fixed before the results</sup>",
                  height=640, width=1250, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_14_evening", FIG)

# ---- 20_15: H8 and H9 against the reference windows ----
R = json.loads(L20.result_path(S4, "stats.json").read_text())
W1 = pl.read_parquet(L20.result_path(S4, "windows_1h.parquet")); W2 = pl.read_parquet(L20.result_path(S4, "windows_2h.parquet"))
ref = lambda W: W.filter(~pl.col("on_casc") & (pl.col("resets") == 0))
PAN = [(W1, "ti_bybit", "H8a: net taker flow, Bybit, BTC", "the hour before", False), (W1, "ti_binance", "H8b: net taker flow, Binance, BTC", "the hour before", False),
       (W2, "vpin", "H9a: VPIN", "two hours before", True), (W2, "hawkes_n", "H9b: branching ratio", "two hours before", True),
       (W2, "kyle_lambda", "H9c: Kyle's lambda, ticks per BTC", "two hours before", True), (W1, "big_sells_binance", "Reported: sells of $1M or more, Binance", "the hour before", True)]
fig = make_subplots(rows=2, cols=3, vertical_spacing=0.2, horizontal_spacing=0.07, subplot_titles=[p[2] for p in PAN])
for i, (W, c, lab, win, higher) in enumerate(PAN):
    r, cc = i // 3 + 1, i % 3 + 1; v = ref(W)[c].drop_nulls().to_numpy(); x = W.filter(pl.col("pre"))[c][0]
    rank = float((v < x).mean())
    fig.add_histogram(x=v, nbinsx=40, marker_color=GRID, showlegend=False, row=r, col=cc)
    fig.add_vline(x=x, line=dict(color=CASC_C, width=2.5), row=r, col=cc)
    fig.add_annotation(x=x, y=0.95, yref=f"y{'' if i == 0 else i + 1} domain", text=f"10 Oct: {(f'{x:+,.0f}' if c.startswith('ti') else (f'{x:,.0f}' if abs(x) >= 20 else f'{x:.3f}' if x < 1 else f'{x:.1f}'))}<br>above {rank:.1%} of windows", xanchor="left", xshift=5,
                       showarrow=False, font=dict(size=10.5, color=CASC_C), align="left", row=r, col=cc)
fig.update_layout(title="Before the post, 10 October looked unusual in the wrong direction: net buying, and trades that moved the price less than usual<br>"
                  f"<sup>Grey: every window of the same length on the other 44 days, aligned to the same clock phase ({R['1h']['n_ref']:,} of one hour, "
                  f"{R['2h']['n_ref']} of two hours). Red: the window before the post on 10 October</sup>",
                  height=640, width=1300, margin=dict(t=110, l=60, r=20, b=50))
save_figure(fig, L20.PREFIX + "20_15_before_post", FIG)
print("done")

# ---- 20_16: the early-warning table on a time line ----
A = pl.read_parquet(L20.result_path(S4, "minutes_casc.parquet")).filter((pl.col("t") >= ms("13:00:00")) & (pl.col("t") < ms("22:00:00")))
Wn = json.loads(L20.result_path(S4, "warn.json").read_text())
NAMES = [("depth", "Depth, best 10 levels (low)"), ("spread", "Spread"), ("chains", "Refill chains"), ("delay", "Publish delay"),
         ("ofi", "Order-flow imbalance, |size|"), ("ti", "Trade imbalance, |size|"), ("vpin", "VPIN"), ("hawkes", "Branching ratio, 15 min"),
         ("kyle", "Kyle's lambda, 15 min"), ("kyle_hasb", "Kyle's lambda, Hasbrouck (follow-up)"), ("kyle_sqrt", "Kyle's lambda, √ net flow (follow-up)"), ("pulls", "Pull rate"), ("sync", "Synchronised pulls")]
fig = make_subplots(rows=1, cols=1)
for i, (c, lab) in enumerate(NAMES):
    thr = Wn["thresholds"][c]; low = c == "depth"
    bey = A.filter((pl.col(c) < thr) if low else (pl.col(c) > thr))
    y = len(NAMES) - i
    fig.add_scatter(x=dt(bey["t"] + 30_000), y=[y] * bey.height, mode="markers", marker=dict(symbol="line-ns-open", size=12, color="#9fb8d9", line=dict(width=2)),
                    showlegend=i == 0, name="minute beyond its threshold")
    fl = [x for x in Wn["ind"][c]["pre_times"]]
    post_first = Wn["ind"][c]["first_post_min"]
    if post_first is not None: fl = fl + [POST + post_first * 60000]
    fig.add_scatter(x=dt(fl), y=[y] * len(fl), mode="markers", marker=dict(symbol="diamond", size=11, color=CASC_C), showlegend=i == 0,
                    name="flag: 5 minutes in a row (first after the post also shown)")
for x, lab in ((MORN, "first post"), (POST, "tariff post"), (T0, "T0")):
    fig.add_vline(x=dt(x), line=dict(color=CASC_C, width=1, dash="dot"))
    fig.add_annotation(x=dt(x), y=len(NAMES) + 0.8, text=lab, showarrow=False, font=dict(size=10.5, color=CASC_C))
fig.update_yaxes(tickvals=list(range(len(NAMES), 0, -1)), ticktext=[n for _, n in NAMES], range=[0.4, len(NAMES) + 1.2], showgrid=False)
fig.update_xaxes(title_text="10 October 2025, UTC")
fig.update_layout(title="Early warning on 10 October: the measures of the book's activity flagged after the first post and in the selling hour, not just before the tariff post<br>"
                  "<sup>Bybit BTCUSDT, per minute. Thresholds: the 99th percentile of the 20 calm days' minutes (1st for depth); a flag needs 5 minutes in a row beyond it</sup>",
                  height=620, width=1300, margin=dict(t=110, l=250, r=20, b=60), legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, L20.PREFIX + "20_16_early_warning", FIG)
print("done 16")
