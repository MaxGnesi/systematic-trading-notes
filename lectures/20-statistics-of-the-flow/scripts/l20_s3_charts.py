"""Lecture 20, Section 3 figures from the results of l20_s3_stats.py and its inputs.
20_08 order-flow imbalance (H1, H2), 20_09 impact over time (H3), 20_10 VPIN (H4), 20_11 Hawkes (H5), 20_12 lead and lag (H6),
20_13 the Lecture 19 puzzle and Simpson's paradox (H7 and the post-hoc check)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
S3 = L20.S3
FIG = L20.FIG
OFI_C, TI_C, OFI10_C = "#2a78d6", "#eb6834", "#174a8b"
INS_C, OOS_C, CASC_C = "#2a78d6", "#2e9e6a", "#eb6834"
R = json.loads(L20.result_path(S3, "stats.json").read_text())
DAYS = sorted(R["D10"]["ofi"]["r2_by_day"]); CASC = "2025-10-10"
day_c = lambda d: CASC_C if d == CASC else (INS_C if d < CASC else OOS_C)
LEG = dict(orientation="h", y=-0.2, x=0)

# ---- 20_08: order-flow imbalance ----
fig = make_subplots(rows=1, cols=3, column_widths=[0.27, 0.43, 0.30], horizontal_spacing=0.07,
                    subplot_titles=("Out of sample: share of the mid's move explained", "Day by day, 10-second intervals",
                                    "Move per BTC of pressure, by depth"))
lab = ["1 s", "10 s", "60 s"]
for key, name, c in (("ti", "trade imbalance: trades only", TI_C), ("ofi", "order-flow imbalance at the best", OFI_C),
                     ("ofi10", "order-flow imbalance, best 10 levels", OFI10_C)):
    v = [R[f"D{D}"][key]["r2_oos"] for D in (1, 10, 60)]
    fig.add_bar(x=lab, y=v, marker_color=c, name=name, text=[f"{x:.0%}" for x in v], textposition="outside", textfont=dict(size=10, color=INK), row=1, col=1)
fig.update_yaxes(title_text="R², out of sample", tickformat=".0%", range=[0, 0.5], row=1, col=1)
fig.update_xaxes(title_text="length of the interval", row=1, col=1)
for key, c, nm in (("ofi", OFI_C, "order-flow imbalance"), ("ti", TI_C, "trade imbalance")):
    v = R["D10"][key]["r2_by_day"]
    fig.add_scatter(x=DAYS, y=[v[d] for d in DAYS], mode="lines+markers", line=dict(color=c, width=1.5), marker=dict(size=7),
                    showlegend=False, name=nm, row=1, col=2)
fig.add_vrect(x0="2025-10-09 12:00", x1="2025-10-10 12:00", fillcolor="#fde8dc", line_width=0, layer="below", row=1, col=2)
fig.add_annotation(x=CASC, y=0.72, text="10 Oct", showarrow=False, font=dict(size=10.5, color=INK), row=1, col=2)
fig.add_annotation(x="2025-09-29", y=0.72, text="in sample (fitted)", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=2)
fig.add_annotation(x="2025-10-23", y=0.72, text="out of sample", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=2)
fig.update_yaxes(title_text="R² of the day", tickformat=".0%", range=[0, 0.76], row=1, col=2)
W = pl.read_parquet(L20.result_path(S3, "halfhours.parquet"))
fig.add_scatter(x=W["depth"], y=W["b"], mode="markers", marker=dict(size=4, color=OFI_C, opacity=0.35), showlegend=False, row=1, col=3)
xs = np.geomspace(W["depth"].quantile(0.01), W["depth"].quantile(0.99), 50)
sl, ic = np.polyfit(np.log(W["depth"]), np.log(W["b"]), 1)
fig.add_scatter(x=xs, y=np.exp(ic) * xs ** sl, mode="lines", line=dict(color=INK, width=2), name=f"fit: slope {sl:.2f}", row=1, col=3)
xm = float(np.exp(np.log(W["depth"]).mean())); ym = float(np.exp(ic) * xm ** sl)
fig.add_scatter(x=xs, y=ym * (xs / xm) ** -1, mode="lines", line=dict(color=MUTED, width=1.5, dash="dot"), name="1 / depth (slope −1)", row=1, col=3)
fig.update_xaxes(type="log", title_text="average size at the best, BTC (log)", row=1, col=3)
fig.update_yaxes(type="log", title_text="ticks per BTC of order-flow imbalance (log)", row=1, col=3)
fig.update_layout(barmode="group", bargap=0.25, title="The pressure on the book explains about twice as much of the price's move as the trades alone, except on 10 October<br>"
                  "<sup>Bybit BTCUSDT, 45 days. Fits on 20 Sep–9 Oct, scored on 11 Oct–3 Nov. Right: one dot per half hour, 10-second intervals</sup>",
                  height=520, width=1300, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_08_ofi_results", FIG)

# ---- 20_09: impact over time ----
P = json.loads(L20.result_path(S3, "prop.json").read_text())
C = np.array([P[d]["C"][1:] for d in DAYS]); Rr = np.array([P[d]["R"] for d in DAYS]); G = np.array([P[d]["G"] for d in DAYS])
L = np.arange(1, 1001); keep = L <= 900                                     # G near lag 1000 is an edge artefact of the fit
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                    subplot_titles=("Do buys follow buys? Correlation of signs", "A trade's own impact, and the move a maker sees"))
for arr, c, nm, col in ((C, MUTED, "sign correlation", 1), (Rr, TI_C, "response: the mid's move after an order, in its direction", 2),
                        (G, OFI_C, "bare impact: the order's own share", 2)):
    q25, q50, q75 = np.quantile(arr[:, keep], [0.25, 0.5, 0.75], axis=0)
    fig.add_scatter(x=np.r_[L[keep], L[keep][::-1]], y=np.r_[q75, q25[::-1]], fill="toself", fillcolor=c, opacity=0.18, line=dict(width=0),
                    showlegend=False, hoverinfo="skip", row=1, col=col)
    fig.add_scatter(x=L[keep], y=q50, mode="lines", line=dict(color=c, width=2.5), name=nm, showlegend=col == 2, row=1, col=col)
fig.update_xaxes(type="log", title_text="orders later (log)", row=1, col=1); fig.update_yaxes(type="log", title_text="correlation (log)", row=1, col=1)
fig.update_xaxes(type="log", title_text="orders later (log)", row=1, col=2); fig.update_yaxes(title_text="ticks", row=1, col=2)
pk = int(np.median(np.argmax(G[:, :200], axis=1)) + 1)
fig.add_vline(x=pk, line=dict(color=GRID, width=1, dash="dot"), row=1, col=2)
fig.add_annotation(x=np.log10(pk), y=float(np.median(G[:, pk - 1])), text=f"peak of the bare impact:<br>median {pk} orders later", showarrow=True, ax=60, ay=-40,
                   font=dict(size=10.5, color=INK), row=1, col=2)
fig.update_layout(title="A trade's own impact builds for about a dozen orders and then fades; the orders that follow on the same side keep the price moving<br>"
                  "<sup>Bybit BTCUSDT, 45 days, taker orders. Lines: median over days; bands: middle half of the days. Bare impact from the propagator model (Section 2.2)</sup>",
                  height=500, width=1250, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_09_impact_results", FIG)

# ---- 20_10: VPIN ----
V = pl.read_parquet(L20.result_path(S3, "vpin_hours.parquet")).drop_nulls(["vpin", "vpin_bvc", "rv_next", "rv_last", "vol_last"])
VO = V.filter(pl.col("day") >= "2025-10-11"); H4 = R["H4"]
fig = make_subplots(rows=1, cols=3, column_widths=[0.34, 0.33, 0.33], horizontal_spacing=0.08,
                    subplot_titles=("Rank correlation with the next hour's volatility", "Recorded sides: VPIN and next hour",
                                    "Estimated sides: VPIN and last hour"))
cats = ["plain", "after volume and<br>last hour's volatility"]
fig.add_bar(x=cats, y=[H4["plain_true"], H4["partial_true"]], marker_color=OFI_C, name="VPIN, sides as recorded by Bybit",
            text=[f"{H4['plain_true']:+.2f}", f"{H4['partial_true']:+.3f}".replace("-", "−")], textposition="outside", row=1, col=1)
fig.add_bar(x=cats, y=[H4["plain_bvc"], H4["partial_bvc"]], marker_color=MUTED, name="VPIN, sides estimated from price moves (original)",
            text=[f"{H4['plain_bvc']:+.2f}", f"{H4['partial_bvc']:+.2f}"], textposition="outside", row=1, col=1)
fig.update_yaxes(range=[-0.1, 0.5], title_text="Spearman correlation, out of sample", row=1, col=1)
rk = lambda s: s.rank().to_numpy() / len(s)
fig.add_scatter(x=rk(VO["vpin"]), y=rk(VO["rv_next"]), mode="markers", marker=dict(size=5, color=OFI_C, opacity=0.5), showlegend=False, row=1, col=2)
fig.add_scatter(x=rk(VO["vpin_bvc"]), y=rk(VO["rv_last"]), mode="markers", marker=dict(size=5, color=MUTED, opacity=0.6), showlegend=False, row=1, col=3)
fig.update_xaxes(title_text="rank of VPIN (recorded sides)", tickformat=".0%", row=1, col=2)
fig.update_yaxes(title_text="rank of next hour's volatility", tickformat=".0%", row=1, col=2)
fig.update_xaxes(title_text="rank of VPIN (estimated sides)", tickformat=".0%", row=1, col=3)
fig.update_yaxes(title_text="rank of last hour's volatility", tickformat=".0%", row=1, col=3)
fig.update_layout(barmode="group", title="VPIN with the true sides adds nothing to the next hour's volatility; with estimated sides it largely echoes the last hour's moves<br>"
                  f"<sup>Bybit BTCUSDT, out of sample (11 Oct–3 Nov), {VO.height} hours. Right panels: one dot per hour, ranks</sup>",
                  height=500, width=1300, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_10_vpin_results", FIG)

# ---- 20_11: Hawkes ----
Hk = pl.read_parquet(L20.result_path(S3, "hawkes_hours.parquet"))
fig = make_subplots(rows=1, cols=3, column_widths=[0.36, 0.36, 0.28], horizontal_spacing=0.08,
                    subplot_titles=("Share of orders triggered by earlier orders, per hour", "By hour of the day (UTC), median",
                                    "Which reaction times carry it"))
for nm, flt, c in (("in sample", pl.col("day") < CASC, INS_C), ("out of sample", pl.col("day") > CASC, OOS_C)):
    fig.add_histogram(x=Hk.filter(flt)["n"], xbins=dict(start=0.4, end=1.06, size=0.02), marker_color=c, opacity=0.6, name=nm, row=1, col=1)
    m = Hk.filter(flt).group_by("hour").agg(pl.col("n").median()).sort("hour")
    fig.add_scatter(x=m["hour"], y=m["n"], mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=6), showlegend=False, row=1, col=2)
cs = Hk.filter(pl.col("day") == CASC).sort("hour")
fig.add_scatter(x=cs["hour"], y=cs["n"], mode="lines+markers", line=dict(color=CASC_C, width=2), marker=dict(size=6), name="10 October", row=1, col=2)
for x, t in ((0.9, "0.9"), (1.0, "1: never settles")):
    fig.add_vline(x=x, line=dict(color=INK, width=1, dash="dot"), row=1, col=1)
fig.add_annotation(x=1.0, y=1, yref="y domain", text="1", showarrow=False, yshift=8, font=dict(size=10, color=INK), row=1, col=1)
fig.add_annotation(x=0.9, y=1, yref="y domain", text="0.9", showarrow=False, yshift=8, font=dict(size=10, color=INK), row=1, col=1)
fig.update_layout(barmode="overlay")
fig.update_xaxes(title_text="branching ratio n", row=1, col=1); fig.update_yaxes(title_text="hours", row=1, col=1)
fig.update_xaxes(title_text="hour (UTC)", dtick=3, row=1, col=2); fig.update_yaxes(title_text="branching ratio n", row=1, col=2)
dec = ["0.001", "0.01", "0.1", "1", "10", "100"]; labd = ["1 ms", "10 ms", "100 ms", "1 s", "10 s", "100 s"]
wts = [float(Hk[f"a_{d}"].mean()) for d in dec]
fig.add_bar(x=labd, y=wts, marker_color=OFI_C, text=[f"{w:.2f}" for w in wts], textposition="outside", showlegend=False, row=1, col=3)
fig.update_xaxes(title_text="decay time of the kernel's part", row=1, col=3); fig.update_yaxes(title_text="average weight (they add up to n)", row=1, col=3)
fig.update_layout(title=f"About 84% of taker orders are triggered by earlier ones, but the market stays below the point where it would never settle<br>"
                  f"<sup>Bybit BTCUSDT, 45 days, {Hk.height:,} hours, a Hawkes process fitted to the times of taker orders hour by hour (Section 2.4)</sup>",
                  height=500, width=1300, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_11_hawkes_results", FIG)

# ---- 20_12: lead and lag ----
LL = pl.read_parquet(L20.result_path(S3, "leadlag.parquet"))
m = LL.group_by("lag").agg(pl.col("rho_last").mean(), pl.col("rho_mid").mean()).sort("lag")
H6 = R["H6"]
fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.08,
                    subplot_titles=("Correlation of Binance's price changes with Bybit's, by lag", "Lag of the peak, day by day"))
fig.add_scatter(x=m["lag"], y=m["rho_last"], mode="lines", line=dict(color=TI_C, width=2), name="Bybit last trade (registered test)", row=1, col=1)
fig.add_scatter(x=m["lag"], y=m["rho_mid"], mode="lines", line=dict(color=OFI_C, width=2), name="Bybit mid (reported)", row=1, col=1)
fig.add_vline(x=0, line=dict(color=GRID, width=1), row=1, col=1)
fig.add_annotation(x=520, y=0.5, text="Binance moves first →", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=1)
fig.add_annotation(x=-520, y=0.5, text="← Bybit moves first", showarrow=False, font=dict(size=10.5, color=MUTED), row=1, col=1)
fig.update_xaxes(title_text="lag in ms", row=1, col=1); fig.update_yaxes(title_text="Hayashi-Yoshida correlation, mean over 45 days", row=1, col=1)
pk = H6["peaks"]; pkm = H6["peaks_mid"]
fig.add_scatter(x=DAYS, y=[pk[d] for d in DAYS], mode="markers", marker=dict(size=8, color=TI_C), showlegend=False, row=1, col=2)
fig.add_scatter(x=DAYS, y=[pkm[d] for d in DAYS], mode="markers", marker=dict(size=8, color=OFI_C, symbol="diamond"), showlegend=False, row=1, col=2)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=1, col=2)
fig.update_yaxes(title_text="lag of the peak, ms (positive: Binance first)", row=1, col=2)
fig.update_layout(title="Binance moves first by about 40 to 50 ms, but over a whole second the balance tips the other way on last trades<br>"
                  f"<sup>Bybit and Binance BTCUSDT perpetuals, 45 days, lags −1 s to +1 s in 1 ms steps. Lead-lag ratio over ±1 s: last trade {H6['llr_oos']:.2f}, "
                  f"mid {H6['llr_mid_oos']:.2f} (out of sample)</sup>",
                  height=500, width=1300, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_12_leadlag_results", FIG)

# ---- 20_13: the Lecture 19 puzzle ----
S = json.loads(L20.result_path(S3, "simpson.json").read_text()); Z = json.loads(L20.result_path(S3, "puzzle.json").read_text())
ID = sorted(S["days"])
fig = make_subplots(rows=1, cols=3, column_widths=[0.36, 0.36, 0.28], horizontal_spacing=0.08,
                    subplot_titles=("The registered test: removing Binance's bounce", "Post-hoc: split by Bybit's last move",
                                    "Post-hoc: by time since that move"))
fig.add_scatter(x=ID, y=[Z[d]["rho_last"] for d in ID], mode="markers", marker=dict(size=8, color=TI_C), name="Binance last trade", row=1, col=1)
fig.add_scatter(x=ID, y=[Z[d]["rho_mid"] for d in ID], mode="markers", marker=dict(size=8, color=OFI_C, symbol="diamond"),
                name="midpoint of Binance's last buy and sell", row=1, col=1)
for k, c, nm, sym in (("all", MUTED, "all samples", "circle"), ("within_up", OOS_C, "after an up move", "triangle-up"),
                      ("within_down", "#c0436f", "after a down move", "triangle-down")):
    fig.add_scatter(x=ID, y=[S["days"][d][k] for d in ID], mode="markers", marker=dict(size=8, color=c, symbol=sym), name=nm, row=1, col=2)
bins = [("age_0_200", "< 0.2 s"), ("age_200_1000", "0.2–1 s"), ("age_1000_5000", "1–5 s"), ("age_5000_1000000000000", "> 5 s")]
med = [S["median"][k] for k, _ in bins]
fig.add_bar(x=[b for _, b in bins], y=med, marker_color=MUTED, text=[f"{v:+.2f}" for v in med], textposition="outside", showlegend=False, row=1, col=3)
for c in (1, 2, 3): fig.add_hline(y=0, line=dict(color=INK, width=1), row=1, col=c)
fig.update_yaxes(title_text="rank correlation of Bybit's imbalance with the gap", row=1, col=1)
fig.update_xaxes(title_text="time since Bybit's mid last moved", row=1, col=3); fig.update_yaxes(title_text="median over 20 days", row=1, col=3)
fig.update_layout(title="The Lecture 19 puzzle is a Simpson's paradox: within up moves and within down moves the sign is as expected, pooled it flips<br>"
                  "<sup>Bybit BTCUSDT and Binance, the 20 calm days (20 Sep–9 Oct), samples of Lecture 19. Gap = Binance price − Bybit mid</sup>",
                  height=500, width=1300, margin=dict(t=110, l=70, r=20, b=60), legend=LEG)
save_figure(fig, L20.PREFIX + "20_13_puzzle_results", FIG)
print("done")
