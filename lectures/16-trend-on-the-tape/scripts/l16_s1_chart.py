"""Lecture 16 figure 16_01: three clocks on one day (12 March 2024, a CPI release at 12:30 UTC). Top: the day's price from one-minute closes, with a dot
where each dollar bar finished; below it, how many dollar bars finished in each hour (columns: one per hourly close). Bottom: 00:00-04:00 and
15:00-19:00, with a shaded band from the last finished dollar bar to each hourly close: how old the information is that the rule can read."""
import json, sys
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

DAY = datetime(2024, 3, 12); RELEASE = datetime(2024, 3, 12, 12, 30)
m1 = pl.read_parquet(tape.ROOT / "interim" / "tape" / "BTCUSDT" / "2024-03" / "m1.parquet", columns=["time", "close"]).filter(pl.col("time").is_between(DAY - timedelta(hours=1), DAY + timedelta(days=1), closed="left"))
db = pl.read_parquet(tape.ROOT / "interim" / "bars" / "BTCUSDT" / "dollar" / "2024-03.parquet", columns=["end_ms", "close"])
a = int(DAY.replace(tzinfo=timezone.utc).timestamp() * 1000)
db = db.filter(pl.col("end_ms").is_between(a - 3 * 3_600_000, a + 86_400_000)).with_columns(pl.from_epoch("end_ms", time_unit="ms").alias("t"))
ends, endp = db["t"].to_list(), db["close"].to_list()
hours = [DAY + timedelta(hours=h) for h in range(1, 25)]
ages = [(h, max(t for t in ends if t <= h)) for h in hours]
counts = [sum(1 for t in ends if h - timedelta(hours=1) < t <= h) for h in hours]

fig = make_subplots(rows=3, cols=2, specs=[[{"colspan": 2}, None], [{"colspan": 2}, None], [{}, {}]], row_heights=[0.42, 0.13, 0.45], vertical_spacing=0.10,
                    horizontal_spacing=0.06, subplot_titles=(f"The whole day: {sum(counts)} dollar bars finished (dashes along the top), against 48 on an average day", "",
                                                            "A quiet night, 00:00 to 04:00", "The afternoon sell-off, 15:00 to 19:00"))
day = m1.filter(pl.col("time") >= DAY)
fig.add_scatter(x=day["time"].to_list(), y=day["close"].to_list(), mode="lines", line=dict(color=INK, width=1.1), name="price, one-minute closes", row=1, col=1)
de = [(t, p) for t, p in zip(ends, endp) if t >= DAY]
top = float(day["close"].max()) + 0.12 * float(day["close"].max() - day["close"].min())                       # a row of dashes along the top of the panel
fig.add_scatter(x=[t for t, _ in de], y=[top] * len(de), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=2, color=SERIES[0])), name="a dollar bar finished (information clock)", row=1, col=1)
fig.add_vline(x=RELEASE, line=dict(color=MUTED, dash="dot"), row=1, col=1)
fig.add_annotation(x=RELEASE, y=0, yref="y domain", xref="x", text="CPI release", showarrow=False, yshift=10, xanchor="left", xshift=4, font=dict(size=11, color=MUTED))
fig.add_bar(x=[h - timedelta(minutes=30) for h in hours], y=counts, marker=dict(color=SERIES[0], line=dict(width=0)), width=3_000_000, showlegend=False,
            text=counts, textposition="outside", textfont=dict(size=9), row=2, col=1)
fig.add_hline(y=2, line=dict(color=SERIES[1], dash="dot", width=1.2), row=2, col=1)
fig.add_annotation(x=DAY + timedelta(hours=8, minutes=30), y=2, xref="x2", yref="y2", text="average day: 2 an hour", showarrow=False, yshift=16, font=dict(size=10, color=SERIES[1]), xanchor="left")
fig.update_yaxes(title_text="bars an hour", range=[0, max(counts) * 1.4], row=2, col=1)
fig.update_xaxes(matches="x", row=2, col=1); fig.update_xaxes(showticklabels=False, row=1, col=1)
for c, (h0, h1) in enumerate(((0, 4), (15, 19)), start=1):
    t0, t1 = DAY + timedelta(hours=h0), DAY + timedelta(hours=h1)
    xr, yr = ("x3", "y3") if c == 1 else ("x4", "y4")
    w = m1.filter(pl.col("time").is_between(t0 - timedelta(minutes=5), t1))
    fig.add_scatter(x=w["time"].to_list(), y=w["close"].to_list(), mode="lines", line=dict(color=INK, width=1.1), showlegend=False, row=3, col=c)
    e = [(t, p) for t, p in zip(ends, endp) if t0 - timedelta(minutes=5) <= t <= t1]
    ytop = float(w["close"].max()) + 0.1 * float(w["close"].max() - w["close"].min())
    fig.add_scatter(x=[t for t, _ in e], y=[ytop] * len(e), mode="markers", marker=dict(symbol="line-ns", size=14, line=dict(width=2.2, color=SERIES[0])), showlegend=False, row=3, col=c)
    for h, last in ages:
        if t0 < h <= t1:
            fig.add_vrect(x0=last, x1=h, fillcolor="rgba(235,104,52,0.18)", line_width=0, row=3, col=c)
            fig.add_vline(x=h, line=dict(color=SERIES[1], width=1.6), row=3, col=c)
            fig.add_annotation(x=h, y=1, xref=xr, yref=f"{yr} domain", text=f"<b>{(h - last).total_seconds() / 60:.0f} min</b>", showarrow=False, yshift=-26, xanchor="right", bgcolor="rgba(255,255,255,0.8)",
                               font=dict(size=11, color=SERIES[1]))
    fig.update_xaxes(range=[t0 - timedelta(minutes=5), t1 + timedelta(minutes=6)], row=3, col=c)
fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=SERIES[1], width=1.6), name="hourly close: the rule decides (decision clock)")
fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color="rgba(235,104,52,0.4)", size=14, symbol="square"), name="age of the information the rule reads")
fig.update_yaxes(title_text="price, $", row=1, col=1); fig.update_yaxes(title_text="price, $", row=3, col=1)
fig.update_layout(title="Three clocks on one day: the rule decides on the hour and reads the last finished dollar bar<br><sup>BTCUSDT, 12 March 2024, UTC; dollar bars of "
                        "Lecture 13 (about 48 a day on average). Lower panels: the shaded band runs from the last finished dollar bar to the hourly close</sup>",
                  height=820, width=1150, margin=dict(t=110, l=80), legend=dict(orientation="h", y=-0.07, x=0))
save_figure(fig, PREFIX + "16_01_three_clocks", FIG)
print(json.dumps([(h.strftime("%H:%M"), round((h - l).total_seconds() / 60, 1)) for h, l in ages]))
