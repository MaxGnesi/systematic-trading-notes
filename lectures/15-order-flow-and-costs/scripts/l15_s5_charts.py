"""Lecture 15 §5 charts, from l15_costs_analysis.json. 15_07: what a trade costs, by order size: a market order (taker fee + effective half-spread) against
a resting order filled by such an order (maker fee + what it loses to the move of the mid over the next 60 s). 15_08: what the resting side keeps,
1 s to 60 s after the fill, by volatility regime and in the minute after a sweep."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

R = json.loads((L15_RESULTS / "l15_costs_analysis.json").read_text())
MAKER, TAKER = 2.0, 5.0; BLAB = ["< $1k", "$1k-10k", "$10k-100k", "$100k-1m", "> $1m"]
S = {r["bucket"]: r for r in R["by_size"]}

# ---------------------------------------------------------------- 15_07: market order against resting order
fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("A market order pays", "A resting order filled by it pays"))
X = ["under $1k", "$1k-10k", "$10k-100k", "$100k-1m", "over $1m"]
fig.add_bar(x=X, y=[TAKER] * 5, name="exchange fee (regular account)", marker=dict(color=MUTED, line=dict(width=0)), legendgroup="fee", row=1, col=1)
fig.add_bar(x=X, y=[S[b]["eff"] for b in BLAB], name="spread and impact paid", marker=dict(color=SERIES[0], line=dict(width=0)),
            text=[f"{TAKER + S[b]['eff']:.1f}" for b in BLAB], textposition="outside", row=1, col=1)
fig.add_bar(x=X, y=[MAKER] * 5, name="exchange fee", marker=dict(color=MUTED, line=dict(width=0)), legendgroup="fee", showlegend=False, row=1, col=2)
fig.add_bar(x=X, y=[-S[b]["real_60s"] for b in BLAB], name="lost to the move of the price in the next 60 s", marker=dict(color=SERIES[3], line=dict(width=0)),
            text=[f"{MAKER - S[b]['real_60s']:.1f}" for b in BLAB], textposition="outside", row=1, col=2)
fig.update_yaxes(title_text="cost per trade, bp of the amount traded", range=[0, 8.5], row=1, col=1)
fig.update_xaxes(title_text="size of the market order")
fig.update_layout(barmode="stack", title="On BTCUSDT a trade's cost is mostly the exchange fee; the spread is one tick, and size adds impact<br><sup>Mean per order, "
                                         "80 days from May 2023 to March 2024 (every fourth day); fees 5 bp taker, 2 bp maker</sup>",
                  height=470, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_07_cost_by_size", FIG)

# ---------------------------------------------------------------- 15_08: what the resting side keeps, by horizon
H = ["1s", "10s", "60s"]; HX = ["1 s", "10 s", "60 s"]
V = {r["vol"]: r for r in R["by_vol"]}; AS = {r["after_sweep"]: r for r in R["after_sweep"]}
fig = make_subplots(rows=1, cols=1)
for lab, row, col, dash in (("calm hours", V["calm"], SERIES[0], "solid"), ("normal hours", V["normal"], SERIES[1], "solid"), ("volatile hours", V["volatile"], SERIES[3], "solid"),
                            ("the minute after a sweep of 10 bp or more (2% sample)", AS[True], INK, "dot")):
    fig.add_scatter(x=HX, y=[row[f"real_{h}"] for h in H], mode="lines+markers", name=lab, line=dict(color=col, width=2.2, dash=dash), marker=dict(size=9))
fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
fig.update_xaxes(title_text="time after the fill")
fig.update_yaxes(title_text="kept by the resting side, bp")
fig.update_layout(title="The resting side earns the half-tick and loses more to the move that follows, most in volatile hours<br><sup>Realised half-spread: the fill "
                        "against the mid 1 s, 10 s and 60 s later, mean per order; negative = the price moved against the resting order. 80 days, May 2023 to March 2024</sup>",
                  height=470, width=950, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "15_08_adverse_selection", FIG)
