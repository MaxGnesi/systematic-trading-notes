"""Lecture 14 §4 charts: crossings against the random-walk count, excursions against the random walk, stop fills by time window."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
from scipy.stats import norm
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
CALM, WILD = SERIES[0], SERIES[3]
R = {}

# ---------------------------------------------------------------- 1. crossings
cr = json.loads((L14_RESULTS / "l14_s4.json").read_text())["crossings"]
fig = make_subplots(rows=1, cols=1)
for lab, col, key in (("calm half of days", CALM, "calm half"), ("most volatile 10%", WILD, "most volatile 10%")):
    fig.add_bar(x=["20 bp", "50 bp", "100 bp"], y=[cr[b][key]["ratio"] for b in ("20", "50", "100")], name=lab, marker=dict(color=col, line=dict(width=0)),
                text=[f"{cr[b][key]['ratio']:.2f}" for b in ("20", "50", "100")], textposition="outside")
fig.add_hline(y=1, line=dict(color=INK, dash="dot"))
fig.add_annotation(x=-0.45, y=1, xref="x", text="random walk: variance ÷ step²", showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11, color=INK))
fig.update_yaxes(title_text="steps per day ÷ random-walk count", range=[0, 1.15]); fig.update_xaxes(title_text="grid spacing")
fig.update_layout(title="A grid crosses its levels far less often than the day's variance promises<br><sup>Steps of each size per day, counted on one-minute prices, divided by the "
                        "day's realised variance over the step squared; five years of BTCUSDT</sup>", barmode="group", bargap=0.35, height=440, width=1100, margin=dict(t=100),
                  legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "14_04_crossings", FIG)

# ---------------------------------------------------------------- 2. excursions: share of positions whose worst move exceeds k sigma sqrt(T)
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
       .with_columns(pl.col("close").forward_fill()))
nd = n // 1440; lp = np.log(g["close"].to_numpy())[: nd * 1440]; X = lp.reshape(nd, 1440)
rv = (np.diff(X, axis=1) ** 2).sum(1); calm, wild = rv <= np.percentile(rv, 50), rv >= np.percentile(rv, 90)
sig1 = pl.Series(rv / 1440).shift(1).rolling_mean(28, min_samples=7).to_numpy()
H = 240; starts = np.arange(1440 * 28, len(lp) - H, 60); day = starts // 1440; s = np.sqrt(sig1[day] * H); ok = np.isfinite(s)
starts, day, s = starts[ok], day[ok], s[ok]
W = lp[starts[:, None] + np.arange(H + 1)] - lp[starts][:, None]
adv = np.r_[-W.min(1), W.max(1)] / np.r_[s, s]; reg = np.r_[day, day]
k = np.linspace(0, 5, 101)
fig = make_subplots(rows=1, cols=1)
fig.add_scatter(x=k, y=2 * norm.sf(k), mode="lines", line=dict(color=INK, width=2, dash="dot"), name="random walk")
for lab, col, sel in (("all days", MUTED, np.ones(len(reg), bool)), ("calm half of days", CALM, calm[reg]), ("most volatile 10%", WILD, wild[reg])):
    a = adv[sel]; surv = np.array([(a > x).mean() for x in k])
    fig.add_scatter(x=k, y=np.where(surv > 0, surv, np.nan), mode="lines", line=dict(color=col, width=2.2), name=lab)
    R[lab] = dict(mean=round(float(a.mean()), 2), over2=round(float((a > 2).mean()), 4), over3=round(float((a > 3).mean()), 4))
fig.update_yaxes(type="log", range=[-3.3, 0.05], title_text="share of positions", exponentformat="power")
fig.update_xaxes(title_text="worst move against the position, in units of the expected volatility over 4 hours (σ√T)")
fig.update_layout(title="The typical bad move is smaller than a random walk's, the rare one far larger<br><sup>Positions opened at every full hour and held 4 hours, long and short; "
                        "σ from the past 28 days' one-minute variance; five years of BTCUSDT</sup>", height=460, width=1100, margin=dict(t=100),
                  legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "14_05_excursions", FIG)

# ---------------------------------------------------------------- 3. stop fills: worst seller beyond the level, by time window
WIN = [0.1, 0.5, 1, 2, 5, 10]
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("Calm half of days", "Most volatile 10% of days"))
for c, (lab, col) in enumerate((("calm", CALM), ("volatile", WILD)), start=1):
    A = np.load(tape.ROOT / "interim" / f"l14_stopfan_{lab}.npy")
    for q, dash, wdt, name in ((50, "solid", 2.5, "median"), (95, "dash", 1.8, "worst 5%"), (99, "dot", 1.8, "worst 1%")):
        y = [float(np.nanpercentile(A[:, i, 1], q)) for i in range(len(WIN))]
        fig.add_scatter(x=WIN, y=y, mode="lines+markers", line=dict(color=col, width=wdt, dash=dash), marker=dict(size=6), name=name, legendgroup=name, showlegend=(c == 1), row=1, col=c)
    R[f"stops_{lab}"] = {f"{w}s": {q: round(float(np.nanpercentile(A[:, i, 1], q)), 1) for q in (50, 95, 99)} for i, w in enumerate(WIN)}
fig.update_xaxes(type="log", tickvals=WIN, ticktext=["0.1 s", "0.5 s", "1 s", "2 s", "5 s", "10 s"], title_text="time after the trigger")
fig.update_yaxes(title_text="worst seller's price beyond the stop level, bp", row=1, col=1)
fig.update_layout(title="What a stop might get: the worst price of the sellers who followed<br><sup>Every first crossing of levels 20, 50 and 100 bp apart; the worst price of the trades on the "
                        "stop's side within each time window. An approximation: the order book is not on the tape</sup>", height=460, width=1100, margin=dict(t=100),
                  legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "14_06_stop_fills", FIG)
(L14_RESULTS / "l14_s4_charts.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
