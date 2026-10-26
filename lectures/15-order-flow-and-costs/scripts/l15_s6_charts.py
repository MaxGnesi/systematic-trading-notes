"""Lecture 15 §6 charts, from data/interim/l15_resting.parquet (l15_resting.py). 15_09: how often a resting order is filled, and what it saves against a
market order when it chases at the end of the wait, by distance and waiting time. 15_10: what it misses: the price one hour after the decision, for orders
that were filled and orders that were not, for trend entries (buying after a rise) and grid entries (buying after a fall)."""
import sys
from pathlib import Path
import polars as pl
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

A = pl.read_parquet(tape.ROOT / "interim" / "l15_resting.parquet").filter((pl.col("rule") == "through") & (pl.col("vol") == "all") & (pl.col("sweep") == "all"))
DX = ["1 tick", "2 bp", "5 bp", "10 bp", "20 bp"]; DL = [0, 2, 5, 10, 20]
TCOL = {1: SERIES[0], 10: SERIES[1], 60: SERIES[2]}

# ---------------------------------------------------------------- 15_09: filled, and what it saves
a = A.filter(pl.col("move") == "all")
fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("How often it is filled", "What it saves against a market order, chasing if not filled"))
for T, col in TCOL.items():
    x = a.filter(pl.col("T") == T).sort("delta")
    fig.add_scatter(x=DX, y=(100 * x["fill"]).to_list(), mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=9), name=f"waiting {T} min", legendgroup=str(T), row=1, col=1)
    fig.add_scatter(x=DX, y=x["b_minus_a"].to_list(), mode="lines+markers", line=dict(color=col, width=2.2), marker=dict(size=9), showlegend=False, legendgroup=str(T), row=1, col=2)
fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=2)
fig.update_yaxes(title_text="filled, %", range=[0, 105], row=1, col=1); fig.update_yaxes(title_text="against a market order, bp", row=1, col=2)
fig.update_xaxes(title_text="resting order's distance from the price")
fig.update_layout(title="A resting order one tick inside is filled four times in five within a minute; chasing the rest still saves about 2 bp<br><sup>Five years of BTCUSDT, "
                        "a decision every seventh minute, buys and mirrored sells;<br>filled when the price trades through the order (one-minute bars); fees 5 bp taker, 2 bp maker</sup>",
                  height=470, width=1100, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_09_resting_fill_and_saving", FIG)

# ---------------------------------------------------------------- 15_10: what it misses
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("Trend entry: buying after a rise", "Grid entry: buying after a fall"))
for c, mv in enumerate(("after a rise", "after a fall"), start=1):
    x = A.filter((pl.col("move") == mv) & (pl.col("T") == 10)).sort("delta")
    fig.add_bar(x=DX, y=x["m60_filled"].to_list(), name="orders that were filled", marker=dict(color=SERIES[3], line=dict(width=0)), showlegend=(c == 1), legendgroup="f",
                text=[f"{100 * v:.0f}% filled" for v in x["fill"].to_list()], textposition="outside", row=1, col=c)
    fig.add_bar(x=DX, y=x["m60_unfilled"].to_list(), name="orders that were not filled", marker=dict(color=SERIES[0], line=dict(width=0)), showlegend=(c == 1), legendgroup="u", row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_yaxes(title_text="price one hour later, bp", row=1, col=1)
fig.update_xaxes(title_text="resting order's distance from the price (waiting 10 minutes)")
fig.update_layout(barmode="group", title="What a resting order misses: the orders that fill are those the price came against, the misses are those it ran away from<br><sup>"
                  "Five years of BTCUSDT; trend entry: the last hour rose by more than one typical hourly move (mirrored for sells); grid entry: it fell</sup>",
                  height=480, width=1100, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_10_resting_what_it_misses", FIG)

# ---------------------------------------------------------------- 15_11: the cut-off: mean saving against the tail
import json
T = json.loads((L15_RESULTS / "l15_resting_tail.json").read_text())
CX = ["5 s", "10 s", "30 s", "1 min", "10 min", "60 min"]
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("Resting one tick inside", "Resting 2 bp inside"))
for c, off in enumerate(("1 tick", "2 bp"), start=1):
    r = {x["cut"]: x for x in T if x["offset"] == off}
    for key, lab, col, dash in (("mean", "average", SERIES[0], "solid"), ("p95", "95th percentile", SERIES[1], "solid"), ("es95", "average of the worst 5%", SERIES[3], "solid"),
                                ("p99", "99th percentile", SERIES[3], "dot")):
        fig.add_scatter(x=CX, y=[r[x][key] for x in CX], mode="lines+markers", name=lab, line=dict(color=col, width=2.2, dash=dash), marker=dict(size=8),
                        legendgroup=key, showlegend=(c == 1), row=1, col=c)
    fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
RP = {x["variant"]: x for x in json.loads((L15_RESULTS / "l15_resting_repost.json").read_text())}
RX = {"30 s": "re-post every 5 s, market order after 30 s", "1 min": "re-post every 5 s, market order after 60 s", "60 min": "re-post every 5 s, market order after 3600 s"}
for key, lab, col in (("mean", "re-posted every 5 s: average", SERIES[0]), ("es95", "re-posted every 5 s: average of the worst 5%", SERIES[3])):
    fig.add_scatter(x=list(RX), y=[RP[v][key] for v in RX.values()], mode="markers", marker=dict(color=col, size=13, symbol="diamond-open", line=dict(width=2.5)),
                    name=lab, row=1, col=1)
fig.update_yaxes(title_text="cost against a market order, bp", row=1, col=1)
fig.update_xaxes(title_text="cut-off: if not filled by then, send a market order")
fig.update_layout(title="A longer wait saves a little more on average and costs much more in the worst cases; re-posting the order avoids the tail<br><sup>Cost of the resting order against a market order sent "
                        "at once (negative = cheaper), over all orders. Diamonds: the order re-posted one tick inside the current price every 5 s, market order at the cut-off.<br>"
                        "Every tenth day, November 2021 to September 2026, tick tape</sup>",
                  height=500, width=1100, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_11_resting_cutoff", FIG)
