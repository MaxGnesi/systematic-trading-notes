"""Lecture 13 §3.5: the crash of 10 October 2025 on the tape: when it began, how it unfolded, and the sweep at the bottom."""
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
SWEEP = datetime(2025, 10, 10, 21, 20, 10, 325000)
m1 = pl.read_parquet(D / "2025-10" / "m1.parquet").sort("time")
low_row = m1.filter(pl.col("time").dt.date() == SWEEP.date()).sort("low").row(0, named=True)
day = m1.filter(pl.col("time").dt.date() == SWEEP.date())
high_row = day.filter(pl.col("time") < low_row["time"]).sort("high", descending=True).row(0, named=True)       # the day's high, before the low
last_hour = m1.filter(pl.col("time").is_between(low_row["time"] - timedelta(minutes=60), low_row["time"]))
crash = last_hour.sort("high", descending=True).row(0, named=True)                                              # the steep fall: from the highest price of the hour before the low
start, peak = crash["time"], crash
win = m1.filter(pl.col("time").is_between(low_row["time"] - timedelta(hours=3), low_row["time"] + timedelta(minutes=90)))
fall = m1.filter(pl.col("time").is_between(start, low_row["time"]))
after = m1.filter(pl.col("time") > low_row["time"])
R = dict(day_high=high_row["high"], day_high_time=str(high_row["time"]), steep_fall_from=peak["high"], steep_fall_began=str(start), low=low_row["low"], low_minute=str(low_row["time"]),
         day_fall_pct=round(100 * (low_row["low"] / high_row["high"] - 1), 1),
         steep_fall_pct=round(100 * (low_row["low"] / peak["high"] - 1), 1), fall_minutes=int((low_row["time"] - start).total_seconds() / 60),
         usd_during_fall_bn=round(float(fall["usd"].sum()) / 1e9, 1), net_buying_during_fall=round(float(fall["signed_usd"].sum() / fall["usd"].sum()), 3),
         busiest_minute_trades=int(win["trades"].max()), busiest_minute=str(win.sort("trades")["time"][-1]),
         median_minute_trades_day_before=float(m1.filter(pl.col("time").dt.date() == (SWEEP - timedelta(days=1)).date())["trades"].median()),
         rebound_1h_pct=round(100 * (after.filter(pl.col("time") <= low_row["time"] + timedelta(hours=1))["close"][-1] / low_row["low"] - 1), 1))

# ---------------------------------------------------------------- chart 1: the evening
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25], vertical_spacing=0.05,
                    subplot_titles=("Price, one-minute candles", "Trades per minute", "Cumulative net aggressive buying, $ billions"))
fig.add_candlestick(x=win["time"], open=win["open"], high=win["high"], low=win["low"], close=win["close"], showlegend=False,
                    increasing_line_color=SERIES[0], decreasing_line_color=SERIES[3], row=1, col=1)
fig.add_bar(x=win["time"], y=win["trades"], marker=dict(color=MUTED, line=dict(width=0)), showlegend=False, row=2, col=1)
fig.add_scatter(x=win["time"], y=win["signed_usd"].cum_sum() / 1e9, mode="lines", line=dict(color=SERIES[2], width=2), showlegend=False, row=3, col=1)
for x, lab in ((start, "the steep fall begins"), (low_row["time"], "the low; the sweep seconds later")):
    fig.add_vline(x=x, line=dict(color=INK, dash="dot", width=1))
    fig.add_annotation(x=x, y=0.97, yref="y domain", text=lab, showarrow=False, xanchor="left", yanchor="top", xshift=4, font=dict(size=11))
fig.update_xaxes(rangeslider_visible=False)
fig.update_layout(title=f"10 October 2025: the crash on BTCUSDT, from {peak['high']:,.0f} to {low_row['low']:,.0f} in {R['fall_minutes']} minutes<br><sup>All times UTC. "
                        "A slow drift for hours, then waves of aggressive selling; at the bottom, trading ran at a hundred times its usual pace</sup>",
                  height=640, width=1100, margin=dict(t=100))
save_figure(fig, PREFIX + "13_05_crash_evening", FIG)

# ---------------------------------------------------------------- chart 2: the 40 seconds around the sweep
ms = int(SWEEP.replace(tzinfo=timezone.utc).timestamp() * 1000)
t = (pl.scan_parquet(tape.source(SYM, "2025-10")).filter(pl.col("transact_time").is_between(ms - 20_000, ms + 20_000)).collect()
       .with_columns(pl.from_epoch("transact_time", time_unit="ms").alias("time"), (pl.col("price") * pl.col("quantity")).alias("usd"),
                     pl.when(pl.col("is_buyer_maker")).then(-1).otherwise(1).alias("sign")))
BIG = 250_000
def bubble(usd): return np.clip(6 + 7 * np.log10(np.maximum(usd, BIG) / BIG), 6, 30)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05)
for s_, col, nm in ((1, SERIES[0], "buyer-initiated trade"), (-1, SERIES[3], "seller-initiated trade")):
    q = t.filter(pl.col("sign") == s_)
    fig.add_scattergl(x=q["time"], y=q["price"], mode="markers", name=nm, marker=dict(size=3, color=col, opacity=0.45, line=dict(width=0)), row=1, col=1)
    b = q.filter(pl.col("usd") >= BIG)
    fig.add_scattergl(x=b["time"], y=b["price"], mode="markers", showlegend=False, marker=dict(size=bubble(b["usd"].to_numpy()), color=col, opacity=0.7, line=dict(width=1, color="white")), row=1, col=1)
for v, lab in ((BIG, "$250k"), (2.5e6, "$2.5m"), (2.5e7, "$25m")):
    fig.add_scattergl(x=[None], y=[None], mode="markers", name=f"trade of {lab}", marker=dict(size=bubble(np.array([v]))[0], color=MUTED, opacity=0.7), row=1, col=1)
sw = t.filter((pl.col("transact_time") == ms) & (pl.col("sign") == 1))
fig.add_scatter(x=[sw["time"][0]], y=[(sw["price"].min() + sw["price"].max()) / 2], mode="markers", name="the sweep: one order, 407 prices (ringed)",
                marker=dict(size=48, color=INK, symbol="circle-open", line=dict(width=2)), row=1, col=1)
cum = t.select("time", ((pl.col("usd") * pl.col("sign")).cum_sum() / 1e6).alias("cum"))
fig.add_scattergl(x=cum["time"], y=cum["cum"], mode="lines", line=dict(color=SERIES[2], width=2), showlegend=False, row=2, col=1)
fig.update_yaxes(title_text="price, USDT", row=1, col=1); fig.update_yaxes(title_text="net buying, $m", row=2, col=1)
fig.update_layout(title="The bottom of 10 October 2025: 21:19:50 to 21:20:30 UTC<br><sup>Each dot is one trade, coloured by the aggressor's side; trades of $250k or more are bubbles "
                        "that grow with their dollar value (see the key). Below: cumulative net aggressive buying</sup>",
                  height=580, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.12, x=0, itemsizing="constant"))
save_figure(fig, PREFIX + "13_06_crash_sweep", FIG)
(L13_RESULTS / "l13_oct10.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps(R, indent=1, default=str))
