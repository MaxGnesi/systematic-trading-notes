"""Lecture 17 figure 17_01: one day of the grid on the tape, 12 March 2024 (Lecture 16's reference day), step 50 bp, 4 levels a side, stop + restart,
daily close. Top: the price (last trade of every 10 s), the ladder's levels around each centre, every fill, stop and restart. Middle: the position
in units. Bottom: what the day earned so far, per USD 100,000 of capital: round-trip income, the inventory result (open units marked to the price,
stops and the close included) and their sum, the gross result. Before fees and funding. From l17_day_log.py, which matches l17_grid.simulate."""
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
import l17_grid as g
from l17_day_log import log_day
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()
usd = lambda v: ("−" if v < 0 else "") + f"USD {abs(v):,.0f}"

CAP, N = 100_000, 4
E, tot, x = log_day(g.load("2024-03", "2024-03"), "2024-03-12", 50, N)
s, last, step, u = x["s"], x["last"], x["step"], x["u"]
hrs = (s % 86400) / 3600
pick = np.r_[np.nonzero(np.diff(s // 10))[0], len(s) - 1]                     # last trade of every 10 seconds
equity = (x["cash"] + x["q"] * u * last) * CAP; trips = x["trips"] * step * u * CAP; inv = equity - trips
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.56, 0.17, 0.27], vertical_spacing=0.04)
# the ladder around each centre, from the start or restart until the next one
rs = E.filter(pl.col("event") == "restart")
starts = [(0.0, E["centre"][0])] + list(zip((rs["s"].to_numpy() % 86400) / 3600, rs["price"].to_list()))
ends = [h for h, _ in starts[1:]] + [24.0]
for (h0, c), h1 in zip(starts, ends):
    for k in range(-N, N + 1):
        col = MUTED if k == 0 else (SERIES[0] if k < 0 else SERIES[3])
        fig.add_scatter(x=[h0, h1], y=[c + k * step] * 2, mode="lines", line=dict(color=col, width=1 if k else 1.2, dash="dot" if k == 0 else "solid"),
                        opacity=0.45, showlegend=False, hoverinfo="skip", row=1, col=1)
    for side in (-1, 1):
        fig.add_scatter(x=[h0, h1], y=[c + side * (N + 1) * step] * 2, mode="lines", line=dict(color=INK, width=1, dash="dash"), opacity=0.5,
                        showlegend=bool(h0 == 0 and side == 1), name="stop: one step beyond the last level", hoverinfo="skip", row=1, col=1)
fig.add_scatter(x=hrs[pick], y=last[pick], mode="lines", line=dict(color=INK, width=1.3), name="price", row=1, col=1)
for ev, sym, col, name in (("buy", "triangle-up", SERIES[0], "buy filled"), ("sell", "triangle-down", SERIES[3], "sell filled"),
                           ("stop", "x", INK, "stop: all units closed at market"), ("daily close", "square", MUTED, "daily close")):
    e = E.filter(pl.col("event") == ev); h = (e["s"].to_numpy() % 86400) / 3600
    yv = e["price"].to_numpy() if ev != "daily close" else last[-1:]
    fig.add_scatter(x=h, y=yv, mode="markers", marker=dict(symbol=sym, color=col, size=9 if ev != "stop" else 11, line=dict(width=0)), name=name,
                    customdata=e["position"].to_numpy(), hovertemplate="%{x:.2f} h: " + ev + " at %{y:,.0f}, position %{customdata}<extra></extra>", row=1, col=1)
fig.add_scatter(x=hrs, y=x["q"], mode="lines", line=dict(color=SERIES[2], width=1.6, shape="hv"), name="position, units (+ long, − short)", row=2, col=1)
fig.add_scatter(x=hrs[pick], y=trips[pick], mode="lines", line=dict(color=SERIES[1], width=2), name="round-trip income", row=3, col=1)
fig.add_scatter(x=hrs[pick], y=inv[pick], mode="lines", line=dict(color=SERIES[0], width=2), name="inventory result", row=3, col=1)
fig.add_scatter(x=hrs[pick], y=equity[pick], mode="lines", line=dict(color=INK, width=2), name="gross result = the sum", row=3, col=1)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=3, col=1)
fig.add_annotation(x=21.4, y=67700, text="16:12–17:49: a fall of 4.0% and a rebound of 2.8%:<br>buy after buy, then sell after sell, three stops",
                   showarrow=False, font=dict(size=11, color=MUTED), row=1, col=1)
fig.update_yaxes(title_text="price, USD", tickformat=",", row=1, col=1)
fig.update_yaxes(title_text="units", tickvals=list(range(-N, N + 1, 2)), row=2, col=1)
fig.update_yaxes(title_text="USD per 100k", tickformat=",", row=3, col=1)
fig.update_xaxes(title_text="hour of the day, UTC", tickvals=list(range(0, 25, 2)), range=[0, 24], row=3, col=1)
fig.update_layout(title=f"One day of the grid on the tape: 12 March 2024, step 50 bp, {N} levels a side<br><sup>{int(tot['trips'])} round trips earned "
                        f"{usd(tot['trips_income']*1e3)}, the inventory result was {usd(tot['inventory']*1e3)}, the gross result {usd(tot['gross']*1e3)} "
                        f"per USD 100,000 of capital, before fees ({usd(-(tot['maker_fee']+tot['taker_fee'])*1e3)}) and funding ({usd(tot['funding']*1e3)})</sup>",
                  height=820, width=1200, margin=dict(t=110, l=80, b=60), legend=dict(orientation="h", y=-0.08, x=0))
save_figure(fig, PREFIX + "17_01_grid_day", FIG)
print(tot)
