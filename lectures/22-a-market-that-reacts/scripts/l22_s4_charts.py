"""Lecture 22 §4-5 charts, from the saved results of l22_s4_tests.py, l22_s4_replay.py and l22_s4_h8.py. Figure 22_s4_replay: the hybrid replay out of sample, single orders by size
(actual against predicted net move at 10 s) and runs of orders (errors of the plain replay, the hybrid replay as fixed, and the parent-order follow-up). Figure 22_s5_fragile: 10 October
against the other days (H9), and the cost tail after quote pulls (H20a). --run recomputes the out-of-sample response by size class (results/s4_classes.json)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_s3_response as S3, l22_hybrid as H
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); CL = L.RESULTS / "s4_classes.json"
T = json.loads((L.RESULTS / "s4_tests.json").read_text(encoding="utf-8")); RP = json.loads((L.RESULTS / "s4_replay.json").read_text(encoding="utf-8"))
PP = json.loads((L.RESULTS / "s4_replay_parent.json").read_text(encoding="utf-8")) if (L.RESULTS / "s4_replay_parent.json").exists() else None
if "--run" in sys.argv or not CL.exists():
    agg = {}
    for d in T["oos"]:
        for r in S3.net_day(d).group_by("cls").agg(pl.len(), pl.col("n_m10000").sum(), pl.col("S").sum()).iter_rows():
            a = agg.setdefault(r[0], np.zeros(3)); a += np.array(r[1:], float)
    CL.write_text(json.dumps({k: dict(n=int(v[0]), actual=v[1] / v[0], S=v[2] / v[0]) for k, v in agg.items()}), encoding="utf-8")
C = json.loads(CL.read_text(encoding="utf-8")); c10 = T["c10"]; cls = [c[2] for c in S3.CLASSES]

fig = make_subplots(rows=1, cols=2, column_widths=[0.45, 0.55], horizontal_spacing=0.1, subplot_titles=("Single orders: does the hybrid replay predict the move? (H6)", "Runs of orders: how far off is each replay? (H7)"))
fig.add_scatter(x=cls, y=[C[k]["actual"] for k in cls], mode="lines+markers", line=dict(color=INK, width=2), marker=dict(size=9, symbol="diamond"), name="real orders, out of sample", row=1, col=1)
fig.add_scatter(x=cls, y=[c10[0] * C[k]["S"] ** c10[1] for k in cls], mode="lines+markers", line=dict(color=SERIES[0], width=2), marker=dict(size=8), name="hybrid replay, fitted in sample", row=1, col=1)
fig.add_scatter(x=cls, y=[0] * len(cls), mode="lines", line=dict(color=SERIES[1], width=2, dash="dot"), name="plain replay", row=1, col=1)
fig.update_xaxes(title_text="order size, BTC", row=1, col=1); fig.update_yaxes(title_text="mid move at 10 s in the order's direction, net, bp", row=1, col=1)
runs = [r for d in RP["per"].values() for r in d]; err = {"plain replay": [r["err_plain"] for r in runs], "hybrid replay, as fixed": [r["err_hybrid"] for r in runs]}
if PP: err["hybrid, parent orders (follow-up)"] = [r["err_hybrid"] for d in PP["per"].values() for r in d]
for (nm, e), c in zip(err.items(), (SERIES[1], SERIES[0], SERIES[2])):
    e = np.array(e); fig.add_box(x=e, name=nm, marker_color=c, boxpoints=False, orientation="h", showlegend=False, row=1, col=2)
fig.add_vline(x=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
fig.update_xaxes(title_text="predicted average price of the run less actual, bp (above 0: too dear)", range=[-6, 10], row=1, col=2)
fig.update_layout(title=f"Does the hybrid replay tell the truth? Out of sample<br><sup>Bybit BTCUSDT perpetual, {T['oos'][0]} to {T['oos'][-1]} ({len(T['oos'])} days). Left: orders of 0.01 BTC or more, net of matched controls. "
                  f"Right: {len(runs):,} runs of same-side orders adding up to 5 BTC or more within 10 s (300 sampled a day); boxes: quartiles, whiskers: 1.5 times the box</sup>",
                  height=520, width=1500, margin=dict(t=110, l=70, r=30, b=130), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L.PREFIX + "22_s4_replay", L.FIG)

W = T["h9_days"]; days = sorted(W); a20 = T["tests"]["H20a"]
fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.09, subplot_titles=("20:50-22:50 UTC: real moves over the calm-day prediction (H9)", "Cost of orders of 1-5 BTC after quote pulls (H20a)"))
col = [SERIES[1] if d == L.CASCADE_DAY else (SERIES[3] if W[d]["ratio_S"] > 4.8 else MUTED) for d in days]
fig.add_bar(x=days, y=[W[d]["ratio_S"] for d in days], marker_color=col, showlegend=False, row=1, col=1)
fig.add_hline(y=1, line=dict(color=INK, width=1, dash="dot"), row=1, col=1)
fig.update_xaxes(title_text="day (10 October in orange)", tickangle=-60, row=1, col=1); fig.update_yaxes(title_text="actual over predicted net move at 10 s", row=1, col=1)
for g, c, nm in (("bottom", SERIES[0], "fewest pulls in the last 5 s (bottom fifth)"), ("top", SERIES[1], "most pulls (top fifth)")):
    fig.add_scatter(x=["median", "90th percentile", "99th percentile"], y=[a20[g]["p50"], a20[g]["p90"], a20[g]["p99"]], mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=9), name=f"{nm}, {a20[g]['n']:,} orders", row=1, col=2)
fig.update_yaxes(title_text="average fill against the mid before, bp", type="log", row=1, col=2)
fig.update_layout(title=f"Close to the tipping point, out of sample<br><sup>Bybit BTCUSDT perpetual. Left: orders of 1 BTC or more in the same two evening hours of each of the {len(days)} days, model fitted in sample; pink: Sunday 26 October. "
                  f"Right: {T['oos'][0]} to {T['oos'][-1]}; fifths of the share of book updates that were quote pulls, fixed in sample</sup>", height=520, width=1500, margin=dict(t=110, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.32, x=0.55))
save_figure(fig, L.PREFIX + "22_s5_fragile", L.FIG)
print({k: round(v["actual"], 3) for k, v in C.items()})
