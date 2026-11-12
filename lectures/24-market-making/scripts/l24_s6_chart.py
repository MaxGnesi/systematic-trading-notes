"""Lecture 24 §6, what it takes to break even: left, the result after fees of the tested designs at each of Bybit's public fee levels (results/sources.md);
right, what each advantage is worth in bp of the value traded, from our replay, from the fee schedule, and from the literature. Output: figures/24_s6_breakeven.png."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

R = lambda f: json.loads((L.RESULTS / f).read_text(encoding="utf-8"))
T, PA, DE, SP, LA = R("tests.json"), R("pause.json")["designs"], R("depth.json"), R("speed_check.json"), R("latency.json")
D = T["designs"]
TIERS = [("VIP 0", 2.0, 5.5), ("VIP 1", 1.8, 4.0), ("VIP 2", 1.6, 3.75), ("VIP 3", 1.4, 3.5), ("VIP 4", 1.2, 3.2), ("VIP 5", 1.0, 3.2), ("Supreme VIP", 0.0, 3.0),
         ("MM 1", -0.1, 3.0), ("MM 2", -0.25, 3.0), ("MM 3", -0.4, 3.0)]                           # maker, taker in bp; MM rebates with the best public taker fee
apply_theme()
fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.24,
                    subplot_titles=("Result after fees at Bybit's public fee levels", "What each advantage is worth"))
x = [t[0] for t in TIERS]
for k, name, c in (("baseline", "baseline", SERIES[0]), ("as_5_2", "Avellaneda-Stoikov", SERIES[2]), ("behind_1", "one tick behind", SERIES[4]),
                   ("pp_e0_c110_n2", "ping-pong, target and stop", SERIES[3])):
    r, tv = D[k]["result_bp"], D[k]["taker_value_share"]
    fig.add_scatter(x=x, y=[r - (1 - tv) * m - tv * tk for _, m, tk in TIERS], mode="lines+markers", line=dict(color=c, width=2), marker=dict(size=8), name=name, row=1, col=1)
fig.add_hline(y=0, line=dict(color=INK, width=1), row=1, col=1)
pause = (PA["baseline_pause0.5"]["in"]["before_bp"] - PA["baseline"]["in"]["before_bp"] + PA["baseline_pause0.5"]["oos"]["before_bp"] - PA["baseline"]["oos"]["before_bp"]) / 2
lat = {w: [LA[d]["5"]["baseline"] for d in LA if (d >= "2025-10-11") == (w == "oos")] for w in ("in", "oos")}
lat50 = {w: [LA[d]["50"]["baseline"] for d in LA if (d >= "2025-10-11") == (w == "oos")] for w in ("in", "oos")}
pool = lambda X: 1e4 * sum(v["result_usdt"] for v in X) / sum(v["value_usdt"] for v in X)
fast = sum(pool(lat[w]) - pool(lat50[w]) for w in ("in", "oos")) / 2
BARS = [("Supreme VIP: maker fee 0, not 2 bp", 2.0, MUTED, "fee schedule"),
        ("Market-maker rebate, level 3", 0.4, MUTED, "fee schedule"),
        ("Front of the queue, not the back", -0.06 + 1.16, SERIES[1], "literature"),
        ("Widen with volatility (H2)", T["tests"]["H2"]["diff_bp"], SERIES[0], "our replay"),
        ("Quote 1 bp deep", DE["behind_110"]["oos"]["result_bp"] - DE["baseline"]["oos"]["result_bp"], SERIES[0], "our replay"),
        ("Pause 0.5 s after a fill", pause, SERIES[0], "our replay"),
        ("See Binance with no delay (at most)", SP["oos"]["0"]["skip0.5"]["gain_bp"], SERIES[0], "our replay"),
        ("Binance guard (H1)", T["tests"]["H1"]["diff_bp"], SERIES[0], "our replay"),
        ("Orders at 5 ms, not 50 ms", fast, SERIES[0], "our replay")]
for lab, v, c, src in BARS:
    fig.add_bar(y=[lab], x=[v], orientation="h", marker_color=c, name=src, legendgroup=src, showlegend=lab in (BARS[0][0], BARS[2][0], BARS[3][0]), row=1, col=2)
fig.add_vline(x=-D["baseline"]["result_bp"], line=dict(color=INK, width=2, dash="dash"), row=1, col=2)
fig.add_annotation(x=-D["baseline"]["result_bp"], y=0.02, yref="y2 domain", text="the baseline's gap before fees", showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11), row=1, col=2)
fig.update_yaxes(title_text="bp of value traded", row=1, col=1); fig.update_yaxes(autorange="reversed", row=1, col=2)
fig.update_xaxes(title_text="fee level", row=1, col=1); fig.update_xaxes(title_text="bp of value traded", row=1, col=2)
fig.update_layout(title="What it takes to break even<br><sup>Bybit BTCUSDT perpetual; left: the tested designs on the 24 out-of-sample days at each public fee level; "
                        "right: what each advantage is worth, before fees, against the baseline</sup>",
                  barmode="overlay", height=620, width=1500, margin=dict(t=100, l=80, r=30, b=120), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, L.PREFIX + "24_s6_breakeven", L.FIG)
