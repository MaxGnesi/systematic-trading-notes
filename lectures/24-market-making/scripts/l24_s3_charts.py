"""Lecture 24 §3, every lever across its range: each design's result before fees less the baseline's on the same sampled hours, in and out of sample
(results/after_fees.json, stops.json, pause.json, latency.json), and what a lean on Binance could at most have saved (speed_check.json); and the
mechanism of quoting deeper (depth.json). Output: figures/24_s3_levers.png, figures/24_s3_depth.png."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

R = lambda f: json.loads((L.RESULTS / f).read_text(encoding="utf-8"))
AF, ST, PA, LA, SP, DE = R("after_fees.json"), R("stops.json")["designs"], R("pause.json")["designs"], R("latency.json"), R("speed_check.json"), R("depth.json")
IN, OUT = dict(color=SERIES[0], width=2), dict(color=SERIES[1], width=2)
apply_theme()


def diff(D, k, w, base="baseline"):
    """After fees, so that designs closing with market orders pay the taker fee; for designs that only rest it equals the difference before fees."""
    return D[k][w]["after_bp"] - D[base][w]["after_bp"]


def lat():
    """Baseline at each latency less the baseline at 50 ms, pooled over the days of each sample."""
    out = {}
    for w in ("in", "oos"):
        days = [d for d in LA if (d >= "2025-10-11") == (w == "oos")]; r = {}
        for l in ("5", "10", "25", "50"):
            x = [LA[d][l]["baseline"] for d in days]; r[l] = 1e4 * sum(v["result_usdt"] for v in x) / sum(v["value_usdt"] for v in x)
        out[w] = [r[l] - r["50"] for l in ("5", "10", "25", "50")]
    return out


T = ["Binance guard: threshold, bp", "Avellaneda-Stoikov: width c times volatility", "Ping-pong: how a position is closed",
     "Stop on every lot: width, bp", "Pause after a fill: seconds", "Order latency: ms", "Lean on Binance: the most it could save, by reaction time, ms"]
fig = make_subplots(rows=2, cols=4, subplot_titles=T + [""], vertical_spacing=0.2, horizontal_spacing=0.06)
def line(r, c, x, yi, yo, show=False, dash=None):
    fig.add_scatter(x=x, y=yi, mode="lines+markers", line=dict(**IN, dash=dash), marker=dict(size=8), name="in sample", legendgroup="in", showlegend=show, row=r, col=c)
    fig.add_scatter(x=x, y=yo, mode="lines+markers", line=dict(**OUT, dash=dash), marker=dict(size=8), name="out of sample", legendgroup="oos", showlegend=show, row=r, col=c)
g = [1, 2, 3, 5]; line(1, 1, g, [diff(AF, f"guard_{t}", "in") for t in g], [diff(AF, f"guard_{t}", "oos") for t in g], show=True)
c = [0, 0.5, 1, 2]
line(1, 2, c, [diff(AF, f"as_5_{v:g}", "in") for v in c], [diff(AF, f"as_5_{v:g}", "oos") for v in c])
line(1, 2, c, [diff(AF, f"as_0_{v:g}", "in") for v in c], [diff(AF, f"as_0_{v:g}", "oos") for v in c], dash="dot")
x = ["at the best", "target, no stop", "target and stop"]; k = ["pp_e0_a_n2", "pp_e0_b110_n2", "pp_e0_c110_n2"]
line(1, 3, x, [diff(AF, d, "in") for d in k], [diff(AF, d, "oos") for d in k])
fig.add_scatter(x=x, y=[AF[d]["oos"]["before_bp"] - AF["baseline"]["oos"]["before_bp"] for d in k], mode="markers", marker=dict(color=INK, size=11, symbol="diamond"),
                name="out of sample, before fees", row=1, col=3)
w = [5, 10, 20]; line(1, 4, w, [diff(ST, f"baseline_stop{v}", "in") for v in w], [diff(ST, f"baseline_stop{v}", "oos") for v in w])
line(1, 4, w, [diff(ST, f"as_5_2_stop{v}", "in", "as_5_2") for v in w], [diff(ST, f"as_5_2_stop{v}", "oos", "as_5_2") for v in w], dash="dot")
p = [0.2, 0.5, 1, 2, 5]; line(2, 1, p, [diff(PA, f"baseline_pause{v:g}", "in") for v in p], [diff(PA, f"baseline_pause{v:g}", "oos") for v in p])
line(2, 1, p, [diff(PA, f"as_5_2_pause{v:g}", "in", "as_5_2") for v in p], [diff(PA, f"as_5_2_pause{v:g}", "oos", "as_5_2") for v in p], dash="dot")
Ld = lat(); line(2, 2, [5, 10, 25, 50], Ld["in"], Ld["oos"])
r = [100, 50, 30, 10, 0]; line(2, 3, r, [SP["in"][str(v)]["skip0.5"]["gain_bp"] for v in r], [SP["oos"][str(v)]["skip0.5"]["gain_bp"] for v in r])
for i in range(1, 8): fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=(i - 1) // 4 + 1, col=(i - 1) % 4 + 1)
fig.update_xaxes(type="log", tickvals=p, ticktext=[f"{v:g}" for v in p], row=2, col=1); fig.update_xaxes(autorange="reversed", row=2, col=3)
fig.update_yaxes(title_text="bp, less the baseline", row=1, col=1); fig.update_yaxes(title_text="bp, less the baseline", row=2, col=1)
fig.update_layout(title="Every lever across its range<br><sup>Bybit BTCUSDT perpetual, sampled hours; each design's result after fees less the baseline's on the same hours (scales differ by panel); "
                        "solid: on the baseline, dotted: on Avellaneda-Stoikov (against Avellaneda-Stoikov without the lever; in panel 2, kappa = 0)</sup>",
                  height=800, width=1500, margin=dict(t=110, l=80, r=30, b=90), legend=dict(orientation="h", y=-0.1, x=0))
save_figure(fig, L.PREFIX + "24_s3_levers", L.FIG)

d = [1, 2, 3, 5, 10]; k = [f"behind_{v * 110}" for v in d]
fig = make_subplots(rows=1, cols=2, subplot_titles=("What a deeper quote earns and loses, per fill", "How often it is filled"), horizontal_spacing=0.1)
for w, sty, nm in (("in", "dot", "in sample"), ("oos", "solid", "out of sample")):
    fig.add_scatter(x=d, y=[DE[x][w]["spread_bp"] for x in k], mode="lines+markers", line=dict(color=SERIES[2], width=2, dash=sty), name=f"spread earned, {nm}", row=1, col=1)
    fig.add_scatter(x=d, y=[-DE[x][w]["move_1s_bp"] for x in k], mode="lines+markers", line=dict(color=SERIES[1], width=2, dash=sty), name=f"move against us in the first second, {nm}", row=1, col=1)
    fig.add_scatter(x=[0.01] + d, y=[DE["baseline"][w]["fills_hour"]] + [DE[x][w]["fills_hour"] for x in k], mode="lines+markers", line=dict(color=INK, width=2, dash=sty),
                    name=f"fills an hour, {nm}", row=1, col=2)
fig.update_xaxes(title_text="depth behind the best, bp", row=1, col=1); fig.update_xaxes(title_text="depth behind the best, bp (0.01: at the best)", type="log", row=1, col=2)
fig.update_yaxes(title_text="bp of value traded", row=1, col=1); fig.update_yaxes(title_text="fills an hour", type="log", row=1, col=2)
fig.update_layout(title="Quoting deeper: more spread, taken straight back<br><sup>Bybit BTCUSDT perpetual, the baseline quoting k bp behind the best on each side; "
                        "3 in-sample and 3 out-of-sample days, four hours each</sup>",
                  height=520, width=1300, margin=dict(t=100, l=80, r=30, b=150), legend=dict(orientation="h", y=-0.25, x=0))
save_figure(fig, L.PREFIX + "24_s3_depth", L.FIG)
