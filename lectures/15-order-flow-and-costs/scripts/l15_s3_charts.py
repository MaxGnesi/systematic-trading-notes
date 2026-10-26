"""Lecture 15 §3 charts: the price path after a sweep, in the sweep's direction, in bp from the price just before it. Independent sweeps (the first of at least
MIN bp in each 10-minute block). 15_04: sweeps with and against the slower trend, by size, all volatility regimes."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
D = tape.ROOT / "interim" / "tape" / "BTCUSDT"

S = pl.read_parquet(tape.ROOT / "interim" / "l15_sweeps.parquet")
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time").with_columns(pl.col("close").forward_fill())
lp = np.log(g["close"].to_numpy()); r1 = np.r_[0.0, np.diff(lp)]
rv60 = np.convolve(r1 ** 2, np.ones(60), "full")[:n]; med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
dvar = pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
t0ms = int(np.datetime64(t0, "ms").astype(np.int64))
i = (S["time_ms"].to_numpy() - t0ms) // 60_000 - 1                             # the minute before the sweep
ok = (i >= 3 * 1440) & (i < n); S = S.filter(pl.Series(ok)); i = i[ok]
S = S.with_columns(pl.Series("trend", (lp[i] - lp[i - 3 * 1440]) / np.sqrt(dvar[i] * 3)), pl.Series("reg", rv60[i] / med[i])).filter(pl.col("reg").is_finite() & pl.col("trend").is_finite())
t1, t2 = np.quantile(S["reg"].to_numpy(), [1 / 3, 2 / 3])                     # the same regime cut-offs as l15_sweeps_matrix.py
S = S.with_columns(pl.when(pl.col("trend").abs() < 0.5).then(pl.lit("none")).when(pl.col("trend").sign() == pl.col("side")).then(pl.lit("with")).otherwise(pl.lit("against")).alias("rel"),
                   pl.when(pl.col("reg") < t1).then(pl.lit("calm")).when(pl.col("reg") < t2).then(pl.lit("normal")).otherwise(pl.lit("volatile")).alias("vol"),
                   *[(pl.col("side") * (pl.col(c) / pl.col("p_before")).log() * 1e4).alias(f"x_{c}") for c in ("p_last", "p_10s", "p_1m", "p_10m", "p_1h")])
STEPS = ["x_p_last", "x_p_10s", "x_p_1m", "x_p_10m", "x_p_1h"]; XL = ["before", "last fill", "+10 s", "+1 min", "+10 min", "+1 h"]


def independent(MIN):
    return (S.filter(pl.col("move_bp") >= MIN).sort("time_ms").with_columns((pl.col("time_ms") // 600_000).alias("blk")).unique(subset="blk", keep="first", maintain_order=True))


def path(c):
    return [0.0] + [float(c[s].drop_nulls().median()) for s in STEPS]


R = {}
# ---------------------------------------------------------------- 15_04: with and against the trend, by size
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05, subplot_titles=("Sweeps with the slower trend", "Sweeps against the slower trend"))
for c, rl in enumerate(("with", "against"), start=1):
    for MIN, col in ((5, SERIES[1]), (10, SERIES[0]), (20, SERIES[2])):
        cc = independent(MIN).filter(pl.col("rel") == rl); y = path(cc); R[f"{rl} | >= {MIN} bp"] = dict(n=cc.height, path=[round(v, 1) for v in y])
        fig.add_scatter(x=XL, y=y, mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=8), name=f"at least {MIN} bp", legendgroup=str(MIN), showlegend=(c == 1), row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_yaxes(title_text="bp from before, in the sweep's direction", row=1, col=1)
fig.update_layout(title="About half of a sweep comes back within ten seconds; after that, the slower trend decides the rest<br><sup>Median price path after independent sweeps "
                        "(the first in each 10-minute block), five years of BTCUSDT; 0 = back where the sweep started</sup>", height=470, width=1100, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.16, x=0))
save_figure(fig, PREFIX + "15_04_sweep_absorption", FIG)
(L15_RESULTS / "l15_s3_charts.json").write_text(json.dumps(R, indent=1))
for k, v in R.items(): print(f"{k:22} n {v['n']:5}  " + "  ".join(f"{a} {b:+.1f}" for a, b in zip(XL, v["path"])))
