"""Lecture 17 figures 17_06 and 17_07. 17_06, the size profile: (a) gross result by regime on simulated prices (l17_shapes_mc.json: 8 levels, step
25 bp, no costs, 300 days per regime, 95% intervals); (b) on the tape (l17_shapes.parquet: ladder 200 bp each side), gross result by step and shape,
2021-24 and 2025-26. 17_07, width, exits and refresh on the tape: (a) Sharpe ratio after costs by width, uniform sizes (l17_shapes.parquet);
(b) Sharpe ratio and (c) the worst 1% of days, by exit and refresh rule, ladder 200 bp each side (l17_levers.parquet)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

COL = {"uniform": MUTED, "V-shaped": SERIES[1], "bell-shaped": SERIES[2], "bimodal": SERIES[0]}
per = lambda df: df.with_columns(pl.when(pl.col("year") <= 2024).then(pl.lit("2021-24")).otherwise(pl.lit("2025-26")).alias("p"))
sr = (pl.col("net").mean() / pl.col("net").std() * np.sqrt(365)).alias("sr")

# 17_06
M = pl.DataFrame(json.loads((L17_RESULTS / "l17_shapes_mc.json").read_text())).filter(pl.col("step") == 25)
REG = ["swings", "random walk", "trend days", "large jumps", "runs"]
S = per(pl.read_parquet(L17_RESULTS / "l17_shapes.parquet").filter((pl.col("width") == 200) & (pl.col("levels") >= 2)))
G = S.group_by("step", "shape", "p").agg(pl.col("gross").mean().alias("g"), (pl.col("gross").std() / pl.len().sqrt()).alias("se"))
fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.1,
                    subplot_titles=("(a) Simulated prices: each shape wins in its own regime", "(b) The tape: all three near zero, gross"))
for sh, c in COL.items():
    m = M.filter(pl.col("shape") == sh); m = m.sort(pl.col("regime").replace_strict({r: i for i, r in enumerate(REG)}))
    fig.add_bar(x=m["regime"], y=m["gross"], error_y=dict(array=1.96 * m["se"].to_numpy(), color=INK, thickness=1), marker=dict(color=c), name=sh, legendgroup=sh, row=1, col=1)
    for p, dash in (("2021-24", None), ("2025-26", "dot")):
        gg = G.filter((pl.col("shape") == sh) & (pl.col("p") == p)).sort("step")
        fig.add_scatter(x=[f"{s} bp" for s in gg["step"]], y=gg["g"], mode="lines+markers", line=dict(color=c, width=2, dash=dash), marker=dict(size=7),
                        name=f"{sh}, {p}", showlegend=False, legendgroup=sh, row=1, col=2)
fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=INK, width=2), name="tape 2021-24 (solid)", row=1, col=2)
fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=INK, width=2, dash="dot"), name="tape 2025-26 (dotted)", row=1, col=2)
for c in (1, 2): fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=c)
fig.update_yaxes(title_text="gross, % of capital per day", row=1, col=1); fig.update_yaxes(title_text="gross, % of capital per day", row=1, col=2)
fig.update_xaxes(title_text="simulated regime (step 25 bp, 8 levels a side)", row=1, col=1); fig.update_xaxes(title_text="step (ladder 200 bp each side)", row=1, col=2)
fig.update_layout(title="The size profile sets how much the grid bets near the centre, not what it bets on<br><sup>Left: Monte Carlo, 300 simulated days per regime, "
                        "no costs, 95% intervals. Right: BTCUSDT, Oct 2021 - Sep 2026, before costs; every shape has the same capital in a full ladder</sup>",
                  barmode="group", height=540, width=1200, margin=dict(t=110, l=70, b=110), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "17_06_shapes_regimes", FIG)

# 17_07
U = per(pl.read_parquet(L17_RESULTS / "l17_shapes.parquet").filter(pl.col("shape") == "uniform")).group_by("step", "width", "p").agg(sr).sort("width")
L = per(pl.read_parquet(L17_RESULTS / "l17_levers.parquet").filter(~pl.col("rule").str.starts_with("levels")))
LA = L.group_by("step", "rule", "p").agg(sr, pl.col("net").quantile(0.01).alias("w1"))
RULES = [("base", "stop + restart, daily refresh (base)", INK), ("stop, off for the day", "stop, then off for the day", SERIES[0]),
         ("hold at the cap", "hold at the cap, no stop", SERIES[3]), ("refresh every 4 hours", "refresh every 4 hours", SERIES[4]),
         ("refresh every hour", "refresh every hour", SERIES[1])]
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.07, subplot_titles=("(a) Width: Sharpe ratio after costs", "(b) Exits and refresh: Sharpe ratio after costs",
                                                                              "(c) Exits and refresh: the worst 1% of days"))
WC = {25: "#cfc4f0", 50: "#a896e3", 100: "#6f55c4", 200: "#3c2878"}
for st, c in WC.items():
    for p, dash in (("2021-24", None), ("2025-26", "dot")):
        u = U.filter((pl.col("step") == st) & (pl.col("p") == p))
        if len(u) > 1:
            fig.add_scatter(x=u["width"], y=u["sr"], mode="lines+markers", line=dict(color=c, width=2, dash=dash), marker=dict(size=7),
                            name=f"step {st} bp", showlegend=(p == "2021-24"), legendgroup=f"w{st}", row=1, col=1)
for key, nm, c in RULES:
    for col, val in ((2, "sr"), (3, "w1")):
        for p, op in (("2021-24", 1.0), ("2025-26", 0.45)):
            a = LA.filter((pl.col("rule") == key) & (pl.col("p") == p)).sort("step")
            fig.add_bar(x=[f"{s} bp" for s in a["step"]], y=a[val], marker=dict(color=c, opacity=op), name=nm, legendgroup=key,
                        showlegend=(col == 2 and p == "2021-24"), offsetgroup=f"{key}{p}", row=1, col=col)
for c in (1, 2): fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=c)
fig.update_xaxes(title_text="width: how far the ladder reaches each way, bp", tickvals=[100, 200, 400], type="log", row=1, col=1)
fig.update_xaxes(title_text="step", row=1, col=2); fig.update_xaxes(title_text="step", row=1, col=3)
fig.update_yaxes(title_text="Sharpe ratio", row=1, col=1); fig.update_yaxes(title_text="Sharpe ratio", row=1, col=2); fig.update_yaxes(title_text="% of capital", row=1, col=3)
fig.update_layout(title="Width, exits and refresh change the cost of leaving and the size of the worst days, not the edge<br><sup>BTCUSDT, Oct 2021 - Sep 2026, "
                        "after all costs. (a) uniform sizes, solid 2021-24, dotted 2025-26. (b), (c) ladder 200 bp each side; full colour 2021-24, pale 2025-26</sup>",
                  barmode="group", height=560, width=1250, margin=dict(t=110, l=60, b=130), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "17_07_levers", FIG)
