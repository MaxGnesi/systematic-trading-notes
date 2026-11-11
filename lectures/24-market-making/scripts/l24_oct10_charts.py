"""Lecture 24 §5, the figures of the 10 October case study, from l24_oct10_phases.py. Output: figures/24_s5_crash.png (the mid, the result so far and the
position through the crash) and figures/24_s5_split.png (each design's result split into fills, positions and fees)."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure


def label(d):
    """Plain names for the designs."""
    kill = ""
    if "_kill" in d:
        d, k = d.split("_kill"); x, o = k.strip("_").split("_") if k else ("10", "30"); kill = f" + kill switch {x} bp / {o} s"
    if d == "baseline": b = "baseline"
    elif d.startswith("guard_"): b = f"Binance guard {d[6:]} bp"
    elif d.startswith("behind_"): b = f"{d[7:]} tick behind"
    elif d.startswith("as_"): b = f"Avellaneda-Stoikov, c = {d.split('_')[2]}"
    else: b = {"pp_e0_c110_n2": "ping-pong (chosen)", "pp_e0_c110_n1": "ping-pong, off after 1 fill", "pp_e0_a_n2": "ping-pong, exit at the best", "pp_e0_b110_n2": "ping-pong, target without stop"}[d]
    return b + kill
apply_theme(); O = json.loads((L.RESULTS / "oct10_phases.json").read_text(encoding="utf-8")); P = pl.read_parquet(L.OUT / "oct10_paths.parquet")
F = pl.concat([pl.read_parquet(L.OUT / "oct10_fills.parquet").filter(~pl.col("design").str.starts_with("pp_"))] + [pl.read_parquet(L.OUT / f) for f in ("oct10_pp_fills.parquet", "oct10_case_quoters_fills.parquet")])
ts = lambda x: datetime.fromtimestamp(x / 1000, tz=timezone.utc).replace(tzinfo=None)
x = [ts(v) for v in P["t"].to_list()][::5]                                                         # every 5 s
SHOW = [("baseline", "baseline", SERIES[0]), ("baseline_kill", "baseline + kill switch", SERIES[1]), ("guard_1", "Binance guard, 1 bp", SERIES[2]),
        ("pp_e0_c110_n2", "ping-pong", SERIES[3]), ("pp_e0_c110_n2_kill", "ping-pong + kill switch", SERIES[4])]

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.34, 0.4, 0.26],
                    subplot_titles=("Bybit's mid; shaded: the fall and the bottom", "Result so far before fees", "Fills per minute"))
fig.add_scatter(x=x, y=P["mid"].to_numpy()[::5], mode="lines", line=dict(color=INK, width=1.5), name="mid", showlegend=False, row=1, col=1)
for k, (n, a, b) in enumerate(O["phases"]):
    for r in (1, 2, 3): fig.add_vrect(x0=ts(a), x1=ts(b), fillcolor=MUTED, opacity=0.15 if n in ("fall", "bottom") else 0.0, line_width=0, row=r, col=1)
    if n in ("before", "fall", "after"): fig.add_annotation(x=ts(a + (b - a) / 2), y=0.04, yref="y domain", text=n, showarrow=False, yanchor="bottom", font=dict(size=11, color=INK), row=1, col=1)
fig.add_annotation(x=ts(O["phases"][2][1]), y=0.04, yref="y domain", text="bottom, rebound", showarrow=False, xanchor="left", xshift=8, yanchor="bottom", font=dict(size=11, color=INK), row=1, col=1)
for d, name, c in SHOW:
    fig.add_scatter(x=x, y=P[d].to_numpy()[::5], mode="lines", line=dict(color=c, width=2), name=name, legendgroup=d, row=2, col=1)
    n = F.filter(pl.col("design") == d).with_columns(((pl.col("t") - P["t"][0]) // 60_000).alias("m")).group_by("m").len().sort("m")
    cnt = np.zeros(150); cnt[n["m"].to_numpy()] = n["len"].to_numpy()                               # minutes without a fill count 0
    xm = [ts(P["t"][0] + 60_000 * m + 30_000) for m in range(150)]
    fig.add_scatter(x=xm, y=cnt, mode="lines", line=dict(color=c, width=1.5), name=name, legendgroup=d, showlegend=False, row=3, col=1)
fig.update_layout(title="10 October 2025: what the crash did to five quoting rules<br><sup>Bybit BTCUSDT perpetual, 20:30 - 23:00 UTC; replay with 50 ms latency, 0.001 BTC orders, at most 10 lots either way; each design starts flat at 20:30</sup>",
                  height=900, width=1300, margin=dict(t=110, l=80, r=30, b=110), legend=dict(orientation="h", y=-0.08, x=0))
fig.update_yaxes(title_text="USDT", row=1, col=1); fig.update_yaxes(title_text="USDT", row=2, col=1); fig.update_yaxes(title_text="fills", row=3, col=1)
fig.update_xaxes(title_text="time, UTC", row=3, col=1)
save_figure(fig, L.PREFIX + "24_s5_crash", L.FIG)

D = sorted(O["designs"].items(), key=lambda kv: kv[1]["total"]["after_fee"])
names = [label(d) for d, _ in D]
fig = make_subplots(rows=1, cols=1)
for key, label, c in (("kept_10s", "fills: spread earned less the move against them after 10 s", SERIES[0]), ("positions", "positions: gain or loss beyond 10 s", SERIES[2]), ("fees", "fees (2 bp maker, 5.5 bp taker)", MUTED)):
    fig.add_bar(y=names, x=[v["total"][key] for _, v in D], orientation="h", marker_color=c, name=label)
fig.add_scatter(y=names, x=[v["total"]["after_fee"] for _, v in D], mode="markers", marker=dict(color=INK, size=9, symbol="diamond"), name="result after fees")
fig.update_layout(title="10 October 2025, 20:30 - 23:00 UTC: where each design's money went<br><sup>Bybit BTCUSDT perpetual, replay; 25 designs, ordered by the result after fees</sup>",
                  barmode="relative", height=900, width=1200, margin=dict(t=100, l=330, r=30, b=110), legend=dict(orientation="h", y=-0.08, x=0))
fig.update_xaxes(title_text="USDT over the 2.5 hours")
save_figure(fig, L.PREFIX + "24_s5_split", L.FIG)
