"""Lecture 17 figure 17_04, from l17_tape_vs_shuffled.parquet: the grid on five years of the tape (Oct 2021 - Sep 2026), steps 10-200 bp, ladder about
200 bp each side, stop + restart, daily close, maker 2 / taker 5 bp, funding. Left: the accounts per day by step. Middle: the gross result on the tape
minus the same days with their minutes shuffled, with 95% intervals. Right: the net result by year."""
import sys
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
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()

R = pl.read_parquet(L17_RESULTS / "l17_tape_vs_shuffled.parquet")
T = R.filter(pl.col("path") == "tape").with_columns((pl.col("maker_fee") + pl.col("taker_fee") - pl.col("funding")).alias("costs"))
A = T.group_by("step").agg([pl.col(c).mean() for c in ("trips_income", "inventory", "gross", "costs", "net")]).sort("step")
W = R.pivot(on="path", index=["step", "day"], values="gross").with_columns((pl.col("tape") - pl.col("shuffled")).alias("d"))
D = W.group_by("step").agg(pl.col("d").mean().alias("m"), (pl.col("d").std() / pl.len().sqrt()).alias("se")).sort("step")
Y = T.group_by("step", "year").agg(pl.col("net").mean()).sort("step", "year")
lab = [f"{s} bp" for s in A["step"]]
fig = make_subplots(rows=1, cols=3, column_widths=[0.42, 0.25, 0.33], horizontal_spacing=0.07,
                    subplot_titles=("The accounts, % of capital per day", "Tape minus shuffled minutes, gross", "Net result by year, % per day"))
for c, col, nm in (("trips_income", SERIES[1], "round-trip income"), ("inventory", SERIES[0], "inventory result"), ("gross", INK, "gross result"),
                   ("costs", MUTED, "fees and funding (cost)"), ("net", SERIES[3], "net result")):
    y = A[c].to_numpy() * (-1 if c == "costs" else 1)
    fig.add_bar(x=lab, y=y, marker=dict(color=col), name=nm, legendgroup="a", row=1, col=1)
fig.add_bar(x=lab, y=D["m"], error_y=dict(array=1.96 * D["se"].to_numpy(), color=INK, thickness=1), marker=dict(color=SERIES[2]),
            name="tape minus shuffled (95% interval)", row=1, col=2)
for k, (st, col) in enumerate(zip(A["step"], ("#cfc4f0", "#a896e3", "#8268d2", "#5f43b2", "#3c2878"))):
    y = Y.filter(pl.col("step") == st)
    fig.add_scatter(x=y["year"], y=y["net"], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=7), name=f"net, step {st} bp", row=1, col=3)
for c in (1, 2, 3): fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=1, col=c)
fig.update_xaxes(title_text="step", row=1, col=1); fig.update_xaxes(title_text="step", row=1, col=2)
fig.update_xaxes(title_text="year (2021: Oct-Dec; 2026: Jan-Sep)", dtick=1, row=1, col=3)
fig.update_layout(title="The grid on five years of BTCUSDT: the round trips pay, the inventory takes it back, the costs decide; the tape is worse than its own minutes shuffled"
                        "<br><sup>Oct 2021 - Sep 2026, 1,826 days; paired grid, ladder about 200 bp each side (levels = 200 / step), stop + restart, daily close, "
                        "fills only when traded through, maker 2 bp, taker 5 bp, funding</sup>", barmode="group", height=560, width=1250,
                  margin=dict(t=110, l=60, b=120), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "17_04_tape", FIG)
