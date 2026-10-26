"""Lecture 15 §7 charts, from l15_capacity.json. 15_12: capacity map: the largest trade, executed over about a day, at which costs take half or all of the
edge per trade, from the square-root law: cost = c0 + Y sigma sqrt(Q / V), c0 = 3 bp (fee and spread with the re-posted entry of §6); Y = 1, band to Y = 0.5;
the most volatile year (2021) against the calmest (2023). 15_13: funding paid by a long against T-bill interest on the spare cash, by year. 15_14: long spot against long perpetual. 15_15 (appendix): aggregate impact
against net flow as a share of daily volume, log-log, with lines of slope 1/2 and 1."""
import json, sys
from pathlib import Path
import numpy as np
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

R = json.loads((L15_RESULTS / "l15_capacity.json").read_text()); Y = {r["year"]: r for r in R["by_year"]}
C0 = 3.0; E = np.geomspace(10, 300, 60)


def qmax(e, frac, yr, y):
    v, s = Y[yr]["V_bn_median"] * 1e3, Y[yr]["sigma_bp_median"]            # $m per day, bp per day
    x = np.maximum(e * frac - C0, 0) / (y * s); return v * x ** 2


fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                    subplot_titles=[f"{yr}: volume ${Y[yr]['V_bn_median']:.0f}bn a day, volatility {Y[yr]['sigma_bp_median']:.0f} bp a day" for yr in (2021, 2023)])
for c, yr in enumerate((2021, 2023), start=1):
    for frac, lab, col in ((1.0, "costs take all of the edge", SERIES[3]), (0.5, "costs take half of the edge", SERIES[0])):
        fig.add_scatter(x=E, y=qmax(E, frac, yr, 0.5), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip", row=1, col=c)
        fig.add_scatter(x=E, y=qmax(E, frac, yr, 1.0), mode="lines", line=dict(color=col, width=2.4), fill="tonexty", fillcolor=f"rgba({int(col[1:3], 16)},{int(col[3:5], 16)},{int(col[5:7], 16)},0.15)",
                        name=lab, legendgroup=lab, showlegend=(c == 1), row=1, col=c)
fig.update_xaxes(type="log", title_text="edge per trade, bp", tickvals=[10, 20, 50, 100, 200, 300])
fig.update_yaxes(type="log", tickvals=[0.1, 1, 10, 100, 1000, 10000], ticktext=["0.1", "1", "10", "100", "1,000", "10,000"], range=[-1.3, 4.7])
fig.update_yaxes(title_text="largest trade, $ million", row=1, col=1)
fig.update_layout(title="How large a trade can be before costs take its edge: square-root impact, the edge per trade and the market's volatility<br><sup>Cost = 3 bp + "
                        "Y × daily volatility × √(trade / daily volume), executed over about a day; line Y = 1, band to Y = 0.5. Volume and volatility: medians of the year</sup>",
                  height=480, width=1100, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "15_12_capacity", FIG)

# ---------------------------------------------------------------- 15_13: funding paid against interest on the spare cash; 15_14: long spot against long perpetual
import polars as pl

PV = json.loads((L15_RESULTS / "l15_perp_vs_spot.json").read_text()); BY = PV["by_year"]
fig = make_subplots(rows=1, cols=1)
lab_y = [f"{r['year']}" + (" (Oct-Dec)" if r["year"] == 2021 else " (to Sep)" if r["year"] == 2026 else "") for r in BY]
fig.add_bar(x=lab_y, y=[100 * r["funding"] for r in BY], name="funding paid by a long perpetual", marker=dict(color=SERIES[3], line=dict(width=0)),
            text=[f"{100 * r['funding']:.1f}%" for r in BY], textposition="outside")
fig.add_bar(x=lab_y, y=[100 * r["cash"] for r in BY], name="interest on the cash it does not tie up (3-month T-bill)", marker=dict(color=SERIES[1], line=dict(width=0)),
            text=[f"{100 * r['cash']:.1f}%" for r in BY], textposition="outside")
fig.update_yaxes(title_text="% of the position, over the year", range=[0, 14])
fig.update_xaxes(type="category")
fig.update_layout(barmode="group", title="A long perpetual pays funding; the cash it frees earns interest, and the funding was the larger in every full year<br><sup>BTCUSDT on Binance; "
                        "funding summed over each year's settlements; T-bill rate from FRED (DTB3)</sup>", height=450, width=1000, margin=dict(t=100, l=80),
                  legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "15_13_funding", FIG)
X = pl.read_parquet(tape.ROOT / "interim" / "l15_perp_vs_spot.parquet")
fig = make_subplots(rows=1, cols=1)
for col_, lab, colr, dash in (("r_spot", "long spot", INK, "solid"), ("r_perp_cash", "long perpetual, after funding, spare cash in T-bills", SERIES[1], "solid"),
                              ("r_perp", "long perpetual, after funding", SERIES[3], "solid")):
    w = (1 + X[col_]).cum_prod()
    fig.add_scatter(x=X["t"].to_list(), y=w.to_list(), mode="lines", line=dict(color=colr, width=2, dash=dash), name=f"{lab}: {w[-1]:.2f}")
fig.update_yaxes(type="log", title_text="value of $1 (log scale)", tickvals=[0.3, 0.5, 0.7, 1, 1.5, 2, 3], ticktext=["0.3", "0.5", "0.7", "1", "1.5", "2", "3"])
fig.update_layout(title="Five years long bitcoin: the perpetual trailed spot by about 8% a year in funding, 4% after interest on the spare cash<br><sup>BTCUSDT, "
                        "October 2021 to September 2026; the perpetual's price tracked spot within a median of 5 bp</sup>", height=460, width=1000, margin=dict(t=100, l=80),
                  legend=dict(orientation="h", y=-0.15, x=0))
save_figure(fig, PREFIX + "15_14_perp_vs_spot", FIG)

# ---------------------------------------------------------------- 15_15: aggregate impact, appendix
fig = make_subplots(rows=1, cols=1)
for (W, r), col in zip(R["shape"].items(), (SERIES[0], SERIES[1], SERIES[2])):
    x, y = np.array(r["bins_x"]), np.array(r["bins_y"]); ok = y > 0
    fig.add_scatter(x=x[ok], y=y[ok], mode="lines+markers", line=dict(color=col, width=2), marker=dict(size=7), name=f"{W} windows (slope {r['slope_all']:.2f})")
xr = np.array([1e-5, 1e-2])
for slope, lab, dash in ((0.5, "slope 1/2: square-root law", "dot"), (1.0, "slope 1: linear", "dash")):
    fig.add_scatter(x=xr, y=0.045 * (xr / 1e-3) ** slope, mode="lines", line=dict(color=MUTED, dash=dash, width=1.5), name=lab)
fig.update_xaxes(type="log", title_text="net aggressive buying in the window, share of a typical day's volume")
fig.update_yaxes(type="log", title_text="price move with the flow, in daily volatilities")
fig.update_layout(title="Aggregate impact: the net flow of many traders moves the price close to linearly with its size over this range<br><sup>Five years of BTCUSDT; "
                        "windows sorted into twenty groups by size; aggregate impact, not one trader's order</sup>", height=460, width=950, margin=dict(t=100, l=80),
                  legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "15_15_aggregate_impact", FIG)
