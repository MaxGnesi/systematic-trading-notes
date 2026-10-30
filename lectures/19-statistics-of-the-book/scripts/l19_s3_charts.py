"""Lecture 19 §3 figures from l19_s3_stats.json and l19_s3_stats2.json (and the spoof candidates, L19_OUT/s3/b2_cand_*, and the mid changes).
19_10 imbalance on the 45 days; 19_11 gaming-resistant versions and spoof candidates; 19_12 microprice; 19_13 shape and queues; 19_14 markouts."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); sys.stdout.reconfigure(encoding="utf-8")
D = L19.S3
FIG = L19.FIG
R1 = json.loads((L19.result_path("l19_s3_stats.json")).read_text()); R2 = json.loads((L19.result_path("l19_s3_stats2.json")).read_text())
DAYS = R1["days"]; CASC = "2025-10-10"
C_IN, C_OOS, C_CASC = SERIES[0], SERIES[2], SERIES[1]
SUB = "Bybit BTCUSDT, 20 September – 3 November 2025. In sample: 20 Sep – 9 Oct; out of sample: 11 Oct – 3 Nov"

# 19_10: imbalance
fig = make_subplots(rows=2, cols=2, vertical_spacing=0.2, horizontal_spacing=0.1,
                    subplot_titles=("Share of next mid moves up, by the imbalance at the best", "Forecast quality (AUC) day by day",
                                    "AUC by the size of the smaller best queue", "AUC by how far ahead the move came"))
b0, b1 = R1["H1_coef"]; xs = np.linspace(-1, 1, 101)
for k, lab, col in (("in", "in sample", C_IN), ("oos", "out of sample", C_OOS), ("casc", "10 October", C_CASC)):
    P = R1["pup"][k]; fig.add_scatter(x=P["I"], y=P["p"], mode="markers", marker=dict(size=7, color=col), name=lab, row=1, col=1)
fig.add_scatter(x=xs, y=1 / (1 + np.exp(-(b0 + b1 * xs))), mode="lines", line=dict(color=INK, width=1.5, dash="dot"), name=f"logistic fit in sample, slope {b1:.1f}", row=1, col=1)
fig.update_xaxes(title_text="imbalance at the best", range=[-1.05, 1.05], row=1, col=1); fig.update_yaxes(title_text="share up", tickformat=".0%", range=[0, 1], row=1, col=1)
dl = R1["daily"]; x = [r["day"] for r in dl]; y = [r["auc"] for r in dl]
fig.add_shape(type="rect", xref="x2", yref="y2", x0=x[0], x1=x[-1], y0=0.75, y1=0.81, fillcolor=GRID, opacity=0.6, line=dict(width=0))
fig.add_annotation(x=x[-1], y=0.78, xref="x2", yref="y2", text="Gould and Bonart's large-tick stocks", xanchor="right", showarrow=False, font=dict(size=10, color=MUTED))
fig.add_scatter(x=x, y=y, mode="lines+markers", line=dict(color=INK, width=1.5), marker=dict(size=6, color=[C_CASC if d == CASC else (C_IN if d < CASC else C_OOS) for d in x]), showlegend=False, row=1, col=2)
fig.add_annotation(x=CASC, y=dict(zip(x, y))[CASC], text="10 October", ax=40, ay=30, font=dict(size=10, color=INK), row=1, col=2)
fig.update_yaxes(title_text="AUC (0.5 = coin flip)", range=[0.7, 1.0], row=1, col=2)
q = R1["H5_auc"]; labs = ["below 0.1 BTC", "0.1 – 1 BTC", "above 1 BTC"]
fig.add_bar(x=labs, y=[v["oos"] for v in q.values()], marker_color=C_OOS, text=[f"{v['oos']:.2f}<br>{v['share_oos']:.0%} of cases" for v in q.values()], textposition="outside", showlegend=False, row=2, col=1)
fig.update_yaxes(title_text="AUC out of sample", range=[0.5, 1.08], row=2, col=1); fig.update_xaxes(title_text="smaller of the two best queues", row=2, col=1)
a = R2["auc_by_ahead"]; la = ["1", "2", "3 – 5", "6 – 19", "20 or more"]
fig.add_bar(x=la, y=[v["auc_oos"] for v in a], marker_color=C_OOS, text=[f"{v['auc_oos']:.2f}<br>{v['share']:.0%}" for v in a], textposition="outside", showlegend=False, row=2, col=2)
fig.update_yaxes(title_text="AUC out of sample", range=[0.5, 1.08], row=2, col=2); fig.update_xaxes(title_text="book updates (100 ms each) until the mid moved", type="category", row=2, col=2)
fig.update_layout(title=f"Book imbalance on 45 days: a strong forecast of the next move, strongest when a queue is nearly empty and the move is imminent<br><sup>{SUB}. "
                        f"{sum(R1['n_samples'].values()) / 1e6:.1f} million samples, one per interval between mid changes, spread one tick</sup>",
                  height=820, width=1250, margin=dict(t=110, l=70, r=30, b=60), legend=dict(orientation="v", y=0.99, x=0.01, yanchor="top", bgcolor="rgba(0,0,0,0)", font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_10_imbalance_results", FIG)

# 19_11: gaming-resistant versions and spoof candidates
fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.1,
                    subplot_titles=("Out-of-sample AUC of each version, across its settings", "What a large new order does to the imbalance, by distance"))
lab = {"distance": ("distance weight, λ (ticks)", ["0.5", "1", "1.5", "3", "5"]), "age": ("age filter, τ (s)", ["0.25", "0.5", "1", "2", "5"]),
       "smoothed": ("smoothing half-life (s)", ["0.2", "0.5", "1", "2", "5"])}
for (f, (nm, ticks)), col in zip(lab.items(), (SERIES[0], SERIES[1], SERIES[2])):
    g = R2["H6"][f]["grid"]
    fig.add_scatter(x=list(range(5)), y=[o["auc_oos"] for o in g], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=8), name=nm, text=ticks,
                    hovertemplate="%{text}: %{y:.3f}", row=1, col=1)
fig.add_hline(y=R2["auc_I5"]["oos"], line=dict(color=INK, dash="dot", width=1), row=1, col=1)
fig.add_hline(y=0.5, line=dict(color=MUTED, width=1), row=1, col=1)
fig.add_annotation(x=4, y=R2["auc_I5"]["oos"], text=f"plain, best 5 levels: {R2['auc_I5']['oos']:.2f}", yshift=10, xanchor="right", showarrow=False, font=dict(size=10, color=INK), row=1, col=1)
fig.add_annotation(x=4, y=0.5, text="coin flip", yshift=-9, xanchor="right", showarrow=False, font=dict(size=10, color=MUTED), row=1, col=1)
fig.update_xaxes(tickvals=list(range(5)), ticktext=["1st", "2nd", "3rd", "4th", "5th"], title_text="setting, from the mildest to the strongest (values in the legend)", row=1, col=1)
fig.update_yaxes(title_text="AUC", range=[0.2, 1.0], row=1, col=1)
CO = json.loads(L19.result_path("l19_cand_offsets.json").read_text())
C = pl.DataFrame([(int(o), *v) for d in DAYS for o, v in CO.get(d, {}).items()], schema=["off", "plain", "dist", "n"], orient="row")
O = C.group_by("off").agg(pl.col("plain", "dist", "n").sum()).with_columns(pl.col("plain") / pl.col("n"), pl.col("dist") / pl.col("n")).sort("off")
fig.add_bar(x=O["off"], y=O["plain"], name="plain imbalance, best 5 levels", marker_color=MUTED, row=1, col=2)
fig.add_bar(x=O["off"], y=O["dist"], name="weighted by distance, λ = 1.5", marker_color=SERIES[0], row=1, col=2)
fig.update_xaxes(title_text="ticks behind the best price", dtick=1, row=1, col=2); fig.update_yaxes(title_text="average change of the imbalance", range=[0, 0.75], row=1, col=2)
fig.update_layout(title="Making imbalance hard to game: distance weighting keeps the forecast but does not damp walls; smoothing costs power; the age filter inverts it<br>"
                        f"<sup>{SUB}. Left: the plain line (dotted) lies under the distance line.<br>Right: spoof candidates, orders of at least 5 BTC added 1–9 ticks behind the best and removed within 2 s without a trade "
                        f"({int(C['n'].sum()):,} on the 45 days); with the age filter (1 s) a new order changes nothing, by construction</sup>",
                  height=600, width=1250, margin=dict(t=140, l=70, r=30, b=60), barmode="group", legend=dict(orientation="h", y=-0.2, x=0.0, font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_11_gaming_results", FIG)
print("19_11 candidates by offset", O.to_dicts())

# 19_12: microprice
fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.1,
                    subplot_titles=("Expected change of the mid, by the imbalance at the best (in sample)", "Error of the forecast, out of sample"))
mids = (np.arange(20) + 0.5) / 10 - 1
for t, lab, col in (("d_next", "until the next change", SERIES[0]), ("d_1s", "over 1 s", SERIES[2]), ("d_10s", "over 10 s", SERIES[1])):
    fig.add_scatter(x=mids, y=R1["H8_g"][t], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=6), name=lab, row=1, col=1)
fig.add_scatter(x=mids, y=mids / 2, mode="lines", line=dict(color=INK, width=1, dash="dot"), name="weighted mid (at most ½ tick)", row=1, col=1)
fig.update_xaxes(title_text="imbalance at the best", row=1, col=1); fig.update_yaxes(title_text="ticks of $0.10", row=1, col=1)
for j, (t, lab) in enumerate((("d_next", "next change"), ("d_1s", "1 s"), ("d_10s", "10 s"))):
    m = R1["H8_mse"][t]["oos"]; ci = R1["H8_mse"][t]["gain_vs_mid_ci"]; g = 1 - m[2] / m[0]
    fig.add_bar(x=[lab], y=[g], marker_color=C_OOS, error_y=dict(type="data", symmetric=False, array=[ci[1] - g], arrayminus=[g - ci[0]]), text=[f"{g:.0%}"], textposition="inside", insidetextanchor="start", textfont=dict(color="white"),
                showlegend=False, row=1, col=2)
fig.update_yaxes(title_text="reduction of the squared error, against the mid", tickformat=".0%", range=[0, 0.25], row=1, col=2); fig.update_xaxes(title_text="horizon", row=1, col=2)
fig.update_layout(title="The microprice on 45 days: an imbalanced book predicts a move of tens of ticks, not half a tick<br>"
                        f"<sup>{SUB}. Microprice = mid + the expected change given the imbalance (20 bands), estimated in sample; spread one tick.<br>Error bars: 95% interval, bootstrap over days</sup>",
                  height=580, width=1250, margin=dict(t=130, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.2, x=0.0, font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_12_microprice_results", FIG)

# 19_13: shape and queues
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08, column_widths=[0.34, 0.38, 0.28],
                    subplot_titles=("Depth near the price and the next 5 minutes", "How the best queues shrink, day by day", "Refilling levels a day"))
dec = R2["H9_deciles"]
fig.add_scatter(x=[r["depth"] for r in dec], y=[r["next5"] / 10 for r in dec], mode="lines+markers", line=dict(color=INK, width=2), name="next 5 minutes", row=1, col=1)
fig.add_scatter(x=[r["depth"] for r in dec], y=[r["prev5"] / 10 for r in dec], mode="lines+markers", line=dict(color=MUTED, width=1.5, dash="dot"), name="previous 5 minutes", row=1, col=1)
fig.update_xaxes(title_text="depth in the best 10 levels, both sides (BTC, deciles)", type="log", tickvals=[3, 5, 10, 20], row=1, col=1); fig.update_yaxes(title_text="average absolute move of the mid ($)", row=1, col=1)
q = R2["H10_daily"]; ds = list(q)
tot = [q[d]["traded"] + q[d]["cancelled"] for d in ds]
fig.add_bar(x=ds, y=[q[d]["cancelled"] / t for d, t in zip(ds, tot)], name="cancelled", marker_color=SERIES[1], row=1, col=2)
fig.add_bar(x=ds, y=[q[d]["traded"] / t for d, t in zip(ds, tot)], name="traded", marker_color=SERIES[0], row=1, col=2)
fig.update_yaxes(title_text="share of the decreases at the best", tickformat=".0%", row=1, col=2)
ic = R2["icebergs"]
fig.add_bar(x=list(ic), y=[v["chains3"] for v in ic.values()], marker_color=INK, showlegend=False, row=1, col=3)
fig.update_yaxes(title_text="levels refilled 3+ times in a row (log scale)", type="log", tickvals=[1, 10, 100, 1000, 10000], row=1, col=3)
fig.add_annotation(x=CASC, y=np.log10(ic[CASC]["chains3"]), text=f"10 October: {ic[CASC]['chains3']:,}", ax=45, ay=10, xanchor="left", font=dict(size=10, color=INK), row=1, col=3)
fig.update_layout(title="Shape and queues on 45 days: thin books come before larger moves; the best queues shrink mostly by cancellation<br>"
                        f"<sup>{SUB}. Left: minutes sorted into deciles of depth.<br>Middle: each decrease of a best queue, the part matched by trades at that price counted as traded, the rest as cancelled. "
                        "Right: a level traded away and refilled at the same price by a similar size within 1 s, at least 3 times in a row</sup>",
                  height=600, width=1250, margin=dict(t=140, l=70, r=30, b=60), barmode="stack", legend=dict(orientation="h", y=-0.22, x=0.0, font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_13_shape_queue_results", FIG)

# 19_14: markouts
HL = ["0", "0.1", "1", "10", "60"]; BK = (("0", "taker orders below 0.01 BTC", SERIES[0]), ("0.01", "0.01 – 0.1 BTC", SERIES[2]), ("0.1", "0.1 – 1 BTC", SERIES[4]), ("1", "1 BTC and more", SERIES[1]))
fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.1,
                    subplot_titles=("Markout of the resting order after h seconds, out of sample", "Price impact over 10 s, by the size of the taker order"))
for k, lab, col in BK:
    fig.add_scatter(x=HL, y=R1["markout"]["oos"][k], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=8), name=lab, row=1, col=1)
fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=1)
fig.update_xaxes(type="category", title_text="seconds after the fill", row=1, col=1); fig.update_yaxes(title_text="ticks of $0.10 per BTC", row=1, col=1)
blab = ["below 0.01", "0.01 – 0.1", "0.1 – 1", "1 and more"]
for key, lab, col in (("oos", "out of sample", C_OOS), ("casc", "10 October", C_CASC)):
    v = [R1["markout"][key][k][0] - R1["markout"][key][k][3] for k, _, _ in BK]
    fig.add_bar(x=blab, y=v, name=lab, marker_color=col, text=[f"{x:.0f}" for x in v], textposition="outside", row=1, col=2)
fig.update_xaxes(title_text="taker order (BTC)", row=1, col=2); fig.update_yaxes(title_text="markout at 0 s − markout at 10 s, ticks per BTC", range=[0, 430], row=1, col=2)
fig.update_layout(title="Markouts on 45 days: the resting side earns at the fill and gives it back within a second; the larger the trade, the larger the move against it<br>"
                        f"<sup>{SUB}. Markout = mid after h seconds − fill price, for the resting order, size-weighted; at 0 s it is the spread earned.<br>"
                        "For scale: half the spread is ½ tick; Bybit's base maker fee is about 200 ticks</sup>",
                  height=580, width=1250, margin=dict(t=130, l=70, r=30, b=60), barmode="group", legend=dict(orientation="h", y=-0.2, x=0.0, font=dict(size=10)))
save_figure(fig, L19.PREFIX + "19_14_markout_results", FIG)
print("ok")
