"""Lecture 14 §2-§3 charts: same candle, different paths; two regimes; the variance ratio."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
R = {}

# ---------------------------------------------------------------- 1. same candle, different paths
m1 = (pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "open", "high", "low", "close").collect().sort("time")
        .with_columns(pl.col("time").dt.truncate("1h").alias("bar"), pl.col("close").log().diff().abs().alias("a")))
h = (m1.group_by("bar").agg(pl.col("open").first().alias("O"), pl.col("high").max().alias("H"), pl.col("low").min().alias("L"), pl.col("close").last().alias("C"),
                            pl.col("a").sum().alias("path"), pl.len().alias("n")).filter(pl.col("n") == 60)
       .with_columns(((pl.col("H") / pl.col("O") - 1) * 1e4).alias("h"), ((pl.col("L") / pl.col("O") - 1) * 1e4).alias("l"), ((pl.col("C") / pl.col("O") - 1) * 1e4).alias("c"),
                     (pl.col("path") / (pl.col("H") / pl.col("L")).log()).alias("ratio")))
h = h.filter(pl.col("h").is_between(40, 60) & pl.col("l").is_between(-60, -40))          # hours with a range of about 1%, open in the middle
v = h.select("h", "l", "c", "ratio").to_numpy(); hours = h["bar"].to_list()
best = None
for i in range(len(v)):                                                    # a pair with nearly the same candle and the most different paths
    dist = np.abs(v[:, 0] - v[i, 0]) + np.abs(v[:, 1] - v[i, 1]) + np.abs(v[:, 2] - v[i, 2])
    ok = dist < 6
    if ok.sum() > 1:
        j = np.argmax(np.where(ok, v[:, 3].astype(float), -1))
        gap = float(v[j, 3]) - float(v[i, 3])
        if best is None or gap > best[0]: best = (gap, i, j)
_, i, j = best; pair = [hours[i], hours[j]]
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                    subplot_titles=[f"{p:%d %b %Y, %H:%M} UTC: the path travels {float(v[k, 3]):.1f} times its range" for p, k in zip(pair, (i, j))])
for col, (p, k) in enumerate(zip(pair, (i, j)), start=1):
    q = m1.filter(pl.col("bar") == p); o = q["open"][0]
    fig.add_scatter(x=list(range(60)), y=((q["close"] / o - 1) * 1e4).to_list(), mode="lines", line=dict(color=SERIES[0], width=1.6), showlegend=False, row=1, col=col)
    for lvl in (float(v[k, 0]), float(v[k, 1]), 0.0, float(v[k, 2])):
        fig.add_hline(y=lvl, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=col)
R["same_candle"] = [dict(hour=str(p), high_bp=round(float(v[k, 0])), low_bp=round(float(v[k, 1])), close_bp=round(float(v[k, 2])), path_over_range=round(float(v[k, 3]), 1)) for p, k in zip(pair, (i, j))]
fig.update_xaxes(title_text="minute of the hour"); fig.update_yaxes(title_text="price, bp from the open", row=1, col=1)
fig.update_layout(title="Same candle, different paths<br><sup>Two hours of BTCUSDT with almost the same open, high, low and close (dotted lines); "
                        "one-minute closes. The candle records neither the order nor the distance travelled</sup>", height=430, width=1100, margin=dict(t=100))
save_figure(fig, PREFIX + "14_01_same_candle_different_paths", FIG)

# ---------------------------------------------------------------- 2. two regimes: continuation against shuffled, by step size
reg = json.loads((L14_RESULTS / "l14_regimes.json").read_text())["same day"]
SE = {"calmest half": (0.34, 0.81, 1.64), "50-80%": (0.29, 0.65, 1.24), "80-90%": (0.40, 0.88, 1.65), "most volatile 10%": (0.30, 0.62, 1.12), "most volatile 2%": (0.52, 1.03, 1.81)}
COL = {"calmest half": SERIES[0], "50-80%": SERIES[1], "80-90%": SERIES[2], "most volatile 10%": SERIES[3], "most volatile 2%": INK}
LAB = {"calmest half": "calmest half of days", "50-80%": "days 50-80%", "80-90%": "days 80-90%", "most volatile 10%": "most volatile 10%", "most volatile 2%": "most volatile 2%"}
fig = make_subplots(rows=1, cols=1)
for gi, (k, row) in enumerate(reg.items()):
    y = [row[f"step_{bp}bp_pts"] for bp in (20, 50, 100)]
    fig.add_scatter(x=[pos + (gi - 2) * 0.06 for pos in (0, 1, 2)], y=y, mode="lines+markers", error_y=dict(type="data", array=[1.96 * s for s in SE[k]], thickness=1, width=3),
                    line=dict(color=COL[k], width=2), marker=dict(size=8), name=LAB[k])
fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
fig.add_annotation(x=-0.35, y=0, text="a path without memory", showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11, color=MUTED))
fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["20 bp", "50 bp", "100 bp"], range=[-0.4, 2.4], title_text="step size")
fig.update_yaxes(title_text="continuation, points above the shuffled path")
fig.update_layout(title="Two regimes: the price turns back on ordinary days and runs on explosive ones<br><sup>Share of steps that continue in the same direction, tape minus its own one-minute returns "
                        "shuffled within the same days; days grouped by their realised variance; ± 95% interval</sup>",
                  height=470, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "14_02_two_regimes", FIG)

# ---------------------------------------------------------------- 3. the variance ratio
vr = json.loads((L14_RESULTS / "l14_path_tests.json").read_text())["variance_ratio"]
labs = list(vr); xs = [5, 30, 60, 240, 1440, 10080]
fig = make_subplots(rows=1, cols=1)
years = sorted({y for v_ in vr.values() for y in v_["by_year"]})
for y in years:
    fig.add_scatter(x=xs, y=[vr[l]["by_year"].get(y) for l in labs], mode="lines", line=dict(color=MUTED, width=0.8), name=f"one line per year", showlegend=(y == years[0]), legendgroup="y")
fig.add_scatter(x=xs + xs[::-1], y=[vr[l]["ci90"][1] for l in labs] + [vr[l]["ci90"][0] for l in labs][::-1], fill="toself", fillcolor="rgba(46,111,203,0.15)",
                mode="lines", line=dict(width=0), name="90% interval", hoverinfo="skip")
fig.add_scatter(x=xs, y=[vr[l]["ratio"] for l in labs], mode="lines+markers", line=dict(color=SERIES[0], width=2.5), marker=dict(size=8), name="five years")
fig.add_hline(y=1, line=dict(color=INK, width=1, dash="dot"))
fig.add_annotation(x=np.log10(5), y=1, text="√t holds", showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11, color=INK))
fig.update_xaxes(type="log", tickvals=xs, ticktext=["5 min", "30 min", "1 hour", "4 hours", "1 day", "1 week"], title_text="horizon")
fig.update_yaxes(title_text="variance at the horizon ÷ one-minute variance", range=[0.6, 1.3])
fig.update_layout(title="√t overstates risk from minutes to a day<br><sup>Realised variance from returns over each horizon divided by realised variance from one-minute returns, "
                        "same weeks, five years of BTCUSDT; below 1 the price turns back at that horizon</sup>",
                  height=460, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "14_03_variance_ratio", FIG)
(L14_RESULTS / "l14_s23_charts.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps(R, indent=1, default=str))
