"""Lecture 16 figure 16_02: how an hourly rule reads a dollar-bar value. The trend measure computed on dollar bars (fast span 1 day = 48 bars, slow 4 x,
divided by the volatility of bar price changes, scaled by its own past; version B of l16_plugin.py) drawn as the staircase it is on the clock: it
steps when a bar finishes and stays flat until the next. At each hourly close the rule reads the height of the step: the value of the last finished bar.
Below each hour: how many bars finished in it (the hourly summary). 12 March 2024, 00:00-04:00 and 15:00-19:00 UTC."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()

DAY = datetime(2024, 3, 12); PER_DAY = 48
DB = pl.concat([pl.read_parquet(f, columns=["end_ms", "close"]) for f in sorted((tape.ROOT / "interim" / "bars" / "BTCUSDT" / "dollar").glob("*.parquet"))]).sort("end_ms")
bt, bp = DB["end_ms"].to_numpy(), DB["close"].to_numpy()
sd = pl.Series(np.r_[0.0, np.diff(bp)] ** 2).ewm_mean(span=36 * PER_DAY, min_samples=7 * PER_DAY).sqrt().to_numpy()
raw = (pl.Series(bp).ewm_mean(span=PER_DAY, adjust=False).to_numpy() - pl.Series(bp).ewm_mean(span=4 * PER_DAY, adjust=False).to_numpy()) / sd
ok = np.isfinite(raw); val = raw / (np.cumsum(np.where(ok, np.abs(raw), 0.0)) / np.maximum(np.cumsum(ok), 1))
T = pl.from_epoch(pl.Series(bt), time_unit="ms").to_list()

fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05, subplot_titles=("A quiet night, 00:00 to 04:00", "The afternoon sell-off, 15:00 to 19:00"))
for c, (h0, h1) in enumerate(((0, 4), (15, 19)), start=1):
    t0, t1 = DAY + timedelta(hours=h0), DAY + timedelta(hours=h1)
    i0 = max(i for i, t in enumerate(T) if t <= t0); i1 = max(i for i, t in enumerate(T) if t <= t1)
    xs = [t0] + T[i0 + 1:i1 + 1] + [t1]; ys = [val[i0]] + list(val[i0 + 1:i1 + 1]) + [val[i1]]
    fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=SERIES[0], width=2.2, shape="hv"), name="trend measure on dollar bars (a staircase)", showlegend=(c == 1), row=1, col=c)
    fig.add_scatter(x=T[i0 + 1:i1 + 1], y=list(val[i0 + 1:i1 + 1]), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=2.2, color=SERIES[0])), name="a dollar bar finishes: the value steps",
                    showlegend=(c == 1), row=1, col=c)
    for h in range(h0 + 1, h1 + 1):
        th = DAY + timedelta(hours=h); j = max(i for i, t in enumerate(T) if t <= th); k = sum(1 for t in T if th - timedelta(hours=1) < t <= th)
        fig.add_vline(x=th, line=dict(color=SERIES[1], width=1.2), row=1, col=c)
        fig.add_scatter(x=[th], y=[val[j]], mode="markers", marker=dict(color=SERIES[1], size=12, symbol="diamond"), name="what the rule reads at the hourly close",
                        showlegend=(c == 1 and h == h0 + 1), row=1, col=c)
        fig.add_annotation(x=th - timedelta(minutes=30), y=1, yref="paper", text=f"{k} bar{'s' if k != 1 else ''} finished", showarrow=False, yshift=-8, font=dict(size=10, color=MUTED),
                           xref=f"x{c}")
        if (c, h) == (2, 17):
            fig.add_annotation(x=th, y=val[j], ax=150, ay=-90, text=f"17:00 reads the bar that ended {T[j]:%H:%M:%S}:<br>value {val[j]:+.2f}, {(th - T[j]).total_seconds() / 60:.0f} minutes old",
                               showarrow=True, arrowhead=2, font=dict(size=11), bgcolor="rgba(255,255,255,0.85)", row=1, col=c)
        if (c, h) == (1, 3):
            fig.add_annotation(x=th, y=val[j], ax=-120, ay=45, text=f"03:00 reads a bar from {T[j]:%H:%M}:<br>an hour old: nothing worth a bar happened",
                               showarrow=True, arrowhead=2, font=dict(size=11), bgcolor="rgba(255,255,255,0.85)", row=1, col=c)
    fig.update_xaxes(range=[t0 - timedelta(minutes=5), t1 + timedelta(minutes=8)], row=1, col=c)
fig.add_hline(y=0, line=dict(color=MUTED, dash="dot", width=1))
fig.update_yaxes(title_text="trend measure (above 0: up), in its own typical size", row=1, col=1)
fig.update_layout(title="How an hourly rule reads a dollar-bar value: the value steps when a bar finishes, the rule reads the step at each hourly close<br><sup>"
                        "BTCUSDT, 12 March 2024, UTC; trend measure with a fast span of 48 dollar bars (about a day); at the top of each hour, how many bars finished in it</sup>",
                  height=520, width=1150, margin=dict(t=110, l=80, b=90), legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "16_02_reading_another_clock", FIG)
print("done")
