"""Lecture 16 §4 figures. 16_06: the two parts of an hour's risk. Left: one week hour by hour (11-17 March 2024): activity (dollar volume over a typical
hour) and risk per unit of activity (realised variance over activity, over its 28-day median), on a log scale. Right: how the hour-to-hour variation of
log realised variance splits (l16_activity.json), and how well each part is forecast out of sample. 16_07: sizing by forecast risk (l16_horizon.json):
Sharpe ratio in both periods and the worst day, by speed, for the plain sizing, the raw and smoothed next-day forecast and the holding-period forecast."""
import json, sys
from datetime import datetime, timedelta
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

ACT = json.loads((L16_RESULTS / "l16_activity.json").read_text()); HZ = json.loads((L16_RESULTS / "l16_horizon.json").read_text())

# ---------------------------------------------------------------- 16_06
D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet([D / "2024-01" / "m1.parquet", D / "2024-02" / "m1.parquet", D / "2024-03" / "m1.parquet"]).select("time", "close", "usd").collect().sort("time")
H = (m1.with_columns(pl.col("close").log().diff().alias("r")).group_by_dynamic("time", every="1h").agg(pl.col("usd").sum(), (pl.col("r") ** 2).sum().alias("rv")).sort("time"))
typ = H["usd"].rolling_sum(24).rolling_median(28 * 24, min_samples=7 * 24).shift(1) / 24
H = H.with_columns((pl.col("usd") / typ).alias("A")).with_columns((pl.col("rv") / pl.col("A")).alias("q"))
H = H.with_columns((pl.col("q") / pl.col("q").rolling_median(28 * 24, min_samples=7 * 24).shift(1)).alias("Q"))
W = H.filter(pl.col("time").is_between(datetime(2024, 3, 11), datetime(2024, 3, 18), closed="left"))
dec = ACT["decomposition"]; tot = dec["var_log_rv"]
fig = make_subplots(rows=1, cols=2, column_widths=[0.64, 0.36], horizontal_spacing=0.1,
                    subplot_titles=("One week, hour by hour: the two parts move separately", "How the hour-to-hour variation of risk splits"))
fig.add_scatter(x=W["time"].to_list(), y=W["A"].to_list(), mode="lines", line=dict(color=SERIES[0], width=1.6), name="activity: dollars traded, x a typical hour", row=1, col=1)
fig.add_scatter(x=W["time"].to_list(), y=W["Q"].to_list(), mode="lines", line=dict(color=SERIES[3], width=1.6), name="risk per dollar traded, x its usual level", row=1, col=1)
fig.add_hline(y=1, line=dict(color=INK, dash="dot", width=1), row=1, col=1)
fig.update_yaxes(type="log", title_text="x its usual level (log scale)", tickvals=[0.1, 0.3, 1, 3, 10], ticktext=["0.1", "0.3", "1", "3", "10"], row=1, col=1)
parts = [("activity", dec["var_log_activity"] / tot, SERIES[0]), ("risk per dollar", dec["var_log_risk_per_activity"] / tot, SERIES[3]), ("both together", dec["two_cov"] / tot, MUTED)]
fig.add_bar(x=[p[0] for p in parts], y=[100 * p[1] for p in parts], marker=dict(color=[p[2] for p in parts], line=dict(width=0)), showlegend=False,
            text=[f"{100 * p[1]:.0f}%" for p in parts], textposition="outside", row=1, col=2)
fig.update_yaxes(title_text="% of the variation of log risk", range=[0, 55], row=1, col=2)
r2a = ACT["activity"]["M4 HAR + releases"]["2025-2026"]; r2q = ACT["ratio_forecast_r2"]["2025-2026"]
fig.add_annotation(x=0.5, y=-0.2, xref="x2 domain", yref="paper", text=f"Forecast out of sample (R²): activity {r2a:.2f}, risk per dollar {r2q:.2f}", showarrow=False, font=dict(size=11))
fig.update_layout(title="An hour's risk has two parts: how much is traded, and how far each dollar moves the price<br><sup>BTCUSDT; risk = realised variance from "
                        "one-minute returns; activity = dollars traded over a typical hour; risk per dollar = their ratio, over its usual level (28-day median)</sup>",
                  height=470, width=1150, margin=dict(t=110, l=80, b=110), legend=dict(orientation="h", y=-0.3, x=0))
save_figure(fig, PREFIX + "16_06_two_parts_of_risk", FIG)

# ---------------------------------------------------------------- 16_07
SP = ["0.5 d", "1 d", "2 d", "3 d", "5 d", "8 d", "13 d", "21 d"]; X = ["12 h", "1 d", "2 d", "3 d", "5 d", "8 d", "13 d", "21 d", "blend 1-3 d"]
V = (("plain: past 36 days", "plain: past 36 days' volatility", SERIES[0], "solid"), ("next-day forecast, raw", "next-day forecast, raw", MUTED, "dot"),
     ("next-day forecast", "next-day forecast, smoothed over a day", SERIES[1], "solid"), ("holding-period forecast", "forecast over the holding period", SERIES[2], "solid"))
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.06, subplot_titles=("Sharpe ratio, 2021-2024", "Sharpe ratio, 2025-2026", "Worst day, 2021-2024 (typical daily moves)"))
for c, (smp, key) in enumerate((("2021-2024", "sharpe"), ("2025-2026", "sharpe"), ("2021-2024", "worst_day")), start=1):
    for k, lab, col, dash in V:
        fig.add_scatter(x=X[:-1], y=[HZ[s][k][smp][key] for s in SP], mode="lines+markers", line=dict(color=col, width=2, dash=dash), marker=dict(size=6),
                        name=lab, legendgroup=k, showlegend=(c == 1), row=1, col=c)
        fig.add_scatter(x=[X[-1]], y=[HZ["blend 1-2-3 d"][k][smp][key]], mode="markers", marker=dict(size=11, color=col, line=dict(width=1.2, color=INK)), showlegend=False,
                        legendgroup=k, row=1, col=c)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=X, tickangle=-45, row=1, col=c)
    fig.add_shape(type="rect", xref=("x" if c == 1 else f"x{c}"), yref=("y domain" if c == 1 else f"y{c} domain"), x0=0.5, x1=3.5, y0=0, y1=1, fillcolor="rgba(27,175,122,0.12)",
                  line_width=0, layer="below")
    if key == "sharpe": fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=c)
fig.update_layout(title="Sizing by a sharper forecast of risk makes the worst days milder, but does not raise the Sharpe ratio<br><sup>The rule of §2 with four ways "
                        "of measuring the risk it sizes by; market orders and funding; shaded: the plateau; right of each panel: the blend of the plateau speeds</sup>",
                  height=500, width=1200, margin=dict(t=110, l=60), legend=dict(orientation="h", y=-0.3, x=0))
save_figure(fig, PREFIX + "16_07_sizing", FIG)
print("done")
